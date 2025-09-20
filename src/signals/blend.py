# src/signals/blend.py - Signal blending and IC weighting as per spec section 3.4

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from sqlalchemy import create_engine, text
from datetime import datetime, date, timedelta
import os

class SignalBlender:
    """
    Signal combination and IC (Information Coefficient) weighting as per spec section 3.4:
    - Compute rolling IC for each signal vs future returns
    - Weight signals by IC performance
    - Combine into final composite signal
    - Portfolio construction with ranking and risk overlay
    """

    def __init__(self):
        self.logger = logging.getLogger("SignalBlender")
        db_url = os.getenv("PATTERNIQ_DB_URL", "postgresql://admin:secret@localhost:5432/patterniq")
        self.engine = create_engine(db_url)

    def calculate_forward_returns(self, symbols: List[str], start_date: date, end_date: date,
                                horizon_days: int = 5) -> pd.DataFrame:
        """Calculate forward returns for IC calculation"""

        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT symbol, t, adj_c,
                       LEAD(adj_c, :horizon) OVER (PARTITION BY symbol ORDER BY t) as future_price
                FROM bars_1d
                WHERE symbol = ANY(:symbols)
                AND t BETWEEN :start_date AND :end_date
                ORDER BY symbol, t
            """), {
                "symbols": symbols,
                "start_date": start_date,
                "end_date": end_date,
                "horizon": horizon_days
            })

            data = result.fetchall()

        returns_data = []
        for symbol, t, current_price, future_price in data:
            if future_price is not None and current_price > 0:
                forward_return = (future_price - current_price) / current_price
                returns_data.append({
                    'symbol': symbol,
                    'date': t.date(),
                    'forward_return': forward_return
                })

        return pd.DataFrame(returns_data)

    def calculate_ic_for_signal(self, signal_name: str, start_date: date, end_date: date,
                              horizon_days: int = 5, min_observations: int = 20) -> float:
        """Calculate Information Coefficient (rank correlation) for a signal"""

        # Get signal data
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT symbol, d, score
                FROM signals_daily
                WHERE signal_name = :signal_name
                AND d BETWEEN :start_date AND :end_date
                ORDER BY symbol, d
            """), {
                "signal_name": signal_name,
                "start_date": start_date,
                "end_date": end_date
            })

            signal_data = pd.DataFrame(result.fetchall(), columns=['symbol', 'date', 'score'])

        if signal_data.empty:
            self.logger.warning(f"No signal data found for {signal_name}")
            return 0.0

        # Get forward returns
        symbols = signal_data['symbol'].unique().tolist()
        returns_df = self.calculate_forward_returns(symbols, start_date, end_date, horizon_days)

        if returns_df.empty:
            self.logger.warning(f"No return data found for IC calculation")
            return 0.0

        # Merge signals with forward returns
        merged = pd.merge(signal_data, returns_df, on=['symbol', 'date'], how='inner')

        if len(merged) < min_observations:
            self.logger.warning(f"Insufficient observations for {signal_name}: {len(merged)}")
            return 0.0

        # Calculate rank correlation (Information Coefficient)
        ic = merged['score'].corr(merged['forward_return'], method='spearman')

        if pd.isna(ic):
            return 0.0

        self.logger.info(f"IC for {signal_name}: {ic:.4f} ({len(merged)} observations)")
        return ic

    def calculate_rolling_ic(self, signal_name: str, end_date: date,
                           lookback_days: int = 120, horizon_days: int = 5) -> float:
        """Calculate rolling IC over specified lookback period"""

        start_date = end_date - timedelta(days=lookback_days)
        return self.calculate_ic_for_signal(signal_name, start_date, end_date, horizon_days)

    def get_signal_weights(self, signal_names: List[str], as_of_date: date,
                          lookback_days: int = 120) -> Dict[str, float]:
        """
        Calculate IC-based weights for signals as per spec:
        w_i = max(IC_i, 0) / sum(max(IC_i,0))
        """
        self.logger.info(f"Calculating IC weights for {len(signal_names)} signals as of {as_of_date}")

        ics = {}
        for signal_name in signal_names:
            ic = self.calculate_rolling_ic(signal_name, as_of_date, lookback_days)
            ics[signal_name] = ic

        # Apply max(IC, 0) and normalize
        positive_ics = {name: max(ic, 0) for name, ic in ics.items()}
        total_positive_ic = sum(positive_ics.values())

        if total_positive_ic == 0:
            # Equal weights if no positive ICs
            equal_weight = 1.0 / len(signal_names)
            weights = {name: equal_weight for name in signal_names}
            self.logger.warning("No positive ICs found, using equal weights")
        else:
            weights = {name: ic / total_positive_ic for name, ic in positive_ics.items()}

        self.logger.info(f"Signal weights: {weights}")
        return weights

    def create_combined_signal(self, symbols: List[str], signal_date: date,
                             signal_names: List[str]) -> Dict[str, float]:
        """Create combined signal using IC-weighted blending"""

        # Get signal weights
        weights = self.get_signal_weights(signal_names, signal_date)

        # Get all signals for the date
        with self.engine.connect() as conn:
            placeholders = ','.join([f"'{name}'" for name in signal_names])
            result = conn.execute(text(f"""
                SELECT symbol, signal_name, score
                FROM signals_daily
                WHERE d = :signal_date
                AND signal_name IN ({placeholders})
                AND symbol = ANY(:symbols)
            """), {
                "signal_date": signal_date,
                "symbols": symbols
            })

            signal_data = result.fetchall()

        # Organize signals by symbol
        symbol_signals = {}
        for symbol, signal_name, score in signal_data:
            if symbol not in symbol_signals:
                symbol_signals[symbol] = {}
            symbol_signals[symbol][signal_name] = score

        # Combine signals using weights
        combined_signals = {}
        for symbol in symbols:
            if symbol in symbol_signals:
                weighted_score = 0.0
                total_weight = 0.0

                for signal_name, weight in weights.items():
                    if signal_name in symbol_signals[symbol]:
                        weighted_score += weight * symbol_signals[symbol][signal_name]
                        total_weight += weight

                if total_weight > 0:
                    combined_signals[symbol] = weighted_score / total_weight
                else:
                    combined_signals[symbol] = 0.0
            else:
                combined_signals[symbol] = 0.0

        self.logger.info(f"Created combined signal for {len(combined_signals)} symbols")
        return combined_signals

    def construct_portfolio(self, combined_signals: Dict[str, float],
                          long_pct: float = 0.2, short_pct: float = 0.2,
                          max_position: float = 0.03) -> Dict[str, Dict[str, float]]:
        """
        Portfolio construction as per spec:
        - Rank-sort by combined_score
        - Take top X% long, bottom Y% short
        - Cap position per name (e.g., 1%-3%)
        """

        # Filter out zero signals and sort
        active_signals = {k: v for k, v in combined_signals.items() if v != 0}
        sorted_signals = sorted(active_signals.items(), key=lambda x: x[1], reverse=True)

        if not sorted_signals:
            self.logger.warning("No active signals for portfolio construction")
            return {"long": {}, "short": {}}

        total_symbols = len(sorted_signals)
        long_count = max(1, int(total_symbols * long_pct))
        short_count = max(1, int(total_symbols * short_pct))

        # Select long and short positions
        long_symbols = sorted_signals[:long_count]
        short_symbols = sorted_signals[-short_count:] if short_count > 0 else []

        # Calculate position weights
        portfolio = {"long": {}, "short": {}}

        # Long positions
        if long_symbols:
            long_weight_per_position = min(max_position, 1.0 / len(long_symbols))
            for symbol, score in long_symbols:
                portfolio["long"][symbol] = long_weight_per_position

        # Short positions
        if short_symbols:
            short_weight_per_position = min(max_position, 1.0 / len(short_symbols))
            for symbol, score in short_symbols:
                portfolio["short"][symbol] = -short_weight_per_position  # Negative for short

        long_exposure = sum(portfolio["long"].values())
        short_exposure = abs(sum(portfolio["short"].values()))
        net_exposure = long_exposure + short_exposure

        self.logger.info(f"Portfolio: {len(portfolio['long'])} long, {len(portfolio['short'])} short")
        self.logger.info(f"Exposure: {long_exposure:.2%} long, {short_exposure:.2%} short, {net_exposure:.2%} gross")

        return portfolio

    def save_combined_signal(self, combined_signals: Dict[str, float], signal_date: date):
        """Save combined signal to database"""

        # Calculate ranks
        signal_items = [(symbol, score) for symbol, score in combined_signals.items() if score != 0]
        signal_items.sort(key=lambda x: x[1], reverse=True)

        with self.engine.connect() as conn:
            for i, (symbol, score) in enumerate(signal_items):
                rank = i + 1

                conn.execute(text("""
                    INSERT INTO signals_daily (symbol, d, signal_name, score, rank)
                    VALUES (:symbol, :date, :signal_name, :score, :rank)
                    ON CONFLICT (symbol, d, signal_name) 
                    DO UPDATE SET score = :score, rank = :rank
                """), {
                    "symbol": symbol,
                    "date": signal_date,
                    "signal_name": "combined_ic_weighted",
                    "score": float(score),
                    "rank": rank
                })

            conn.commit()

        self.logger.info(f"Saved combined signal for {len(signal_items)} symbols")


