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
        # Use the database manager instead of hardcoded URL
        from src.common.db_manager import db_manager
        self.engine = db_manager.get_engine()

    def calculate_forward_returns(self, symbols: List[str], start_date: date, end_date: date,
                                horizon_days: int = 5) -> pd.DataFrame:
        """Calculate forward returns for IC calculation"""

        is_sqlite = 'sqlite' in str(self.engine.url).lower()
        
        with self.engine.connect() as conn:
            if is_sqlite:
                # SQLite: Use IN clause with named parameters
                symbol_placeholders = ', '.join([f":s{i}" for i in range(len(symbols))])
                query = f"""
                    SELECT symbol, t, adj_c, 
                           LEAD(adj_c, :horizon) OVER (PARTITION BY symbol ORDER BY t) as future_price
                    FROM bars_1d
                    WHERE symbol IN ({symbol_placeholders})
                    AND DATE(t) BETWEEN DATE(:start_date) AND DATE(:end_date)
                """
                params = {'horizon': horizon_days, 'start_date': start_date, 'end_date': end_date}
                params.update({f"s{i}": s for i, s in enumerate(symbols)})
                result = conn.execute(text(query), params)
            else:
                # PostgreSQL: Use ANY with array
                result = conn.execute(text("""
                    SELECT symbol, t, adj_c, 
                           LEAD(adj_c, :horizon) OVER (PARTITION BY symbol ORDER BY t) as future_price
                    FROM bars_1d
                    WHERE symbol = ANY(:symbols)
                    AND t BETWEEN :start_date AND :end_date
                """), {
                    'symbols': symbols,
                    'start_date': start_date,
                    'end_date': end_date,
                    'horizon': horizon_days
                })

            df = pd.DataFrame(result.fetchall(), columns=result.keys())

            # Calculate forward returns
            df['fwd_ret'] = (df['future_price'] / df['adj_c']) - 1.0
            return df

    def calculate_ic(self, signals_df: pd.DataFrame, returns_df: pd.DataFrame,
                   window_days: int = 120) -> pd.DataFrame:
        """Calculate rolling information coefficient for each signal"""
        # Merge signals with forward returns
        merged = pd.merge(signals_df, returns_df, on=['symbol', 't'], how='inner')

        # Calculate IC (rank correlation) per date
        dates = sorted(merged['t'].unique())
        ic_values = []

        for d in dates:
            day_data = merged[merged['t'] == d]

            for signal_col in [c for c in merged.columns if c.startswith('signal_')]:
                # Spearman rank correlation
                corr = day_data[signal_col].corr(day_data['fwd_ret'], method='spearman')
                ic_values.append({
                    't': d,
                    'signal': signal_col,
                    'ic': corr if not np.isnan(corr) else 0
                })

        ic_df = pd.DataFrame(ic_values)

        # Calculate rolling window IC
        ic_df = ic_df.sort_values('t')
        ic_df['rolling_ic'] = ic_df.groupby('signal')['ic'].rolling(window=window_days).mean().reset_index(level=0, drop=True)

        return ic_df

    def weight_signals(self, ic_df: pd.DataFrame, min_ic: float = 0.0) -> Dict[str, float]:
        """Weight signals by their rolling IC"""
        # Get most recent IC values
        latest_ic = ic_df.sort_values('t').groupby('signal').last()

        # Apply minimum IC threshold and make all ICs positive
        weights = latest_ic['rolling_ic'].apply(lambda x: max(x, min_ic))

        # If all weights are zero, use equal weights
        if weights.sum() == 0:
            weights = pd.Series([1.0] * len(weights), index=weights.index)

        # Normalize to sum to 1
        weights = weights / weights.sum()

        return weights.to_dict()

    def combine_signals(self, signal_df: pd.DataFrame, weights: Dict[str, float]) -> pd.DataFrame:
        """Combine individual signals using weights"""
        # Start with a copy of the dataframe with just symbol and date
        result_df = signal_df[['symbol', 't']].copy()

        # Calculate weighted signal
        result_df['combined_score'] = 0

        for signal_name, weight in weights.items():
            col_name = signal_name.replace('signal_', '')
            if col_name in signal_df.columns:
                result_df['combined_score'] += signal_df[col_name] * weight

        # Normalize to [-1, 1] range
        score_max = result_df['combined_score'].abs().max()
        if score_max > 0:
            result_df['combined_score'] = result_df['combined_score'] / score_max

        return result_df

