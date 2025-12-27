# src/signals/rules.py - Rule-based signal generation as per spec section 3.3

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from sqlalchemy import create_engine, text
from datetime import datetime, date
import os

class RuleBasedSignals:
    """
    Rule-based signal generation implementing signals from spec section 3.3:
    - momentum_20_120: Combined momentum signal
    - meanrev_bollinger: Mean reversion signal
    - gap_breakaway: Gap breakout signal (intraday when available)

    All signals normalized to [-1,1] range with gating conditions.
    """

    def __init__(self):
        self.logger = logging.getLogger("RuleBasedSignals")
        # Use the database manager instead of hardcoded URL
        from src.common.db_manager import db_manager
        self.engine = db_manager.get_engine()

    def get_features_for_signal(self, symbol: str, signal_date: date, required_features: List[str]) -> Dict[str, float]:
        """Get required features for a symbol on a specific date"""

        with self.engine.connect() as conn:
            # Get features for the signal date (or most recent available)
            placeholders = ','.join([f"'{feature}'" for feature in required_features])

            result = conn.execute(text(f"""
                SELECT feature_name, value
                FROM features_daily
                WHERE symbol = :symbol 
                AND d <= :signal_date
                AND feature_name IN ({placeholders})
                ORDER BY d DESC, feature_name
            """), {"symbol": symbol, "signal_date": signal_date})

            features = {}
            seen_features = set()

            for feature_name, value in result.fetchall():
                if feature_name not in seen_features:
                    features[feature_name] = float(value)
                    seen_features.add(feature_name)

        return features

    def check_earnings_gate(self, symbol: str, signal_date: date, window_days: int = 2) -> bool:
        """Check if symbol is within earnings window (gate condition)"""

        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*)
                FROM earnings
                WHERE symbol = :symbol
                AND ABS(EXTRACT(DAYS FROM (event_time::date - :signal_date))) <= :window_days
            """), {
                "symbol": symbol,
                "signal_date": signal_date,
                "window_days": window_days
            })

            earnings_count = result.fetchone()[0]
            return earnings_count == 0  # True if NO earnings within window

    def z_score_normalize(self, value: float, cross_sectional_values: List[float]) -> float:
        """Normalize value using cross-sectional z-score"""
        if not cross_sectional_values or len(cross_sectional_values) < 2:
            return 0.0

        mean_val = np.mean(cross_sectional_values)
        std_val = np.std(cross_sectional_values)

        if std_val == 0:
            return 0.0

        z_score = (value - mean_val) / std_val

        # Clip to [-3, 3] and normalize to [-1, 1]
        z_score = np.clip(z_score, -3, 3)
        return z_score / 3.0

    def momentum_20_120_signal(self, symbols: List[str], signal_date: date) -> Dict[str, float]:
        """
        Momentum signal: score = 0.6 * z(ret_20) + 0.4 * z(ret_120)
        Gate: exclude if earnings within ±2 days
        """
        self.logger.info(f"Computing momentum_20_120 signal for {len(symbols)} symbols on {signal_date}")

        signals = {}
        ret_20_values = []
        ret_120_values = []
        valid_symbols = []

        # First pass: collect all values for cross-sectional normalization
        for symbol in symbols:
            features = self.get_features_for_signal(symbol, signal_date,
                                                  ['momentum_ret_20', 'momentum_ret_120'])

            if 'momentum_ret_20' in features and 'momentum_ret_120' in features:
                # Check earnings gate
                if self.check_earnings_gate(symbol, signal_date):
                    ret_20_values.append(features['momentum_ret_20'])
                    ret_120_values.append(features['momentum_ret_120'])
                    valid_symbols.append(symbol)
                else:
                    signals[symbol] = 0.0  # Gated out due to earnings

        # Second pass: calculate z-scores and combine
        for i, symbol in enumerate(valid_symbols):
            features = self.get_features_for_signal(symbol, signal_date,
                                                  ['momentum_ret_20', 'momentum_ret_120'])

            z_ret_20 = self.z_score_normalize(features['momentum_ret_20'], ret_20_values)
            z_ret_120 = self.z_score_normalize(features['momentum_ret_120'], ret_120_values)

            # Combine with weights from spec
            signal_score = 0.6 * z_ret_20 + 0.4 * z_ret_120
            signals[symbol] = signal_score

        self.logger.info(f"Generated momentum signals for {len(signals)} symbols ({len(valid_symbols)} passed gates)")
        return signals

    def meanrev_bollinger_signal(self, symbols: List[str], signal_date: date) -> Dict[str, float]:
        """
        Mean reversion signal: score = -z(bollinger_z_20)
        Gate: require vol_z < 2.5 to avoid news-driven spikes
        """
        self.logger.info(f"Computing meanrev_bollinger signal for {len(symbols)} symbols on {signal_date}")

        signals = {}
        bollinger_values = []
        valid_symbols = []

        # Calculate Bollinger Z-score from available features
        for symbol in symbols:
            features = self.get_features_for_signal(symbol, signal_date,
                                                  ['trend_sma_20', 'momentum_vol_20d'])

            # Get recent price data to calculate Bollinger position
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT adj_c
                    FROM bars_1d
                    WHERE symbol = :symbol AND t <= :signal_date
                    ORDER BY t DESC
                    LIMIT 20
                """), {"symbol": symbol, "signal_date": signal_date})

                prices = [row[0] for row in result.fetchall()]

            if len(prices) >= 20 and 'trend_sma_20' in features and 'momentum_vol_20d' in features:
                current_price = prices[0]
                sma_20 = features['trend_sma_20']
                vol_20d = features['momentum_vol_20d']

                # Calculate Bollinger position: (price - sma) / (2 * std)
                recent_prices = np.array(prices[:20])
                std_20 = np.std(recent_prices)

                if std_20 > 0:
                    bollinger_z = (current_price - sma_20) / (2 * std_20)

                    # Volume gate: avoid high volatility periods
                    if vol_20d < 2.5:  # Vol z-score gate from spec
                        bollinger_values.append(bollinger_z)
                        valid_symbols.append((symbol, bollinger_z))
                    else:
                        signals[symbol] = 0.0  # Gated out due to high volatility

        # Normalize and invert (mean reversion)
        bollinger_list = [bz for _, bz in valid_symbols]
        for symbol, bollinger_z in valid_symbols:
            z_bollinger = self.z_score_normalize(bollinger_z, bollinger_list)
            signals[symbol] = -z_bollinger  # Negative for mean reversion

        self.logger.info(f"Generated mean reversion signals for {len(signals)} symbols")
        return signals

    def gap_breakaway_signal(self, symbols: List[str], signal_date: date) -> Dict[str, float]:
        """
        Gap breakaway signal: score = z(overnight_gap_pct) + 0.5 * z(vol_z_open)
        Gate: ignore if fills > 70% by 11:00 (simplified for daily data)
        """
        self.logger.info(f"Computing gap_breakaway signal for {len(symbols)} symbols on {signal_date}")

        signals = {}
        gap_values = []
        valid_symbols = []

        for symbol in symbols:
            # Get recent bars to calculate overnight gap
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT t, adj_o, adj_c, adj_h, adj_l, adj_v
                    FROM bars_1d
                    WHERE symbol = :symbol AND t <= :signal_date
                    ORDER BY t DESC
                    LIMIT 2
                """), {"symbol": symbol, "signal_date": signal_date})

                bars = result.fetchall()

            if len(bars) >= 2:
                current_bar = bars[0]  # Most recent
                prev_bar = bars[1]     # Previous day

                current_open = current_bar[1]
                prev_close = prev_bar[2]
                current_high = current_bar[3]
                current_low = current_bar[4]
                current_volume = current_bar[5]

                # Calculate overnight gap percentage
                if prev_close > 0:
                    gap_pct = (current_open - prev_close) / prev_close

                    # Simple gap fill check: if open is between high/low, consider it filled
                    gap_fill_ratio = 0.0
                    if gap_pct > 0:  # Gap up
                        if current_low < current_open:
                            gap_fill_ratio = (current_open - current_low) / (current_open - prev_close)
                    elif gap_pct < 0:  # Gap down
                        if current_high > current_open:
                            gap_fill_ratio = (current_high - current_open) / (prev_close - current_open)

                    # Gate: ignore if gap filled significantly (simplified)
                    if gap_fill_ratio < 0.7:  # Less than 70% filled
                        gap_values.append(abs(gap_pct))  # Use absolute value for ranking
                        valid_symbols.append((symbol, gap_pct, current_volume))
                    else:
                        signals[symbol] = 0.0  # Gated out due to gap fill

        # Get volume features for normalization
        for symbol, gap_pct, volume in valid_symbols:
            features = self.get_features_for_signal(symbol, signal_date, ['momentum_vol_20d'])

            gap_list = [abs(gp) for _, gp, _ in valid_symbols]
            vol_list = [v for _, _, v in valid_symbols]

            z_gap = self.z_score_normalize(abs(gap_pct), gap_list)
            z_vol = self.z_score_normalize(volume, vol_list)

            # Combine gap and volume signals (preserve gap direction)
            signal_score = z_gap + 0.5 * z_vol
            if gap_pct < 0:  # Gap down - negative signal
                signal_score = -signal_score

            signals[symbol] = signal_score

        self.logger.info(f"Generated gap breakaway signals for {len(signals)} symbols")
        return signals

    def save_signals_to_db(self, signals: Dict[str, float], signal_name: str, signal_date: date, 
                          time_horizons: Optional[Dict[str, str]] = None):
        """Save calculated signals to signals_daily table"""

        if not signals:
            self.logger.warning(f"No signals to save for {signal_name}")
            return

        # Calculate ranks
        signal_values = list(signals.values())
        signal_items = [(symbol, score) for symbol, score in signals.items() if score != 0]
        signal_items.sort(key=lambda x: x[1], reverse=True)  # Descending order

        with self.engine.connect() as conn:
            for i, (symbol, score) in enumerate(signal_items):
                rank = i + 1
                
                # Build explain JSON with time horizon if available
                explain_data = {}
                if time_horizons and symbol in time_horizons:
                    explain_data["time_horizon"] = time_horizons[symbol]
                
                import json
                explain_json = json.dumps(explain_data) if explain_data else None

                conn.execute(text("""
                    INSERT INTO signals_daily (symbol, d, signal_name, score, rank, explain)
                    VALUES (:symbol, :date, :signal_name, :score, :rank, :explain::jsonb)
                    ON CONFLICT (symbol, d, signal_name) 
                    DO UPDATE SET score = :score, rank = :rank, explain = :explain::jsonb
                """), {
                    "symbol": symbol,
                    "date": signal_date,
                    "signal_name": signal_name,
                    "score": float(score),
                    "rank": rank,
                    "explain": explain_json
                })

            conn.commit()

        non_zero_signals = len([s for s in signals.values() if s != 0])
        self.logger.info(f"Saved {non_zero_signals} {signal_name} signals to database")

    def compute_all_signals(self, symbols: List[str], signal_date: date):
        """Compute all rule-based signals for given symbols and date"""
        self.logger.info(f"Computing all signals for {len(symbols)} symbols on {signal_date}")

        # Generate each signal type
        momentum_signals = self.momentum_20_120_signal(symbols, signal_date)
        meanrev_signals = self.meanrev_bollinger_signal(symbols, signal_date)
        gap_signals = self.gap_breakaway_signal(symbols, signal_date)

        # Classify signals by time horizon
        try:
            from src.signals.strategies import TimeHorizonStrategy
            strategy = TimeHorizonStrategy()
            
            # Get features for classification
            features_map = {}
            for symbol in symbols:
                features = self.get_features_for_signal(
                    symbol, signal_date,
                    ['momentum_ret_20', 'momentum_ret_120', 'momentum_vol_20d']
                )
                if features:
                    features_map[symbol] = features
            
            # Classify each signal type
            momentum_horizons = {}
            for symbol, score in momentum_signals.items():
                features = features_map.get(symbol)
                horizon = strategy.classify_signal("momentum_20_120", score, symbol, features)
                momentum_horizons[symbol] = horizon.value
            
            meanrev_horizons = {}
            for symbol, score in meanrev_signals.items():
                horizon = strategy.classify_signal("meanrev_bollinger", score, symbol, None)
                meanrev_horizons[symbol] = horizon.value
            
            gap_horizons = {}
            for symbol, score in gap_signals.items():
                horizon = strategy.classify_signal("gap_breakaway", score, symbol, None)
                gap_horizons[symbol] = horizon.value
            
        except Exception as e:
            self.logger.warning(f"Could not classify time horizons: {e}")
            momentum_horizons = meanrev_horizons = gap_horizons = None

        # Save to database with time horizons
        self.save_signals_to_db(momentum_signals, "momentum_20_120", signal_date, momentum_horizons)
        self.save_signals_to_db(meanrev_signals, "meanrev_bollinger", signal_date, meanrev_horizons)
        self.save_signals_to_db(gap_signals, "gap_breakaway", signal_date, gap_horizons)

        return {
            "momentum_20_120": momentum_signals,
            "meanrev_bollinger": meanrev_signals,
            "gap_breakaway": gap_signals
        }


def generate_signals():
    """Generate rule-based trading signals for all available symbols"""
    print("📊 PatternIQ Signal Generation Demo")
    print("=" * 50)

    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

    signal_engine = RuleBasedSignals()

    try:
        # Get available symbols and dates
        with signal_engine.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT symbol FROM instruments 
                WHERE symbol IN (SELECT DISTINCT symbol FROM features_daily)
                ORDER BY symbol
            """))
            available_symbols = [row[0] for row in result.fetchall()]

            result = conn.execute(text("""
                SELECT MAX(d) FROM features_daily
            """))
            latest_date = result.fetchone()[0]

        if not available_symbols:
            print("❌ No symbols with features found. Run feature engineering first.")
            return

        print(f"📈 Available symbols: {available_symbols}")
        print(f"📅 Latest feature date: {latest_date}")

        # Generate signals for latest date
        signal_date = latest_date
        print(f"\n🔄 Computing signals for {signal_date}")

        all_signals = signal_engine.compute_all_signals(available_symbols, signal_date)

        # Display results
        print(f"\n📊 Signal Generation Results:")
        print("-" * 40)

        for signal_name, signals in all_signals.items():
            non_zero = {k: v for k, v in signals.items() if v != 0}
            print(f"\n{signal_name}:")
            print(f"   Active signals: {len(non_zero)}/{len(signals)}")

            if non_zero:
                # Show top 3 positive and negative
                sorted_signals = sorted(non_zero.items(), key=lambda x: x[1], reverse=True)

                print(f"   Top 3 positive:")
                for symbol, score in sorted_signals[:3]:
                    print(f"     {symbol}: {score:+.4f}")

                if len(sorted_signals) > 3:
                    print(f"   Top 3 negative:")
                    for symbol, score in sorted_signals[-3:]:
                        print(f"     {symbol}: {score:+.4f}")

        # Show database summary
        with signal_engine.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT signal_name, COUNT(*) as count, 
                       AVG(score) as avg_score, STDDEV(score) as std_score
                FROM signals_daily
                WHERE d = :signal_date
                GROUP BY signal_name
                ORDER BY signal_name
            """), {"signal_date": signal_date})

            signal_stats = result.fetchall()

            print(f"\n📋 Database Signal Summary:")
            print(f"Signal Name          | Count | Avg Score | Std Dev")
            print(f"---------------------|-------|-----------|--------")
            for signal_name, count, avg_score, std_score in signal_stats:
                avg_str = f"{avg_score:.4f}" if avg_score else "0.0000"
                std_str = f"{std_score:.4f}" if std_score else "0.0000"
                print(f"{signal_name:20} | {count:5} | {avg_str:9} | {std_str:7}")

        print(f"\n✅ Signal generation demo completed!")
        print(f"Features implemented:")
        print(f"  ✅ momentum_20_120 (combined momentum)")
        print(f"  ✅ meanrev_bollinger (mean reversion)")
        print(f"  ✅ gap_breakaway (gap signals)")
        print(f"  ✅ Cross-sectional z-score normalization")
        print(f"  ✅ Gating conditions (earnings, volatility)")
        print(f"  ✅ Signal ranking and database storage")

    except Exception as e:
        print(f"❌ Error in signal generation demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    demo_signal_generation()
