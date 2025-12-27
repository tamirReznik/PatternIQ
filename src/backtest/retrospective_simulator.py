#!/usr/bin/env python3
"""
Retrospective Simulator for Day-by-Day Trading Analysis
Simulates bot decisions over historical periods and evaluates performance
"""

import logging
import os
from typing import Dict, List, Optional
from datetime import date, datetime, timedelta
from pathlib import Path
import json
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text

from src.trading.bot import TradingBot
from src.backtest.decision_tracker import DecisionTracker


class RetrospectiveSimulator:
    """
    Day-by-day retrospective simulation of trading bot decisions
    Evaluates both profitability and decision quality
    """
    
    def __init__(
        self,
        start_date: date,
        end_date: date,
        initial_capital: float = 100000.0,
        time_horizon_filter: Optional[str] = None
    ):
        self.logger = logging.getLogger("RetrospectiveSimulator")
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.time_horizon_filter = time_horizon_filter
        
        # Setup database connection
        db_url = os.getenv("PATTERNIQ_DB_URL", "sqlite:///data/patterniq.db")
        self.engine = create_engine(db_url)
        
        # Initialize bot and tracker
        self.bot = TradingBot(
            initial_capital=initial_capital,
            paper_trading=True,
            max_position_size=0.05,
            enable_multi_asset=True
        )
        self.decision_tracker = DecisionTracker()
        
        # Simulation state
        self.daily_decisions: List[Dict] = []
        self.daily_portfolio_values: List[Dict] = []
        self.trading_days: List[date] = []
        
        # Statistics tracking
        self.reports_loaded = 0
        self.reports_generated = 0
        self.days_with_signals = 0
        self.days_without_signals = 0
    
    def _get_trading_days(self) -> List[date]:
        """Get list of trading days in date range"""
        # Get dates from database that have price data
        is_sqlite = 'sqlite' in str(self.engine.url).lower()
        
        with self.engine.connect() as conn:
            if is_sqlite:
                # SQLite: Use named parameters (SQLAlchemy 2.0+ requires this)
                query = """
                    SELECT DISTINCT DATE(t) as trade_date
                    FROM bars_1d
                    WHERE DATE(t) BETWEEN :start_date AND :end_date
                    ORDER BY trade_date
                """
                result = conn.execute(text(query), {
                    "start_date": self.start_date,
                    "end_date": self.end_date
                })
            else:
                query = """
                    SELECT DISTINCT t::date as trade_date
                    FROM bars_1d
                    WHERE t::date BETWEEN :start_date AND :end_date
                    ORDER BY trade_date
                """
                result = conn.execute(text(query), {
                    "start_date": self.start_date,
                    "end_date": self.end_date
                })
            
            dates = [row[0] for row in result.fetchall()]
            if dates and isinstance(dates[0], str):
                dates = [datetime.strptime(d, '%Y-%m-%d').date() for d in dates]
            return dates
    
    def _load_report_for_date(self, report_date: date) -> Optional[Dict]:
        """Load daily report for a specific date, generating if missing"""
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        report_file = reports_dir / f"patterniq_report_{report_date.strftime('%Y%m%d')}.json"
        
        # If report exists, load it
        if report_file.exists():
            try:
                with open(report_file, 'r') as f:
                    self.reports_loaded = getattr(self, 'reports_loaded', 0) + 1
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Error loading existing report for {report_date}: {e}")
        
        # Report missing - generate on-the-fly from database
        self.logger.info(f"Report missing for {report_date}, generating from database signals...")
        try:
            from src.report.generator import generate_daily_report
            result = generate_daily_report(report_date.strftime('%Y-%m-%d'))
            
            if result and result.get('status') == 'success':
                # Report was generated and saved, now load it
                if report_file.exists():
                    with open(report_file, 'r') as f:
                        report_data = json.load(f)
                    
                    # Check if report contains sample data (no real signals)
                    risk_alerts = report_data.get('risk_alerts', [])
                    is_sample_data = any('Sample data' in str(alert) for alert in risk_alerts)
                    
                    if is_sample_data:
                        self.logger.warning(f"Report generated but contains sample data (no real signals) for {report_date}")
                        return None
                    
                    self.reports_generated += 1
                    return report_data
                else:
                    self.logger.warning(f"Report generation succeeded but file not found: {report_file}")
                    return None
            else:
                error_msg = result.get('message', 'Unknown error') if result else 'No result returned'
                self.logger.warning(f"Report generation failed for {report_date}: {error_msg}")
                return None
        except Exception as e:
            self.logger.error(f"Error generating report for {report_date}: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return None
    
    def _get_price_for_symbol(self, symbol: str, price_date: date) -> Optional[float]:
        """Get price for a symbol on a specific date"""
        is_sqlite = 'sqlite' in str(self.engine.url).lower()
        
        with self.engine.connect() as conn:
            if is_sqlite:
                # SQLite: Use named parameters (SQLAlchemy 2.0+ requires this)
                query = """
                    SELECT adj_c
                    FROM bars_1d
                    WHERE symbol = :symbol
                    AND DATE(t) = :price_date
                    ORDER BY t DESC
                    LIMIT 1
                """
                result = conn.execute(text(query), {
                    "symbol": symbol,
                    "price_date": price_date
                })
            else:
                query = """
                    SELECT adj_c
                    FROM bars_1d
                    WHERE symbol = :symbol
                    AND t::date = :price_date
                    ORDER BY t DESC
                    LIMIT 1
                """
                result = conn.execute(text(query), {
                    "symbol": symbol,
                    "price_date": price_date
                })
            
            row = result.fetchone()
            return float(row[0]) if row else None
    
    def _simulate_day(self, current_date: date) -> Dict:
        """Simulate one day of trading"""
        day_result = {
            'date': current_date,
            'decisions': [],
            'trades_executed': [],
            'portfolio_value': self.bot.get_portfolio_value(),
            'cash_balance': self.bot.cash_balance,
            'positions_count': len(self.bot.positions)
        }
        
        # Load or generate report for this date
        report = self._load_report_for_date(current_date)
        if not report:
            day_result['status'] = 'no_signals'
            day_result['reason'] = 'No signals available in database for this date'
            self.days_without_signals += 1
            return day_result
        
        self.days_with_signals += 1
        
        # Process report with bot
        try:
            result = self.bot.process_daily_report(current_date, self.time_horizon_filter)
            day_result['status'] = result.get('status', 'completed')
            day_result['trades_executed'] = result.get('executed_trades', [])
            
            # Track decisions
            for trade in result.get('executed_trades', []):
                symbol = trade.get('symbol', '')
                action = trade.get('action', 'BUY')
                
                # Get decision details from bot's decision logic
                decision_dict = {'should_buy': action == 'BUY', 'should_sell': action == 'SELL'}
                
                decision_id = self.decision_tracker.record_decision(
                    date=current_date,
                    symbol=symbol,
                    action=action,
                    decision=decision_dict,
                    price=trade.get('price', 0.0),
                    signal_score=trade.get('signal_score'),
                    time_horizon=trade.get('time_horizon'),
                    asset_class=trade.get('asset_class')
                )
                day_result['decisions'].append(decision_id)
                
                # Store decision_id in position for outcome tracking
                # Note: For existing positions, we keep the original decision_id
                # but track multiple buys with separate decision_ids
                if symbol in self.bot.positions:
                    # If position already has a decision_id, keep it (first buy)
                    # For tracking purposes, we'll use the first decision_id for the position
                    if 'decision_id' not in self.bot.positions[symbol]:
                        self.bot.positions[symbol]['decision_id'] = decision_id
                    # Update entry_date to latest buy
                    self.bot.positions[symbol]['entry_date'] = current_date
                    # Track all decision_ids for this position (for future multi-decision tracking)
                    if 'all_decision_ids' not in self.bot.positions[symbol]:
                        self.bot.positions[symbol]['all_decision_ids'] = []
                    self.bot.positions[symbol]['all_decision_ids'].append(decision_id)
            
            # Update portfolio value
            day_result['portfolio_value'] = self.bot.get_portfolio_value()
            day_result['cash_balance'] = self.bot.cash_balance
            day_result['positions_count'] = len(self.bot.positions)
            
        except Exception as e:
            self.logger.error(f"Error simulating day {current_date}: {e}")
            day_result['status'] = 'error'
            day_result['error'] = str(e)
        
        return day_result
    
    def _update_outcomes(self, current_date: date):
        """Update outcomes for closed positions and execute sells"""
        # Check for positions that should be closed
        for symbol, position in list(self.bot.positions.items()):
            current_price = self._get_price_for_symbol(symbol, current_date)
            if not current_price:
                continue
            
            # Check if position should be sold
            sell_decision = self.bot._should_sell(symbol, current_price)
            
            if sell_decision.get('should_sell'):
                entry_price = position['entry_price']
                shares = position['shares']
                entry_date = position.get('entry_date', current_date)
                
                pnl = (current_price - entry_price) * shares
                pnl_percent = (current_price - entry_price) / entry_price
                holding_period = (current_date - entry_date).days
                
                # Find decision ID for this position (the original BUY decision)
                buy_decision_id = position.get('decision_id')
                
                # Record SELL decision first (so it can be tracked)
                sell_decision_dict = {'should_sell': True, 'reason': sell_decision.get('reason', 'Risk management exit')}
                sell_decision_id = self.decision_tracker.record_decision(
                    date=current_date,
                    symbol=symbol,
                    action='SELL',
                    decision=sell_decision_dict,
                    price=current_price,
                    signal_score=None,  # Sell decisions don't have signal scores
                    time_horizon=position.get('time_horizon'),
                    asset_class=position.get('asset_class')
                )
                
                # Execute the sell (same logic as in bot.process_daily_report)
                proceeds = shares * current_price - self.bot.trading_fee
                self.bot.cash_balance += proceeds
                
                # Record trade history
                self.bot.trade_history.append({
                    'date': current_date,
                    'symbol': symbol,
                    'action': 'SELL',
                    'shares': shares,
                    'price': current_price,
                    'pnl': pnl,
                    'reason': sell_decision.get('reason', 'Risk management exit')
                })
                
                # Remove position
                del self.bot.positions[symbol]
                
                # Record outcome for the original BUY decision (not the SELL decision)
                # The outcome is linked to the BUY decision that opened the position
                if buy_decision_id is not None:
                    self.decision_tracker.record_outcome(
                        decision_id=buy_decision_id,
                        exit_date=current_date,
                        exit_price=current_price,
                        pnl=pnl,
                        pnl_percent=pnl_percent,
                        holding_period_days=holding_period
                    )
                    self.logger.debug(f"✅ Executed sell for {symbol}: PnL=${pnl:.2f} ({pnl_percent:.2%}), held {holding_period} days (buy_decision_id: {buy_decision_id})")
                else:
                    self.logger.warning(f"Executed sell for {symbol} but no buy_decision_id found, cannot record outcome")
    
    def _close_all_positions(self, final_date: date):
        """Close all remaining positions at end of simulation and record outcomes"""
        self.logger.info(f"Closing all remaining positions on {final_date}")
        
        closed_count = 0
        for symbol, position in list(self.bot.positions.items()):
            current_price = self._get_price_for_symbol(symbol, final_date)
            if not current_price:
                self.logger.warning(f"Could not get price for {symbol} on {final_date}, skipping")
                continue
            
            entry_price = position['entry_price']
            shares = position['shares']
            entry_date = position.get('entry_date', final_date)
            
            pnl = (current_price - entry_price) * shares
            pnl_percent = (current_price - entry_price) / entry_price
            holding_period = (final_date - entry_date).days
            
            # Record SELL decision for closing position
            sell_decision_dict = {'should_sell': True, 'reason': 'Position closed at end of simulation'}
            sell_decision_id = self.decision_tracker.record_decision(
                date=final_date,
                symbol=symbol,
                action='SELL',
                decision=sell_decision_dict,
                price=current_price,
                signal_score=None,
                time_horizon=position.get('time_horizon'),
                asset_class=position.get('asset_class')
            )
            
            # Record outcome for all decision_ids associated with this position
            decision_ids = position.get('all_decision_ids', [])
            if not decision_ids:
                # Fallback to single decision_id
                decision_id = position.get('decision_id')
                if decision_id is not None:
                    decision_ids = [decision_id]
            
            if decision_ids:
                # Record outcome for the primary decision_id (first buy)
                primary_decision_id = decision_ids[0]
                self.decision_tracker.record_outcome(
                    decision_id=primary_decision_id,
                    exit_date=final_date,
                    exit_price=current_price,
                    pnl=pnl,
                    pnl_percent=pnl_percent,
                    holding_period_days=holding_period
                )
                closed_count += 1
                self.logger.debug(f"Recorded outcome for {symbol}: PnL=${pnl:.2f} ({pnl_percent:.2%}), held {holding_period} days (buy_decision_id: {primary_decision_id})")
            else:
                self.logger.warning(f"No decision_id found for position {symbol}, cannot record outcome")
        
        self.logger.info(f"Closed {closed_count} positions and recorded outcomes")
    
    def run_day_by_day(self) -> Dict:
        """
        Run day-by-day simulation
        
        Returns:
            Dictionary with simulation results:
            - daily_decisions: List of daily decision summaries
            - profitability_metrics: Calculated profitability metrics
            - decision_quality_metrics: Calculated decision quality metrics
        """
        self.logger.info(f"Starting retrospective simulation: {self.start_date} to {self.end_date}")
        
        # Get trading days
        trading_days = self._get_trading_days()
        self.logger.info(f"Found {len(trading_days)} trading days")
        
        if not trading_days:
            return {
                'status': 'error',
                'message': 'No trading days found in date range'
            }
        
        # Simulate each day
        for i, current_date in enumerate(trading_days):
            if i % 50 == 0:
                self.logger.info(f"Simulating day {i+1}/{len(trading_days)}: {current_date}")
            
            # Update outcomes for existing positions
            self._update_outcomes(current_date)
            
            # Simulate day
            day_result = self._simulate_day(current_date)
            self.daily_decisions.append(day_result)
            self.daily_portfolio_values.append({
                'date': current_date,
                'portfolio_value': day_result['portfolio_value'],
                'cash_balance': day_result['cash_balance'],
                'positions_count': day_result['positions_count']
            })
            self.trading_days.append(current_date)
        
        # Close all remaining positions and record outcomes
        if self.bot.positions:
            final_date = trading_days[-1] if trading_days else self.end_date
            self._close_all_positions(final_date)
        
        # Calculate metrics
        profitability_metrics = self._calculate_profitability_metrics()
        decision_quality_metrics = self.decision_tracker.calculate_quality_metrics()
        per_symbol_trades = self.decision_tracker.get_per_symbol_trade_summary()
        
        return {
            'status': 'completed',
            'simulation_period': {
                'start': self.start_date.isoformat(),
                'end': self.end_date.isoformat(),
                'trading_days': len(trading_days)
            },
            'daily_decisions': self.daily_decisions,
            'daily_portfolio_values': self.daily_portfolio_values,
            'profitability_metrics': profitability_metrics,
            'decision_quality_metrics': decision_quality_metrics,
            'decision_summary': self.decision_tracker.get_decision_summary(),
            'per_symbol_trades': per_symbol_trades,
            'report_statistics': {
                'reports_generated': self.reports_generated,
                'reports_loaded': self.reports_loaded,
                'days_with_signals': self.days_with_signals,
                'days_without_signals': self.days_without_signals
            }
        }
    
    def _calculate_profitability_metrics(self) -> Dict:
        """Calculate profitability metrics"""
        if not self.daily_portfolio_values:
            return {
                'total_return': 0.0,
                'annualized_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'average_holding_period': 0.0
            }
        
        # Calculate returns
        portfolio_values = [pv['portfolio_value'] for pv in self.daily_portfolio_values]
        initial_value = portfolio_values[0] if portfolio_values else self.initial_capital
        final_value = portfolio_values[-1] if portfolio_values else self.initial_capital
        
        total_return = (final_value - initial_value) / initial_value
        
        # Annualized return
        days = len(self.daily_portfolio_values)
        years = days / 252.0  # Trading days per year
        if years > 0:
            annualized_return = (1 + total_return) ** (1 / years) - 1
        else:
            annualized_return = 0.0
        
        # Daily returns
        daily_returns = []
        for i in range(1, len(portfolio_values)):
            daily_return = (portfolio_values[i] - portfolio_values[i-1]) / portfolio_values[i-1]
            daily_returns.append(daily_return)
        
        # Sharpe ratio (assuming 252 trading days, risk-free rate = 0)
        if daily_returns and np.std(daily_returns) > 0:
            sharpe_ratio = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252)
        else:
            sharpe_ratio = 0.0
        
        # Max drawdown
        cumulative = np.array(portfolio_values)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = abs(np.min(drawdown)) if len(drawdown) > 0 else 0.0
        
        # Win rate and profit factor from outcomes
        outcomes = self.decision_tracker.outcomes
        if outcomes:
            profitable = [o for o in outcomes if o['profitable']]
            win_rate = len(profitable) / len(outcomes) if outcomes else 0.0
            
            profits = [o['pnl'] for o in outcomes if o['pnl'] > 0]
            losses = [abs(o['pnl']) for o in outcomes if o['pnl'] < 0]
            
            gross_profit = sum(profits) if profits else 0.0
            gross_loss = sum(losses) if losses else 0.0
            
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
            
            holding_periods = [o['holding_period_days'] for o in outcomes]
            avg_holding_period = np.mean(holding_periods) if holding_periods else 0.0
        else:
            win_rate = 0.0
            profit_factor = 0.0
            avg_holding_period = 0.0
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'average_holding_period': avg_holding_period,
            'initial_capital': initial_value,
            'final_capital': final_value,
            'total_trades': len(outcomes) if outcomes else 0
        }