def blend_signals_ic_weighted(date_str: str = None):
    """
    Blend signals using Information Coefficient weighting

    This function implements the IC weighting approach from section 3.4:
    1. Calculate forward returns for each stock
    2. Compute rolling IC (correlation of signal to future returns)
    3. Weight signals by their IC
    4. Combine into a single score
    5. Rank and normalize to create final signal
    6. Save combined signal to database

    Args:
        date_str: Optional date string in YYYY-MM-DD format. If not provided,
                 uses yesterday's date for a daily run.
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("SignalBlender")

    # Use yesterday if date not specified
    if date_str is None:
        eval_date = date.today() - timedelta(days=1)
    else:
        eval_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    logger.info(f"🔀 Blending signals using IC weighting for date: {eval_date}")

    blender = SignalBlender()
    
    try:
        # Get symbols that have signals for this date
        with blender.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT symbol
                FROM signals_daily
                WHERE d = :eval_date
                AND signal_name IN ('momentum_20_120', 'meanrev_bollinger', 'gap_breakaway')
            """), {"eval_date": eval_date})
            
            symbols = [row[0] for row in result.fetchall()]
        
        if not symbols:
            logger.warning(f"No signals found for date {eval_date}, using equal weights")
            # Fallback to equal weights if no historical data
            weights = {
                "momentum_20_120": 0.4,
                "meanrev_bollinger": 0.35,
                "gap_breakaway": 0.25
            }
        else:
            # Calculate IC using historical data (last 120 days)
            lookback_start = eval_date - timedelta(days=180)  # Extra buffer for forward returns
            
            # Get signals for IC calculation period
            is_sqlite = 'sqlite' in str(blender.engine.url).lower()
            symbols_limited = symbols[:100]  # Limit for performance
            
            with blender.engine.connect() as conn:
                if is_sqlite:
                    # SQLite: Use IN clause with named parameters
                    symbol_placeholders = ', '.join([f":s{i}" for i in range(len(symbols_limited))])
                    query = f"""
                        SELECT symbol, d, signal_name, score
                        FROM signals_daily
                        WHERE d >= :start_date AND d <= :eval_date
                        AND signal_name IN ('momentum_20_120', 'meanrev_bollinger', 'gap_breakaway')
                        AND symbol IN ({symbol_placeholders})
                        ORDER BY d, symbol
                    """
                    params = {"start_date": lookback_start, "eval_date": eval_date}
                    params.update({f"s{i}": s for i, s in enumerate(symbols_limited)})
                    result = conn.execute(text(query), params)
                else:
                    # PostgreSQL: Use ANY with array
                    result = conn.execute(text("""
                        SELECT symbol, d, signal_name, score
                        FROM signals_daily
                        WHERE d >= :start_date AND d <= :eval_date
                        AND signal_name IN ('momentum_20_120', 'meanrev_bollinger', 'gap_breakaway')
                        AND symbol = ANY(:symbols)
                        ORDER BY d, symbol
                    """), {
                        "start_date": lookback_start,
                        "eval_date": eval_date,
                        "symbols": symbols_limited
                    })
                
                signal_data = result.fetchall()
            
            if len(signal_data) < 50:  # Not enough data for IC calculation
                logger.warning("Insufficient historical data for IC calculation, using equal weights")
                weights = {
                    "momentum_20_120": 0.4,
                    "meanrev_bollinger": 0.35,
                    "gap_breakaway": 0.25
                }
            else:
                # Convert to DataFrame
                signals_df = pd.DataFrame(signal_data, columns=['symbol', 'd', 'signal_name', 'score'])
                signals_pivot = signals_df.pivot_table(
                    index=['symbol', 'd'],
                    columns='signal_name',
                    values='score',
                    aggfunc='first'
                ).reset_index()
                
                # Calculate forward returns
                unique_symbols = signals_pivot['symbol'].unique().tolist()
                returns_df = blender.calculate_forward_returns(
                    unique_symbols,
                    lookback_start,
                    eval_date,
                    horizon_days=5
                )
                
                if returns_df.empty or len(returns_df) < 20:
                    logger.warning("Insufficient return data for IC calculation, using equal weights")
                    weights = {
                        "momentum_20_120": 0.4,
                        "meanrev_bollinger": 0.35,
                        "gap_breakaway": 0.25
                    }
                else:
                    # Calculate IC
                    ic_df = blender.calculate_ic(signals_pivot, returns_df, window_days=120)
                    
                    if ic_df.empty:
                        logger.warning("IC calculation returned empty, using equal weights")
                        weights = {
                            "momentum_20_120": 0.4,
                            "meanrev_bollinger": 0.35,
                            "gap_breakaway": 0.25
                        }
                    else:
                        # Get weights from IC
                        weights_dict = blender.weight_signals(ic_df, min_ic=0.0)
                        
                        # Map to our signal names
                        weights = {
                            "momentum_20_120": weights_dict.get("signal_momentum_20_120", 0.4),
                            "meanrev_bollinger": weights_dict.get("signal_meanrev_bollinger", 0.35),
                            "gap_breakaway": weights_dict.get("signal_gap_breakaway", 0.25)
                        }
                        
                        # Normalize to sum to 1
                        total = sum(weights.values())
                        if total > 0:
                            weights = {k: v/total for k, v in weights.items()}
        
        # Get signals for the evaluation date
        with blender.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT symbol, signal_name, score, explain
                FROM signals_daily
                WHERE d = :eval_date
                AND signal_name IN ('momentum_20_120', 'meanrev_bollinger', 'gap_breakaway')
            """), {"eval_date": eval_date})
            
            signal_data = result.fetchall()
        
        # Combine signals using weights
        combined_signals = {}
        signal_dict = {}
        
        for symbol, signal_name, score, explain_json in signal_data:
            if symbol not in signal_dict:
                signal_dict[symbol] = {}
            signal_dict[symbol][signal_name] = float(score)
            if symbol not in combined_signals:
                combined_signals[symbol] = {
                    "score": 0.0,
                    "explain": explain_json
                }
        
        # Calculate weighted combined score
        for symbol, signals in signal_dict.items():
            combined_score = 0.0
            for signal_name, score in signals.items():
                weight = weights.get(signal_name, 0.0)
                combined_score += score * weight
            combined_signals[symbol]["score"] = combined_score
        
        # Save combined signal to database
        signal_items = [(symbol, data["score"]) for symbol, data in combined_signals.items()]
        signal_items.sort(key=lambda x: x[1], reverse=True)
        
        # Detect database type for SQL compatibility
        is_sqlite = 'sqlite' in str(blender.engine.url).lower()
        
        with blender.engine.connect() as conn:
            for i, (symbol, combined_score) in enumerate(signal_items):
                rank = i + 1
                explain_json = combined_signals[symbol]["explain"]
                
                # Add IC weights to explain
                import json
                try:
                    explain = json.loads(explain_json) if explain_json else {}
                except:
                    explain = {}
                explain["ic_weights"] = weights
                explain_json = json.dumps(explain)
                
                if is_sqlite:
                    # SQLite: No type casting, use proper ON CONFLICT syntax
                    conn.execute(text("""
                        INSERT INTO signals_daily (symbol, d, signal_name, score, rank, explain)
                        VALUES (:symbol, :date, :signal_name, :score, :rank, :explain)
                        ON CONFLICT (symbol, d, signal_name) 
                        DO UPDATE SET score = :score_update, rank = :rank_update, explain = :explain_update
                    """), {
                        "symbol": symbol,
                        "date": eval_date,
                        "signal_name": "combined_ic_weighted",
                        "score": float(combined_score),
                        "rank": rank,
                        "explain": explain_json,
                        "score_update": float(combined_score),
                        "rank_update": rank,
                        "explain_update": explain_json
                    })
                else:
                    # PostgreSQL: Use jsonb type casting
                    conn.execute(text("""
                        INSERT INTO signals_daily (symbol, d, signal_name, score, rank, explain)
                        VALUES (:symbol, :date, :signal_name, :score, :rank, :explain::jsonb)
                        ON CONFLICT (symbol, d, signal_name) 
                        DO UPDATE SET score = :score, rank = :rank, explain = :explain::jsonb
                    """), {
                        "symbol": symbol,
                        "date": eval_date,
                        "signal_name": "combined_ic_weighted",
                        "score": float(combined_score),
                        "rank": rank,
                        "explain": explain_json
                    })
            
            conn.commit()
        
        logger.info("✅ Successfully blended signals with IC weighting")
        logger.info(f"📊 Signal weights:")
        for signal_name, weight in weights.items():
            logger.info(f"   - {signal_name}: {weight:.3f}")
        logger.info(f"📈 Combined signals saved: {len(combined_signals)} symbols")

        return {
            "date": eval_date.strftime("%Y-%m-%d"),
            "status": "success",
            "signals_blended": len(combined_signals),
            "weights": weights,
            "top_weights": {
                "momentum": weights.get("momentum_20_120", 0.0),
                "mean_reversion": weights.get("meanrev_bollinger", 0.0),
                "gap": weights.get("gap_breakaway", 0.0)
            }
        }
    
    except Exception as e:
        logger.error(f"❌ Error blending signals: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Fallback to equal weights
        return {
            "date": eval_date.strftime("%Y-%m-%d"),
            "status": "error",
            "error": str(e),
            "signals_blended": 0,
            "top_weights": {
                "momentum": 0.4,
                "mean_reversion": 0.35,
                "gap": 0.25
            }
        }

# Allow running as a script
if __name__ == "__main__":
    blend_signals_ic_weighted()
