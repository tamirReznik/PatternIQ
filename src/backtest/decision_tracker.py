#!/usr/bin/env python3
"""
Decision Tracker for Retrospective Simulation
Tracks all buy/sell decisions and their outcomes for quality analysis
"""

import logging
from typing import Dict, List, Optional
from datetime import date
import pandas as pd
import numpy as np


class DecisionTracker:
    """
    Tracks trading decisions and their outcomes for quality analysis
    """
    
    def __init__(self):
        self.logger = logging.getLogger("DecisionTracker")
        self.decisions: List[Dict] = []
        self.outcomes: List[Dict] = []
        self.decision_id_counter = 0
    
    def record_decision(
        self,
        date: date,
        symbol: str,
        action: str,  # 'BUY' or 'SELL'
        decision: Dict,
        price: float,
        signal_score: Optional[float] = None,
        time_horizon: Optional[str] = None,
        asset_class: Optional[str] = None
    ) -> int:
        """
        Record a trading decision with all context
        
        Returns:
            decision_id for tracking
        """
        decision_id = self.decision_id_counter
        self.decision_id_counter += 1
        
        decision_record = {
            'decision_id': decision_id,
            'date': date,
            'symbol': symbol,
            'action': action,
            'price': price,
            'signal_score': signal_score,
            'time_horizon': time_horizon,
            'asset_class': asset_class,
            'reason': decision.get('reason', ''),
            'should_execute': decision.get('should_buy', False) or decision.get('should_sell', False),
            'adjusted_size': decision.get('adjusted_size', 0) or decision.get('shares', 0),
            'metadata': {
                'decision': decision,
                'timestamp': pd.Timestamp.now()
            }
        }
        
        self.decisions.append(decision_record)
        return decision_id
    
    def record_outcome(
        self,
        decision_id: int,
        exit_date: date,
        exit_price: float,
        pnl: float,
        pnl_percent: float,
        holding_period_days: int
    ):
        """
        Record the outcome of a decision
        
        Args:
            decision_id: ID of the decision being tracked
            exit_date: Date when position was closed
            exit_price: Price at which position was closed
            pnl: Profit/loss in dollars
            pnl_percent: Profit/loss as percentage
            holding_period_days: Number of days position was held
        """
        outcome_record = {
            'decision_id': decision_id,
            'exit_date': exit_date,
            'exit_price': exit_price,
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'holding_period_days': holding_period_days,
            'profitable': pnl > 0
        }
        
        self.outcomes.append(outcome_record)
    
    def get_decisions_by_symbol(self, symbol: str) -> List[Dict]:
        """Get all decisions for a specific symbol"""
        return [d for d in self.decisions if d['symbol'] == symbol]
    
    def get_decisions_by_date_range(self, start_date: date, end_date: date) -> List[Dict]:
        """Get all decisions within a date range"""
        return [
            d for d in self.decisions
            if start_date <= d['date'] <= end_date
        ]
    
    def get_outcomes_for_decisions(self, decision_ids: List[int]) -> List[Dict]:
        """Get outcomes for specific decisions"""
        outcome_dict = {o['decision_id']: o for o in self.outcomes}
        return [outcome_dict[did] for did in decision_ids if did in outcome_dict]
    
    def calculate_quality_metrics(self) -> Dict:
        """
        Calculate decision quality metrics
        
        Returns:
            Dictionary with quality metrics:
            - accuracy: % of profitable decisions
            - signal_correlation: correlation between signal strength and outcome
            - false_positive_rate: bad buys / total buys
            - false_negative_rate: missed opportunities / total opportunities
            - timing_quality: how well decisions timed market movements
        """
        if not self.outcomes:
            return {
                'accuracy': 0.0,
                'signal_correlation': 0.0,
                'false_positive_rate': 0.0,
                'false_negative_rate': 0.0,
                'timing_quality': 0.0,
                'total_decisions': 0,
                'total_outcomes': 0
            }
        
        # Match decisions with outcomes
        decision_dict = {d['decision_id']: d for d in self.decisions}
        matched_data = []
        
        for outcome in self.outcomes:
            decision_id = outcome['decision_id']
            if decision_id in decision_dict:
                decision = decision_dict[decision_id]
                matched_data.append({
                    'decision': decision,
                    'outcome': outcome
                })
        
        if not matched_data:
            return {
                'accuracy': 0.0,
                'signal_correlation': 0.0,
                'false_positive_rate': 0.0,
                'false_negative_rate': 0.0,
                'timing_quality': 0.0,
                'total_decisions': len(self.decisions),
                'total_outcomes': len(self.outcomes)
            }
        
        # Calculate accuracy (% of profitable decisions)
        profitable_count = sum(1 for m in matched_data if m['outcome']['profitable'])
        accuracy = profitable_count / len(matched_data) if matched_data else 0.0
        
        # Calculate signal correlation
        signal_scores = [m['decision'].get('signal_score', 0) for m in matched_data if m['decision'].get('signal_score') is not None]
        pnl_percents = [m['outcome']['pnl_percent'] for m in matched_data if m['decision'].get('signal_score') is not None]
        
        if len(signal_scores) > 1 and len(pnl_percents) > 1:
            signal_correlation = np.corrcoef(signal_scores, pnl_percents)[0, 1]
            if np.isnan(signal_correlation):
                signal_correlation = 0.0
        else:
            signal_correlation = 0.0
        
        # Calculate false positive rate (bad buys)
        buy_decisions = [m for m in matched_data if m['decision']['action'] == 'BUY']
        bad_buys = sum(1 for m in buy_decisions if not m['outcome']['profitable'])
        false_positive_rate = bad_buys / len(buy_decisions) if buy_decisions else 0.0
        
        # Calculate false negative rate (missed opportunities)
        # This is harder - we'd need to track opportunities that were rejected
        # For now, we'll use a simplified metric based on decisions that were rejected
        rejected_decisions = [d for d in self.decisions if not d['should_execute']]
        false_negative_rate = len(rejected_decisions) / len(self.decisions) if self.decisions else 0.0
        
        # Calculate timing quality (how well decisions timed market movements)
        # Simplified: compare holding period to optimal (shorter is better for profitable trades)
        profitable_trades = [m for m in matched_data if m['outcome']['profitable']]
        if profitable_trades:
            avg_holding_profitable = np.mean([m['outcome']['holding_period_days'] for m in profitable_trades])
            avg_holding_all = np.mean([m['outcome']['holding_period_days'] for m in matched_data])
            timing_quality = 1.0 - (avg_holding_profitable / max(avg_holding_all, 1))
            timing_quality = max(0.0, min(1.0, timing_quality))
        else:
            timing_quality = 0.0
        
        return {
            'accuracy': accuracy,
            'signal_correlation': signal_correlation,
            'false_positive_rate': false_positive_rate,
            'false_negative_rate': false_negative_rate,
            'timing_quality': timing_quality,
            'total_decisions': len(self.decisions),
            'total_outcomes': len(self.outcomes),
            'matched_pairs': len(matched_data),
            'profitable_count': profitable_count,
            'bad_buys_count': bad_buys,
            'rejected_decisions_count': len(rejected_decisions)
        }
    
    def get_decision_summary(self) -> Dict:
        """Get summary statistics of all decisions"""
        if not self.decisions:
            return {
                'total_decisions': 0,
                'buy_decisions': 0,
                'sell_decisions': 0,
                'executed_decisions': 0,
                'rejected_decisions': 0
            }
        
        buy_count = sum(1 for d in self.decisions if d['action'] == 'BUY')
        sell_count = sum(1 for d in self.decisions if d['action'] == 'SELL')
        executed_count = sum(1 for d in self.decisions if d['should_execute'])
        rejected_count = len(self.decisions) - executed_count
        
        return {
            'total_decisions': len(self.decisions),
            'buy_decisions': buy_count,
            'sell_decisions': sell_count,
            'executed_decisions': executed_count,
            'rejected_decisions': rejected_count
        }
    
    def export_to_dataframe(self) -> pd.DataFrame:
        """Export decisions and outcomes to pandas DataFrame"""
        if not self.decisions:
            return pd.DataFrame()
        
        # Merge decisions with outcomes
        decision_df = pd.DataFrame(self.decisions)
        outcome_df = pd.DataFrame(self.outcomes)
        
        if not outcome_df.empty:
            merged_df = decision_df.merge(
                outcome_df,
                on='decision_id',
                how='left'
            )
        else:
            merged_df = decision_df.copy()
            merged_df['exit_date'] = None
            merged_df['exit_price'] = None
            merged_df['pnl'] = None
            merged_df['pnl_percent'] = None
            merged_df['holding_period_days'] = None
            merged_df['profitable'] = None
        
        return merged_df
    
    def get_per_symbol_trade_summary(self) -> List[Dict]:
        """
        Get summary of all trades grouped by symbol
        
        Returns:
            List of dictionaries, one per symbol, with:
            - symbol: Stock symbol
            - buy_dates: List of buy dates
            - sell_dates: List of sell dates (None if still open)
            - profits_at_sell: List of PnL at each sell point
            - total_profit: Sum of all profits for this symbol
            - num_trades: Number of trades for this symbol
            - first_buy_date: First buy date
            - last_sell_date: Last sell date (or None if still open)
            - avg_holding_period: Average days held
        """
        # Group decisions by symbol
        symbol_trades = {}
        
        for decision in self.decisions:
            symbol = decision['symbol']
            if symbol not in symbol_trades:
                symbol_trades[symbol] = {
                    'decisions': [],
                    'outcomes': []
                }
            symbol_trades[symbol]['decisions'].append(decision)
        
        # Match with outcomes
        outcome_dict = {o['decision_id']: o for o in self.outcomes}
        
        for symbol, data in symbol_trades.items():
            data['outcomes'] = [
                outcome_dict[d['decision_id']] 
                for d in data['decisions'] 
                if d['decision_id'] in outcome_dict
            ]
        
        # Build summary per symbol
        summary = []
        for symbol, data in symbol_trades.items():
            buy_decisions = [d for d in data['decisions'] if d['action'] == 'BUY']
            sell_decisions = [d for d in data['decisions'] if d['action'] == 'SELL']
            
            buy_dates = [d['date'] for d in buy_decisions]
            
            # Get outcomes for closed positions (matched with buy decisions)
            profits_at_sell = []
            closed_sell_dates = []
            buy_outcome_pairs = []
            
            # Match each buy decision with its outcome
            for buy_decision in buy_decisions:
                decision_id = buy_decision['decision_id']
                if decision_id in outcome_dict:
                    outcome = outcome_dict[decision_id]
                    profits_at_sell.append(outcome['pnl'])
                    closed_sell_dates.append(outcome['exit_date'])
                    buy_outcome_pairs.append({
                        'buy_date': buy_decision['date'].isoformat() if hasattr(buy_decision['date'], 'isoformat') else str(buy_decision['date']),
                        'sell_date': outcome['exit_date'].isoformat() if hasattr(outcome['exit_date'], 'isoformat') else str(outcome['exit_date']),
                        'profit': outcome['pnl'],
                        'profit_percent': outcome['pnl_percent']
                    })
            
            # Check if any positions are still open (buy decision exists but no outcome)
            open_positions = len(buy_decisions) - len(data['outcomes'])
            is_still_open = open_positions > 0
            
            total_profit = sum(p for p in profits_at_sell if p is not None)
            total_profit_percent = sum(o['pnl_percent'] for o in data['outcomes']) / len(data['outcomes']) if data['outcomes'] else 0.0
            
            summary.append({
                'symbol': symbol,
                'first_buy_date': min(buy_dates).isoformat() if buy_dates else None,
                'last_sell_date': max(closed_sell_dates).isoformat() if closed_sell_dates else None,
                'is_still_open': is_still_open,
                'num_trades': len(buy_decisions),
                'buy_dates': [d.isoformat() for d in sorted(buy_dates)],
                'sell_dates': [d.isoformat() for d in sorted(closed_sell_dates)],
                'profits_at_sell': profits_at_sell,
                'total_profit': total_profit,
                'total_profit_percent': total_profit_percent,
                'avg_holding_period': np.mean([o['holding_period_days'] for o in data['outcomes']]) if data['outcomes'] else 0.0,
                'trade_details': buy_outcome_pairs  # Detailed list of buy/sell pairs
            })
        
        return sorted(summary, key=lambda x: x['total_profit'], reverse=True)

