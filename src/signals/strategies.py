# src/signals/strategies.py - Time horizon strategy classification

"""
Time Horizon Strategy Classification

This module classifies trading signals by investment time horizon:
- Short-term: Days to weeks (momentum-driven, quick entry/exit)
- Mid-term: Weeks to months (balanced momentum + mean reversion)
- Long-term: Months to years (fundamental focus, trend following)
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import date, timedelta
from enum import Enum

class TimeHorizon(Enum):
    """Investment time horizon classification"""
    SHORT = "short"      # Days to weeks
    MID = "mid"          # Weeks to months
    LONG = "long"        # Months to years

class TimeHorizonStrategy:
    """
    Classifies signals by investment time horizon based on signal characteristics
    
    Strategy Rules:
    - Short-term: High momentum signals, gap breakaways, quick reversals
    - Mid-term: Balanced momentum + mean reversion, moderate holding periods
    - Long-term: Strong trend signals, fundamental strength, low volatility
    """
    
    def __init__(self):
        self.logger = logging.getLogger("TimeHorizonStrategy")
    
    def classify_signal(
        self,
        signal_name: str,
        signal_score: float,
        symbol: str,
        features: Optional[Dict[str, float]] = None
    ) -> TimeHorizon:
        """
        Classify a signal by time horizon
        
        Args:
            signal_name: Name of the signal (e.g., 'momentum_20_120', 'meanrev_bollinger')
            signal_score: Signal score (-1 to 1)
            symbol: Stock symbol
            features: Optional feature dictionary for additional context
        
        Returns:
            TimeHorizon enum value
        """
        
        # Signal type-based classification
        if signal_name == "gap_breakaway":
            # Gap breakaways are typically short-term momentum plays
            return TimeHorizon.SHORT
        
        elif signal_name == "meanrev_bollinger":
            # Mean reversion signals are typically mid-term (weeks to months)
            return TimeHorizon.MID
        
        elif signal_name == "momentum_20_120":
            # Momentum signals can be any horizon, need to analyze further
            return self._classify_momentum_signal(signal_score, features)
        
        else:
            # Default to mid-term for unknown signals
            self.logger.warning(f"Unknown signal type: {signal_name}, defaulting to MID")
            return TimeHorizon.MID
    
    def _classify_momentum_signal(
        self,
        signal_score: float,
        features: Optional[Dict[str, float]] = None
    ) -> TimeHorizon:
        """
        Classify momentum signal by analyzing its characteristics
        
        Short-term: Strong short-term momentum (ret_20), high volatility
        Mid-term: Balanced 20/120 day momentum
        Long-term: Strong long-term momentum (ret_120), low volatility, trend following
        """
        
        if not features:
            # Default based on signal strength
            if abs(signal_score) > 0.7:
                return TimeHorizon.SHORT  # Strong signals often short-term
            else:
                return TimeHorizon.MID
        
        ret_20 = features.get('momentum_ret_20', 0.0)
        ret_120 = features.get('momentum_ret_120', 0.0)
        volatility = features.get('momentum_vol_20d', 0.0)
        
        # Short-term indicators
        short_term_score = 0
        if abs(ret_20) > 0.15:  # Strong 20-day momentum
            short_term_score += 2
        if volatility > 0.25:  # High volatility
            short_term_score += 1
        if abs(ret_20) > abs(ret_120) * 1.5:  # Short-term momentum dominates
            short_term_score += 1
        
        # Long-term indicators
        long_term_score = 0
        if abs(ret_120) > 0.30:  # Strong 120-day momentum
            long_term_score += 2
        if volatility < 0.15:  # Low volatility
            long_term_score += 1
        if abs(ret_120) > abs(ret_20) * 1.2:  # Long-term momentum dominates
            long_term_score += 1
        
        # Classify based on scores
        if short_term_score >= 3:
            return TimeHorizon.SHORT
        elif long_term_score >= 3:
            return TimeHorizon.LONG
        else:
            return TimeHorizon.MID
    
    def classify_signals_batch(
        self,
        signals: Dict[str, Dict[str, float]],
        features_map: Optional[Dict[str, Dict[str, float]]] = None
    ) -> Dict[str, Dict[TimeHorizon, List[Tuple[str, float]]]]:
        """
        Classify a batch of signals by time horizon
        
        Args:
            signals: Dict mapping signal_name -> {symbol: score}
            features_map: Optional Dict mapping symbol -> {feature_name: value}
        
        Returns:
            Dict mapping signal_name -> {TimeHorizon: [(symbol, score), ...]}
        """
        
        classified = {}
        
        for signal_name, symbol_scores in signals.items():
            classified[signal_name] = {
                TimeHorizon.SHORT: [],
                TimeHorizon.MID: [],
                TimeHorizon.LONG: []
            }
            
            for symbol, score in symbol_scores.items():
                features = features_map.get(symbol, {}) if features_map else None
                horizon = self.classify_signal(signal_name, score, symbol, features)
                
                classified[signal_name][horizon].append((symbol, score))
            
            # Sort each horizon by score (absolute value for shorts)
            for horizon in TimeHorizon:
                classified[signal_name][horizon].sort(
                    key=lambda x: abs(x[1]),
                    reverse=True
                )
        
        return classified
    
    def get_horizon_characteristics(self, horizon: TimeHorizon) -> Dict[str, any]:
        """
        Get characteristics for a time horizon
        
        Returns:
            Dict with holding_period, risk_level, signal_types, etc.
        """
        
        characteristics = {
            TimeHorizon.SHORT: {
                "holding_period": "Days to weeks",
                "typical_days": (1, 14),
                "risk_level": "High",
                "volatility": "High",
                "signal_focus": ["momentum", "gap_breakaway"],
                "entry_exit_frequency": "High",
                "stop_loss_pct": 10.0,
                "take_profit_pct": 15.0,
                "description": "Quick momentum plays, gap breakaways, high-frequency trading"
            },
            TimeHorizon.MID: {
                "holding_period": "Weeks to months",
                "typical_days": (14, 90),
                "risk_level": "Medium",
                "volatility": "Medium",
                "signal_focus": ["momentum", "mean_reversion"],
                "entry_exit_frequency": "Moderate",
                "stop_loss_pct": 15.0,
                "take_profit_pct": 25.0,
                "description": "Balanced momentum and mean reversion, moderate holding periods"
            },
            TimeHorizon.LONG: {
                "holding_period": "Months to years",
                "typical_days": (90, 365),
                "risk_level": "Low to Medium",
                "volatility": "Low",
                "signal_focus": ["trend_following", "fundamentals"],
                "entry_exit_frequency": "Low",
                "stop_loss_pct": 20.0,
                "take_profit_pct": 40.0,
                "description": "Trend following, fundamental strength, lower frequency trading"
            }
        }
        
        return characteristics.get(horizon, {})

def classify_signal_by_horizon(
    signal_name: str,
    signal_score: float,
    symbol: str,
    features: Optional[Dict[str, float]] = None
) -> str:
    """
    Convenience function to classify a single signal
    
    Returns:
        String representation of time horizon ('short', 'mid', 'long')
    """
    strategy = TimeHorizonStrategy()
    horizon = strategy.classify_signal(signal_name, signal_score, symbol, features)
    return horizon.value

