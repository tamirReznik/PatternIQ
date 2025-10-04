# src/features/momentum.py - Momentum feature calculations

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from sqlalchemy import create_engine, text
from datetime import datetime, date
import os

class MomentumFeatures:
    """
    Momentum feature calculations as per spec section 3.1:
    - ret_20, ret_60, ret_120 (normalized by volatility)
    - rolling volatility and trend quality
    """

    def __init__(self):
        self.logger = logging.getLogger("MomentumFeatures")
        # Use the database manager instead of hardcoded URL
        from src.common.db_manager import db_manager
        self.engine = db_manager.get_engine()

    def calculate_returns(self, symbol: str, periods: List[int] = [20, 60, 120]) -> pd.DataFrame:
        """Calculate momentum returns for specified periods"""

        # Fetch price data for the symbol
        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                SELECT t, adj_c as close
                FROM bars_1d
                WHERE symbol = :symbol
                ORDER BY t ASC
                """),
                {"symbol": symbol}
            )

            data = result.fetchall()

        if not data:
            self.logger.warning(f"No price data found for {symbol}")
            return pd.DataFrame()

        # Convert to DataFrame
        df = pd.DataFrame(data, columns=['date', 'close'])
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        df['close'] = pd.to_numeric(df['close'])

        # Calculate returns for each period
        features = pd.DataFrame(index=df.index)

        for period in periods:
            if len(df) > period:
                # Simple return: (price_t / price_{t-n}) - 1
                returns = (df['close'] / df['close'].shift(period)) - 1
                features[f'ret_{period}'] = returns

                # Volatility-normalized momentum
                rolling_vol = df['close'].pct_change().rolling(60).std()
                features[f'mom_{period}_vol_norm'] = returns / (rolling_vol + 1e-6)

        # Calculate rolling volatility (20-day)
        features['vol_20d'] = df['close'].pct_change().rolling(20).std() * np.sqrt(252)  # Annualized

        return features.dropna()

    def calculate_trend_quality(self, symbol: str) -> pd.DataFrame:
        """Calculate trend quality indicators (ADX proxy and SMA slope)"""

        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                SELECT t, adj_o as open, adj_h as high, adj_l as low, adj_c as close
                FROM bars_1d
                WHERE symbol = :symbol
                ORDER BY t ASC
                """),
                {"symbol": symbol}
            )

            data = result.fetchall()

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data, columns=['date', 'open', 'high', 'low', 'close'])
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')

        for col in ['open', 'high', 'low', 'close']:
            df[col] = pd.to_numeric(df[col])

        features = pd.DataFrame(index=df.index)

        # Simple Moving Average and its slope
        features['sma_20'] = df['close'].rolling(20).mean()

        # Annualized slope of SMA (trend strength)
        sma_slope = (features['sma_20'] - features['sma_20'].shift(20)) / features['sma_20'].shift(20)
        features['sma_slope_20'] = sma_slope * 252 / 20  # Annualized

        # True Range for ADX calculation
        df['prev_close'] = df['close'].shift(1)
        df['tr1'] = df['high'] - df['low']
        df['tr2'] = abs(df['high'] - df['prev_close'])
        df['tr3'] = abs(df['low'] - df['prev_close'])
        df['true_range'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)

        # Simplified ADX (14-period average true range / price)
        features['atr_14'] = df['true_range'].rolling(14).mean()
        features['adx_proxy'] = features['atr_14'] / df['close']

        return features.dropna()

    def save_features_to_db(self, symbol: str, features_df: pd.DataFrame, feature_type: str):
        """Save calculated features to the features_daily table"""

        if features_df.empty:
            self.logger.warning(f"No features to save for {symbol}")
            return

        self.logger.info(f"Attempting to save {len(features_df)} rows and {len(features_df.columns)} columns of {feature_type} features for {symbol}")
        inserted = 0
        with self.engine.connect() as conn:
            for date_idx, row in features_df.iterrows():
                for feature_name, value in row.items():
                    if pd.notna(value):  # Only save non-NaN values
                        full_feature_name = f"{feature_type}_{feature_name}"
                        conn.execute(
                            text("""
                            INSERT INTO features_daily (symbol, d, feature_name, value)
                            VALUES (:symbol, :date, :feature_name, :value)
                            ON CONFLICT (symbol, d, feature_name) 
                            DO UPDATE SET value = :value
                            """),
                            {
                                "symbol": symbol,
                                "date": date_idx.date(),
                                "feature_name": full_feature_name,
                                "value": float(value)
                            }
                        )
                        inserted += 1
            conn.commit()
        self.logger.info(f"Saved {inserted} individual {feature_type} feature values for {symbol}")

    def compute_all_momentum_features(self, symbol: str):
        """Compute and save all momentum features for a symbol"""
        self.logger.info(f"Computing momentum features for {symbol}")

        # Calculate momentum returns
        momentum_features = self.calculate_returns(symbol)
        if not momentum_features.empty:
            self.save_features_to_db(symbol, momentum_features, "momentum")

        # Calculate trend quality
        trend_features = self.calculate_trend_quality(symbol)
        if not trend_features.empty:
            self.save_features_to_db(symbol, trend_features, "trend")

        self.logger.info(f"Completed momentum features for {symbol}")


def demo_momentum_features():
    """Demo: Calculate and save momentum features"""
    print("📈 PatternIQ Momentum Features Demo")
    print("=" * 50)

    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

    momentum_calc = MomentumFeatures()

    try:
        # Test with our existing symbols
        test_symbols = ["MMM", "AOS", "ABT"]

        for symbol in test_symbols:
            print(f"\n🔄 Computing features for {symbol}")
            print("-" * 30)

            momentum_calc.compute_all_momentum_features(symbol)

        # Show sample results
        print(f"\n📊 Sample Feature Results:")
        print("-" * 30)

        with momentum_calc.engine.connect() as conn:
            result = conn.execute(
                text("""
                SELECT symbol, d, feature_name, value
                FROM features_daily
                WHERE feature_name LIKE 'momentum_%' OR feature_name LIKE 'trend_%'
                ORDER BY symbol, d DESC, feature_name
                LIMIT 10
                """)
            )

            features = result.fetchall()

            if features:
                print("Symbol | Date       | Feature           | Value")
                print("-" * 50)
                for symbol, date, feature_name, value in features:
                    print(f"{symbol:6} | {date} | {feature_name:16} | {value:8.4f}")
            else:
                print("No features found in database")

        # Count total features
        with momentum_calc.engine.connect() as conn:
            result = conn.execute(
                text("SELECT COUNT(*) FROM features_daily")
            )
            total_features = result.fetchone()[0]
            print(f"\n✅ Total features in database: {total_features}")

        print(f"\n🎉 Momentum features demo completed!")
        print(f"Features implemented:")
        print(f"  ✅ ret_20, ret_60, ret_120 (momentum returns)")
        print(f"  ✅ vol_20d (rolling volatility)")
        print(f"  ✅ mom_*_vol_norm (volatility-normalized momentum)")
        print(f"  ✅ sma_slope_20 (trend strength)")
        print(f"  ✅ adx_proxy (trend quality)")

    except Exception as e:
        print(f"❌ Error in momentum features demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    demo_momentum_features()
