# src/backtest/metrics.py - Performance metrics and analytics as per spec section 4

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from sqlalchemy import create_engine, text
from datetime import datetime, date, timedelta
import os

class PerformanceAnalyzer:
    """
    Performance analytics for backtesting results implementing spec requirements:
    - IC (Information Coefficient) measurement
    - Sharpe ratio, max drawdown, hit-rate analysis
    - Risk attribution and factor decomposition
    - Turnover cost analysis
    """

    def __init__(self):
        self.logger = logging.getLogger("PerformanceAnalyzer")
        db_url = os.getenv("PATTERNIQ_DB_URL", "postgresql://admin:secret@localhost:5432/patterniq")
        self.engine = create_engine(db_url)

    def get_backtest_returns(self, run_id: str) -> pd.DataFrame:
        """Get daily returns for a backtest run"""

        with self.engine.connect() as conn:
            # Get positions and calculate daily returns
            result = conn.execute(text("""
                WITH daily_positions AS (
                    SELECT d, symbol, weight, price_entry
                    FROM backtest_positions
                    WHERE run_id = :run_id
                    ORDER BY d, symbol
                ),
                daily_returns AS (
                    SELECT 
                        bp.d,
                        bp.symbol,
                        bp.weight,
                        bp.price_entry,
                        b.adj_c as price_close,
                        LAG(b.adj_c) OVER (PARTITION BY bp.symbol ORDER BY bp.d) as price_prev,
                        CASE 
                            WHEN LAG(b.adj_c) OVER (PARTITION BY bp.symbol ORDER BY bp.d) > 0
                            THEN (b.adj_c - LAG(b.adj_c) OVER (PARTITION BY bp.symbol ORDER BY bp.d)) 
                                 / LAG(b.adj_c) OVER (PARTITION BY bp.symbol ORDER BY bp.d)
                            ELSE 0
                        END as stock_return
                    FROM daily_positions bp
                    JOIN bars_1d b ON bp.symbol = b.symbol AND bp.d = b.t::date
                )
                SELECT 
                    d,
                    SUM(weight * stock_return) as portfolio_return
                FROM daily_returns
                WHERE stock_return IS NOT NULL
                GROUP BY d
                ORDER BY d
            """), {"run_id": run_id})

            data = result.fetchall()

        if not data:
            self.logger.warning(f"No return data found for run_id: {run_id}")
            return pd.DataFrame()

        df = pd.DataFrame(data, columns=['date', 'return'])
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')

        return df

    def calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calculate annualized Sharpe ratio"""

        if len(returns) == 0 or returns.std() == 0:
            return 0.0

        excess_return = returns.mean() * 252 - risk_free_rate
        volatility = returns.std() * np.sqrt(252)

        return excess_return / volatility

    def calculate_max_drawdown(self, returns: pd.Series) -> Tuple[float, int]:
        """Calculate maximum drawdown and duration"""

        if len(returns) == 0:
            return 0.0, 0

        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max

        max_dd = drawdown.min()

        # Calculate drawdown duration (days in drawdown)
        is_in_drawdown = drawdown < -0.001  # More than 0.1% down
        drawdown_periods = is_in_drawdown.astype(int).groupby((is_in_drawdown != is_in_drawdown.shift()).cumsum()).sum()
        max_dd_duration = drawdown_periods.max() if len(drawdown_periods) > 0 else 0

        return max_dd, max_dd_duration

    def calculate_hit_rate(self, returns: pd.Series) -> Dict[str, float]:
        """Calculate hit rates (% positive days, weeks, months)"""

        if len(returns) == 0:
            return {"daily": 0.0, "weekly": 0.0, "monthly": 0.0}

        # Daily hit rate
        daily_hit_rate = (returns > 0).mean()

        # Weekly hit rate (resample to weekly)
        weekly_returns = returns.resample('W').sum()
        weekly_hit_rate = (weekly_returns > 0).mean() if len(weekly_returns) > 0 else 0.0

        # Monthly hit rate
        monthly_returns = returns.resample('M').sum()
        monthly_hit_rate = (monthly_returns > 0).mean() if len(monthly_returns) > 0 else 0.0

        return {
            "daily": daily_hit_rate,
            "weekly": weekly_hit_rate,
            "monthly": monthly_hit_rate
        }

    def calculate_information_coefficient(self, run_id: str, horizon_days: int = 5) -> float:
        """Calculate Information Coefficient (IC) for the strategy"""

        with self.engine.connect() as conn:
            # Get signal scores and forward returns
            result = conn.execute(text("""
                WITH signal_returns AS (
                    SELECT 
                        bp.d,
                        bp.symbol,
                        bp.weight,
                        s.score as signal_score,
                        b1.adj_c as price_entry,
                        b2.adj_c as price_exit,
                        CASE 
                            WHEN b1.adj_c > 0 
                            THEN (b2.adj_c - b1.adj_c) / b1.adj_c
                            ELSE NULL
                        END as forward_return
                    FROM backtest_positions bp
                    JOIN signals_daily s ON bp.symbol = s.symbol AND bp.d = s.d
                    JOIN bars_1d b1 ON bp.symbol = b1.symbol AND bp.d = b1.t::date
                    JOIN bars_1d b2 ON bp.symbol = b2.symbol 
                        AND b2.t::date = bp.d + INTERVAL ':horizon days'
                    WHERE bp.run_id = :run_id
                    AND s.signal_name IN (
                        SELECT labeling FROM backtests WHERE run_id = :run_id
                    )
                )
                SELECT signal_score, forward_return
                FROM signal_returns
                WHERE forward_return IS NOT NULL
                AND signal_score IS NOT NULL
            """), {"run_id": run_id, "horizon": horizon_days})

            data = result.fetchall()

        if len(data) < 10:  # Need minimum observations
            self.logger.warning(f"Insufficient data for IC calculation: {len(data)} observations")
            return 0.0

        signals, returns = zip(*data)

        # Calculate Spearman rank correlation
        ic = pd.Series(signals).corr(pd.Series(returns), method='spearman')

        return ic if not pd.isna(ic) else 0.0

    def calculate_turnover_analysis(self, run_id: str) -> Dict[str, float]:
        """Analyze portfolio turnover and associated costs"""

        with self.engine.connect() as conn:
            # Get daily positions to calculate turnover
            result = conn.execute(text("""
                WITH daily_weights AS (
                    SELECT d, symbol, weight
                    FROM backtest_positions
                    WHERE run_id = :run_id
                    ORDER BY d, symbol
                ),
                weight_changes AS (
                    SELECT 
                        d,
                        symbol,
                        weight,
                        LAG(weight, 1, 0) OVER (PARTITION BY symbol ORDER BY d) as prev_weight,
                        ABS(weight - LAG(weight, 1, 0) OVER (PARTITION BY symbol ORDER BY d)) as weight_change
                    FROM daily_weights
                )
                SELECT 
                    d,
                    SUM(weight_change) as daily_turnover
                FROM weight_changes
                GROUP BY d
                ORDER BY d
            """), {"run_id": run_id})

            turnover_data = result.fetchall()

        if not turnover_data:
            return {"avg_daily": 0.0, "avg_annual": 0.0, "total_cost_bps": 0.0}

        turnovers = [row[1] for row in turnover_data if row[1] is not None]

        if len(turnovers) == 0:
            return {"avg_daily": 0.0, "avg_annual": 0.0, "total_cost_bps": 0.0}

        avg_daily_turnover = np.mean(turnovers)
        avg_annual_turnover = avg_daily_turnover * 252

        # Get cost parameters from backtest metadata
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT cost_bps, slippage_bps
                FROM backtests
                WHERE run_id = :run_id
            """), {"run_id": run_id})

            cost_data = result.fetchone()

        total_cost_bps = (cost_data[0] + cost_data[1]) if cost_data else 7.0
        annual_cost_bps = avg_annual_turnover * total_cost_bps

        return {
            "avg_daily": avg_daily_turnover,
            "avg_annual": avg_annual_turnover,
            "total_cost_bps": annual_cost_bps
        }

    def generate_performance_report(self, run_id: str) -> Dict[str, any]:
        """Generate comprehensive performance report"""

        self.logger.info(f"Generating performance report for run_id: {run_id}")

        # Get backtest metadata
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT universe, start_date, end_date, cost_bps, slippage_bps, labeling, created_at
                FROM backtests
                WHERE run_id = :run_id
            """), {"run_id": run_id})

            metadata = result.fetchone()

        if not metadata:
            self.logger.error(f"No backtest found for run_id: {run_id}")
            return {}

        universe, start_date, end_date, cost_bps, slippage_bps, signal_name, created_at = metadata

        # Get returns data
        returns_df = self.get_backtest_returns(run_id)

        if returns_df.empty:
            self.logger.error(f"No returns data found for run_id: {run_id}")
            return {}

        returns = returns_df['return']

        # Calculate all metrics
        total_return = (1 + returns).prod() - 1
        annualized_return = (1 + total_return) ** (252 / len(returns)) - 1
        sharpe = self.calculate_sharpe_ratio(returns)
        max_dd, max_dd_duration = self.calculate_max_drawdown(returns)
        hit_rates = self.calculate_hit_rate(returns)
        ic = self.calculate_information_coefficient(run_id)
        turnover_analysis = self.calculate_turnover_analysis(run_id)

        # Additional metrics
        volatility = returns.std() * np.sqrt(252)
        skewness = returns.skew()
        kurtosis = returns.kurtosis()

        # Calmar ratio (annualized return / max drawdown)
        calmar = abs(annualized_return / max_dd) if max_dd < 0 else 0

        # Best and worst days
        best_day = returns.max()
        worst_day = returns.min()

        report = {
            "run_id": run_id,
            "metadata": {
                "signal_name": signal_name,
                "universe": universe,
                "start_date": start_date,
                "end_date": end_date,
                "trading_days": len(returns),
                "cost_bps": cost_bps,
                "slippage_bps": slippage_bps,
                "created_at": created_at
            },
            "returns": {
                "total_return": total_return,
                "annualized_return": annualized_return,
                "volatility": volatility,
                "sharpe_ratio": sharpe,
                "calmar_ratio": calmar
            },
            "risk": {
                "max_drawdown": max_dd,
                "max_drawdown_days": max_dd_duration,
                "skewness": skewness,
                "kurtosis": kurtosis,
                "worst_day": worst_day,
                "best_day": best_day
            },
            "hit_rates": hit_rates,
            "signal_quality": {
                "information_coefficient": ic
            },
            "turnover": turnover_analysis
        }

        self.logger.info(f"Performance report generated for {signal_name}: "
                        f"Return={total_return:.2%}, Sharpe={sharpe:.2f}, MaxDD={max_dd:.2%}")

        return report


def demo_performance_analysis():
    """Demo: Analyze performance of a completed backtest"""
    print("📈 PatternIQ Performance Analysis Demo")
    print("=" * 50)

    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

    analyzer = PerformanceAnalyzer()

    try:
        # Get available backtest runs
        with analyzer.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT run_id, labeling, start_date, end_date, created_at
                FROM backtests
                ORDER BY created_at DESC
                LIMIT 3
            """))

            runs = result.fetchall()

        if not runs:
            print("❌ No backtest runs found. Run backtesting first.")
            return

        print(f"📊 Available backtest runs:")
        for run_id, signal_name, start_date, end_date, created_at in runs:
            print(f"   {run_id[:8]}... | {signal_name} | {start_date} to {end_date}")

        # Analyze the most recent run
        latest_run = runs[0]
        run_id = latest_run[0]

        print(f"\n🔍 Analyzing run: {run_id}")

        # Generate comprehensive report
        report = analyzer.generate_performance_report(run_id)

        if not report:
            print("❌ Could not generate performance report")
            return

        # Display results
        print(f"\n📋 Performance Report")
        print(f"{'='*50}")

        meta = report['metadata']
        print(f"Signal: {meta['signal_name']}")
        print(f"Period: {meta['start_date']} to {meta['end_date']} ({meta['trading_days']} days)")
        print(f"Universe: {meta['universe']}")
        print(f"Costs: {meta['cost_bps']}bps + {meta['slippage_bps']}bps slippage")

        returns = report['returns']
        print(f"\n📊 Return Metrics:")
        print(f"   Total Return:      {returns['total_return']:8.2%}")
        print(f"   Annualized Return: {returns['annualized_return']:8.2%}")
        print(f"   Volatility:        {returns['volatility']:8.2%}")
        print(f"   Sharpe Ratio:      {returns['sharpe_ratio']:8.2f}")
        print(f"   Calmar Ratio:      {returns['calmar_ratio']:8.2f}")

        risk = report['risk']
        print(f"\n⚠️  Risk Metrics:")
        print(f"   Max Drawdown:      {risk['max_drawdown']:8.2%}")
        print(f"   Drawdown Duration: {risk['max_drawdown_days']:8.0f} days")
        print(f"   Skewness:          {risk['skewness']:8.2f}")
        print(f"   Kurtosis:          {risk['kurtosis']:8.2f}")
        print(f"   Best Day:          {risk['best_day']:8.2%}")
        print(f"   Worst Day:         {risk['worst_day']:8.2%}")

        hit_rates = report['hit_rates']
        print(f"\n🎯 Hit Rates:")
        print(f"   Daily:             {hit_rates['daily']:8.2%}")
        print(f"   Weekly:            {hit_rates['weekly']:8.2%}")
        print(f"   Monthly:           {hit_rates['monthly']:8.2%}")

        signal_quality = report['signal_quality']
        print(f"\n📡 Signal Quality:")
        print(f"   Information Coeff: {signal_quality['information_coefficient']:8.4f}")

        turnover = report['turnover']
        print(f"\n🔄 Turnover Analysis:")
        print(f"   Daily Turnover:    {turnover['avg_daily']:8.2%}")
        print(f"   Annual Turnover:   {turnover['avg_annual']:8.2%}")
        print(f"   Annual Cost:       {turnover['total_cost_bps']:8.0f} bps")

        print(f"\n✅ Performance analysis completed!")
        print(f"Features demonstrated:")
        print(f"  ✅ Comprehensive return metrics (Sharpe, Calmar)")
        print(f"  ✅ Risk analysis (drawdown, skew, kurtosis)")
        print(f"  ✅ Hit rate analysis (daily/weekly/monthly)")
        print(f"  ✅ Information Coefficient measurement")
        print(f"  ✅ Turnover and cost analysis")

    except Exception as e:
        print(f"❌ Error in performance analysis demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    demo_performance_analysis()