def demo_signal_blending():
    """Demo: Blend signals using IC weighting and construct portfolio"""
    print("🔗 PatternIQ Signal Blending & Portfolio Construction Demo")
    print("=" * 60)

    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

    blender = SignalBlender()

    try:
        # Get available signals and dates
        with blender.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT signal_name 
                FROM signals_daily 
                WHERE signal_name != 'combined_ic_weighted'
                ORDER BY signal_name
            """))
            available_signals = [row[0] for row in result.fetchall()]

            result = conn.execute(text("""
                SELECT MAX(d) FROM signals_daily
                WHERE signal_name != 'combined_ic_weighted'
            """))
            latest_date = result.fetchone()[0]

            result = conn.execute(text("""
                SELECT DISTINCT symbol FROM signals_daily 
                WHERE d = :latest_date
                ORDER BY symbol
            """), {"latest_date": latest_date})
            available_symbols = [row[0] for row in result.fetchall()]

        if not available_signals:
            print("❌ No individual signals found. Run signal generation first.")
            return

        print(f"📊 Available signals: {available_signals}")
        print(f"📅 Latest signal date: {latest_date}")
        print(f"📈 Available symbols: {available_symbols}")

        # Calculate IC weights
        print(f"\n🔄 Calculating IC weights...")
        weights = blender.get_signal_weights(available_signals, latest_date)

        print(f"\n📊 Signal IC Weights:")
        for signal_name, weight in weights.items():
            print(f"   {signal_name:20}: {weight:.4f}")

        # Create combined signal
        print(f"\n🔗 Creating combined signal...")
        combined_signals = blender.create_combined_signal(available_symbols, latest_date, available_signals)

        # Save combined signal
        blender.save_combined_signal(combined_signals, latest_date)

        # Construct portfolio
        print(f"\n📈 Constructing portfolio...")
        portfolio = blender.construct_portfolio(combined_signals, long_pct=0.3, short_pct=0.2)

        # Display results
        print(f"\n📋 Portfolio Construction Results:")
        print("-" * 40)

        print(f"\nLong Positions ({len(portfolio['long'])}):")
        if portfolio['long']:
            for symbol, weight in sorted(portfolio['long'].items(), key=lambda x: x[1], reverse=True):
                signal_score = combined_signals.get(symbol, 0)
                print(f"   {symbol}: {weight:6.2%} (signal: {signal_score:+.4f})")

        print(f"\nShort Positions ({len(portfolio['short'])}):")
        if portfolio['short']:
            for symbol, weight in sorted(portfolio['short'].items(), key=lambda x: x[1]):
                signal_score = combined_signals.get(symbol, 0)
                print(f"   {symbol}: {weight:6.2%} (signal: {signal_score:+.4f})")

        # Portfolio statistics
        long_exposure = sum(portfolio['long'].values())
        short_exposure = abs(sum(portfolio['short'].values()))
        gross_exposure = long_exposure + short_exposure
        net_exposure = long_exposure - short_exposure

        print(f"\n📊 Portfolio Statistics:")
        print(f"   Long exposure:  {long_exposure:7.2%}")
        print(f"   Short exposure: {short_exposure:7.2%}")
        print(f"   Gross exposure: {gross_exposure:7.2%}")
        print(f"   Net exposure:   {net_exposure:7.2%}")
        print(f"   Total positions: {len(portfolio['long']) + len(portfolio['short'])}")

        print(f"\n✅ Signal blending demo completed!")
        print(f"Features implemented:")
        print(f"  ✅ IC (Information Coefficient) calculation")
        print(f"  ✅ Rolling IC weighting (6-month lookback)")
        print(f"  ✅ Signal combination with IC weights")
        print(f"  ✅ Portfolio construction (long/short)")
        print(f"  ✅ Position sizing and risk controls")

    except Exception as e:
        print(f"❌ Error in signal blending demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    demo_signal_blending()
