# src/trading/bot.py - Unified Trading Bot with Time Horizon Strategy Support

"""
Unified Trading Bot for PatternIQ

Consolidates AutoTradingBot, MultiAssetTradingBot, and EnhancedMultiAssetBot
into a single configurable implementation with:
- Time horizon strategy support (short/mid/long-term)
- Multi-asset class support (stocks, ETFs, crypto)
- Sophisticated risk management
- Fundamental analysis filters
- Portfolio tracking and performance metrics
"""

import os
import json
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from enum import Enum

import pandas as pd
import yfinance as yf

from src.core.exceptions import TradingBotError, ConfigurationError


class TimeHorizon(Enum):
    """Investment time horizon"""
    SHORT = "short"
    MID = "mid"
    LONG = "long"


class TradingBot:
    """
    Unified trading bot with time horizon strategy support
    
    Features:
    - Time horizon strategies (short/mid/long-term)
    - Multi-asset class support (stocks, ETFs, crypto)
    - Fundamental analysis filters
    - Sophisticated risk management
    - Portfolio tracking and performance metrics
    - State persistence
    """
    
    def __init__(
        self,
        initial_capital: float = 100000.0,
        paper_trading: bool = True,
        max_position_size: float = 0.05,
        max_portfolio_risk: float = 0.20,
        trading_fee_per_trade: float = 0.0,
        enable_multi_asset: bool = True,
        leverage_multiplier: float = 1.0,
        default_time_horizon: str = "mid"
    ):
        """
        Initialize unified trading bot
        
        Args:
            initial_capital: Starting capital amount
            paper_trading: If True, simulate trades without real execution
            max_position_size: Maximum percentage of portfolio in single position
            max_portfolio_risk: Maximum drawdown allowed before risk reduction
            trading_fee_per_trade: Fee per trade
            enable_multi_asset: Enable multi-asset class trading
            leverage_multiplier: Leverage multiplier (1.0 = no leverage, 1.2 = 20% leverage)
            default_time_horizon: Default time horizon strategy ("short", "mid", "long")
        """
        self.logger = logging.getLogger("TradingBot")
        self.initial_capital = initial_capital
        self.effective_capital = initial_capital * leverage_multiplier
        self.leverage_multiplier = leverage_multiplier
        self.leverage_cost = 0.005 if leverage_multiplier > 1.0 else 0.0
        self.paper_trading = paper_trading
        self.max_position_size = max_position_size
        self.max_portfolio_risk = max_portfolio_risk
        self.trading_fee = trading_fee_per_trade
        self.enable_multi_asset = enable_multi_asset
        self.default_time_horizon = TimeHorizon(default_time_horizon)
        
        # Time horizon strategy parameters
        self.time_horizon_params = {
            TimeHorizon.SHORT: {
                "max_position": 0.05,
                "stop_loss": 0.10,
                "take_profit": 0.15,
                "holding_period_days": (1, 14),
                "min_signal_threshold": 0.6
            },
            TimeHorizon.MID: {
                "max_position": 0.05,
                "stop_loss": 0.15,
                "take_profit": 0.25,
                "holding_period_days": (14, 90),
                "min_signal_threshold": 0.5
            },
            TimeHorizon.LONG: {
                "max_position": 0.08,
                "stop_loss": 0.20,
                "take_profit": 0.40,
                "holding_period_days": (90, 365),
                "min_signal_threshold": 0.4
            }
        }
        
        # Multi-asset allocation (if enabled)
        if enable_multi_asset:
            self.asset_allocation = {
                'equity': 0.70,
                'sector_etf': 0.20,
                'crypto_etf': 0.05,
                'international_etf': 0.03,
                'factor_etf': 0.02
            }
            self.asset_risk_params = {
                'equity': {'max_position': 0.05, 'stop_loss': 0.15, 'take_profit': 0.30},
                'sector_etf': {'max_position': 0.08, 'stop_loss': 0.12, 'take_profit': 0.25},
                'crypto_etf': {'max_position': 0.03, 'stop_loss': 0.20, 'take_profit': 0.40},
                'international_etf': {'max_position': 0.06, 'stop_loss': 0.18, 'take_profit': 0.35},
                'factor_etf': {'max_position': 0.04, 'stop_loss': 0.10, 'take_profit': 0.20}
            }
        else:
            self.asset_allocation = {'equity': 1.0}
            self.asset_risk_params = {'equity': {'max_position': 0.05, 'stop_loss': 0.15, 'take_profit': 0.30}}
        
        # Risk management
        self.max_positions = 20
        self.min_trade_size = 1000
        self.rebalance_threshold = 0.02
        
        # Portfolio state
        self.cash_balance = self.effective_capital
        self.positions = {}  # symbol -> {shares, entry_price, entry_date, cost_basis, asset_class, time_horizon}
        self.trade_history = []
        self.start_date = date.today()
        
        # Performance tracking
        self.daily_returns = []
        self.max_drawdown = 0.0
        
        # State directory
        self.state_dir = Path("trading_data")
        self.state_dir.mkdir(exist_ok=True)
        
        # Load existing state
        self._load_state()
        
        self.logger.info(f"Unified Trading Bot initialized:")
        self.logger.info(f"  Capital: ${initial_capital:,.2f}")
        if leverage_multiplier > 1.0:
            self.logger.info(f"  Effective Capital (leveraged): ${self.effective_capital:,.2f}")
        self.logger.info(f"  Mode: {'PAPER' if paper_trading else 'LIVE'}")
        self.logger.info(f"  Multi-Asset: {'ENABLED' if enable_multi_asset else 'DISABLED'}")
        self.logger.info(f"  Default Time Horizon: {default_time_horizon.upper()}")
    
    def _load_state(self) -> None:
        """Load portfolio state from disk"""
        state_file = self.state_dir / "portfolio_state.json"
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                
                self.initial_capital = state.get('initial_capital', self.initial_capital)
                self.effective_capital = state.get('effective_capital', self.effective_capital)
                self.cash_balance = state.get('cash_balance', self.cash_balance)
                self.positions = state.get('positions', {})
                self.trade_history = state.get('trade_history', [])
                self.start_date = datetime.strptime(
                    state.get('start_date', date.today().strftime('%Y-%m-%d')),
                    '%Y-%m-%d'
                ).date()
                self.daily_returns = state.get('daily_returns', [])
                self.max_drawdown = state.get('max_drawdown', 0.0)
                
                self.logger.info(f"Loaded portfolio state: {len(self.positions)} positions, {len(self.trade_history)} trades")
            except Exception as e:
                self.logger.error(f"Error loading portfolio state: {e}")
    
    def _save_state(self) -> None:
        """Save portfolio state to disk"""
        state_file = self.state_dir / "portfolio_state.json"
        
        state = {
            'initial_capital': self.initial_capital,
            'effective_capital': self.effective_capital,
            'cash_balance': self.cash_balance,
            'positions': self.positions,
            'trade_history': self.trade_history,
            'start_date': self.start_date.strftime('%Y-%m-%d'),
            'daily_returns': self.daily_returns,
            'max_drawdown': self.max_drawdown,
            'paper_trading': self.paper_trading,
            'enable_multi_asset': self.enable_multi_asset,
            'default_time_horizon': self.default_time_horizon.value,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        try:
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving portfolio state: {e}")
    
    def _get_asset_class(self, symbol: str) -> str:
        """Determine asset class for a symbol"""
        if not self.enable_multi_asset:
            return 'equity'
        
        sector_etfs = ['XLK', 'XLF', 'XLV', 'XLE', 'XLI', 'XLU', 'XLB', 'XLRE', 'XLP', 'XLY', 'XLC']
        crypto_etfs = ['GBTC', 'ETHE', 'BITO', 'BITI']
        international_etfs = ['EFA', 'EEM', 'VWO', 'FXI', 'EWJ', 'EWZ']
        factor_etfs = ['MTUM', 'QUAL', 'SIZE', 'USMV', 'VLUE']
        
        if symbol in sector_etfs:
            return 'sector_etf'
        elif symbol in crypto_etfs:
            return 'crypto_etf'
        elif symbol in international_etfs:
            return 'international_etf'
        elif symbol in factor_etfs:
            return 'factor_etf'
        else:
            return 'equity'
    
    def _get_time_horizon_from_signal(self, signal_data: Dict) -> TimeHorizon:
        """Extract time horizon from signal data"""
        explain = signal_data.get('explain', {})
        if isinstance(explain, str):
            import json
            try:
                explain = json.loads(explain)
            except:
                explain = {}
        
        time_horizon_str = explain.get('time_horizon', self.default_time_horizon.value)
        try:
            return TimeHorizon(time_horizon_str)
        except ValueError:
            return self.default_time_horizon
    
    def _get_fundamentals_score(self, symbol: str) -> float:
        """Get fundamental quality score (0-1, higher is better)"""
        try:
            from src.providers.sp500_provider import SP500Provider
            provider = SP500Provider()
            fundamentals = provider.get_fundamentals(symbol)
            
            if not fundamentals:
                return 0.5
            
            score = 0.5
            
            # P/E ratio check
            pe = fundamentals.get('pe_ratio')
            if pe and pe > 0:
                if pe < 15:
                    score += 0.2
                elif pe < 25:
                    score += 0.1
                elif pe > 40:
                    score -= 0.2
            
            # Profit margins
            margins = fundamentals.get('profit_margins')
            if margins and margins > 0:
                if margins > 0.15:
                    score += 0.2
                elif margins > 0.05:
                    score += 0.1
                else:
                    score -= 0.1
            
            return max(0.0, min(1.0, score))
        except Exception as e:
            self.logger.warning(f"Could not get fundamentals for {symbol}: {e}")
            return 0.5
    
    def process_daily_report(self, report_date: Union[str, date], time_horizon_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Process daily report and execute trades based on signals
        
        Args:
            report_date: Date of the report to process
            time_horizon_filter: Optional filter by time horizon ("short", "mid", "long")
        
        Returns:
            Dictionary with execution results
        """
        if isinstance(report_date, str):
            report_date = datetime.strptime(report_date, "%Y-%m-%d").date()
        
        self.logger.info(f"🚀 Processing daily report for {report_date}")
        
        # Load report
        reports_dir = Path("reports")
        report_file = reports_dir / f"patterniq_report_{report_date.strftime('%Y%m%d')}.json"
        
        if not report_file.exists():
            self.logger.error(f"Report not found: {report_file}")
            return {"status": "error", "message": f"Report not found for {report_date}"}
        
        try:
            with open(report_file, 'r') as f:
                report = json.load(f)
            
            executed_trades = []
            skipped_trades = []
            
            portfolio_value_before = self.get_portfolio_value()
            
            # Process long recommendations
            top_long = report.get('top_long', [])
            if time_horizon_filter:
                top_long = [r for r in top_long if r.get('time_horizon') == time_horizon_filter]
            
            for position in top_long:
                symbol = position['symbol']
                signal_score = position.get('score', 0.5)
                price = position.get('price', 0.0)
                suggested_size = position.get('position_size', 2.0) / 100.0
                time_horizon_str = position.get('time_horizon', self.default_time_horizon.value)
                
                if price <= 0:
                    skipped_trades.append({"symbol": symbol, "reason": "Invalid price"})
                    self.logger.debug(f"⏭️ Skipping {symbol}: Invalid price")
                    continue
                
                # Get time horizon
                try:
                    time_horizon = TimeHorizon(time_horizon_str)
                except ValueError:
                    time_horizon = self.default_time_horizon
                
                # Get strategy parameters
                strategy_params = self.time_horizon_params[time_horizon]
                
                # Check signal threshold
                if abs(signal_score) < strategy_params['min_signal_threshold']:
                    skipped_trades.append({"symbol": symbol, "reason": f"Signal below threshold ({strategy_params['min_signal_threshold']})"})
                    self.logger.debug(f"⏭️ Skipping {symbol}: Signal {signal_score:.3f} below threshold {strategy_params['min_signal_threshold']}")
                    continue
                
                # Determine asset class
                asset_class = self._get_asset_class(symbol)
                
                # Get asset-specific risk params
                asset_params = self.asset_risk_params.get(asset_class, self.asset_risk_params['equity'])
                
                # Calculate position size
                portfolio_value = self.get_portfolio_value()
                max_position = min(strategy_params['max_position'], asset_params['max_position'])
                target_dollars = portfolio_value * min(suggested_size, max_position)
                
                # Check if we should buy (now returns dict)
                buy_decision = self._should_buy(symbol, signal_score, price, target_dollars, time_horizon, asset_class)
                
                if buy_decision['should_buy']:
                    adjusted_dollars = buy_decision['adjusted_size']
                    shares = int(adjusted_dollars / price)
                    
                    if shares > 0 and target_dollars >= self.min_trade_size:
                        # Execute buy
                        cost = shares * price + self.trading_fee
                        
                        if cost <= self.cash_balance:
                            self.logger.debug(f"✅ Buying {shares} shares of {symbol} @ ${price:.2f} (signal: {signal_score:.3f}, time_horizon: {time_horizon_str})")
                            if symbol in self.positions:
                                # Add to existing position
                                existing = self.positions[symbol]
                                total_shares = existing['shares'] + shares
                                avg_price = ((existing['shares'] * existing['entry_price']) + (shares * price)) / total_shares
                                self.positions[symbol] = {
                                    **existing,
                                    'shares': total_shares,
                                    'entry_price': avg_price
                                }
                            else:
                                # New position
                                self.positions[symbol] = {
                                    'shares': shares,
                                    'entry_price': price,
                                    'entry_date': report_date,
                                    'cost_basis': cost,
                                    'asset_class': asset_class,
                                    'time_horizon': time_horizon.value
                                }
                            
                            self.cash_balance -= cost
                            
                            executed_trades.append({
                                'action': 'BUY',
                                'symbol': symbol,
                                'shares': shares,
                                'price': price,
                                'cost': cost,
                                'time_horizon': time_horizon.value,
                                'asset_class': asset_class,
                                'date': report_date.strftime('%Y-%m-%d')
                            })
                            
                            self.trade_history.append({
                                **executed_trades[-1],
                                'pnl': 0.0  # Will be calculated on exit
                            })
                            
                            self.logger.info(f"✅ Bought {shares} shares of {symbol} @ ${price:.2f} ({time_horizon.value}) - {buy_decision['reason']}")
                        else:
                            skipped_trades.append({"symbol": symbol, "reason": "Insufficient cash"})
                    else:
                        skipped_trades.append({"symbol": symbol, "reason": f"Trade size too small (${adjusted_dollars:.2f})"})
                        self.logger.debug(f"⏭️ Skipping {symbol}: Trade size too small (${adjusted_dollars:.2f})")
                else:
                    skipped_trades.append({"symbol": symbol, "reason": buy_decision['reason']})
                    self.logger.debug(f"⏭️ Skipping {symbol}: {buy_decision['reason']}")
            
            # Check existing positions for exits (including sell signals from report)
            positions_to_close = []
            
            # First, check sell signals from report
            top_short = report.get('top_short', [])
            for position in top_short:
                symbol = position['symbol']
                signal_score = position.get('score', -0.5)
                price = position.get('price', 0.0)
                
                if symbol in self.positions and price > 0:
                    sell_decision = self._should_sell(symbol, price, signal_score)
                    if sell_decision['should_sell']:
                        positions_to_close.append({
                            'symbol': symbol,
                            'shares': sell_decision['shares'],
                            'entry_price': self.positions[symbol]['entry_price'],
                            'exit_price': price,
                            'reason': sell_decision['reason'],
                            'pnl': (price - self.positions[symbol]['entry_price']) * sell_decision['shares'] - self.trading_fee
                        })
            
            # Then check all positions for risk management exits
            for symbol, pos_data in list(self.positions.items()):
                # Skip if already marked for exit
                if any(exit_trade['symbol'] == symbol for exit_trade in positions_to_close):
                    continue
                
                time_horizon_str = pos_data.get('time_horizon', self.default_time_horizon.value)
                try:
                    time_horizon = TimeHorizon(time_horizon_str)
                except ValueError:
                    time_horizon = self.default_time_horizon
                
                # Get current price
                try:
                    ticker = yf.Ticker(symbol)
                    current_price = float(ticker.history(period="1d")['Close'].iloc[-1])
                except:
                    current_price = pos_data['entry_price']  # Fallback
                
                # Use sophisticated sell decision logic
                sell_decision = self._should_sell(symbol, current_price)
                
                if sell_decision['should_sell']:
                    entry_price = pos_data['entry_price']
                    shares = sell_decision['shares']
                    positions_to_close.append({
                        'symbol': symbol,
                        'shares': shares,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'reason': sell_decision['reason'],
                        'pnl': (current_price - entry_price) * shares - self.trading_fee
                    })
                else:
                    # Check holding period (force exit if exceeded)
                    days_held = (report_date - pos_data['entry_date']).days
                    strategy_params = self.time_horizon_params[time_horizon]
                    min_hold, max_hold = strategy_params['holding_period_days']
                    
                    if days_held > max_hold:
                        positions_to_close.append({
                            'symbol': symbol,
                            'shares': pos_data['shares'],
                            'entry_price': pos_data['entry_price'],
                            'exit_price': current_price,
                            'reason': f"Max holding period exceeded ({days_held} days)",
                            'pnl': (current_price - pos_data['entry_price']) * pos_data['shares'] - self.trading_fee
                        })
            
            # Execute exits
            for exit_trade in positions_to_close:
                symbol = exit_trade['symbol']
                shares = exit_trade['shares']
                exit_price = exit_trade['exit_price']
                pnl = exit_trade['pnl']
                
                proceeds = shares * exit_price - self.trading_fee
                self.cash_balance += proceeds
                
                executed_trades.append({
                    'action': 'SELL',
                    'symbol': symbol,
                    'shares': shares,
                    'price': exit_price,
                    'proceeds': proceeds,
                    'pnl': pnl,
                    'reason': exit_trade['reason'],
                    'date': report_date.strftime('%Y-%m-%d')
                })
                
                self.trade_history.append(executed_trades[-1])
                
                del self.positions[symbol]
                
                self.logger.info(f"✅ Sold {shares} shares of {symbol} @ ${exit_price:.2f} ({exit_trade['reason']}) - P&L: ${pnl:+,.2f}")
            
            # Calculate leverage costs
            leverage_cost_daily = self._calculate_leverage_cost()
            if leverage_cost_daily > 0:
                self.cash_balance -= leverage_cost_daily
                self.logger.info(f"Leverage cost: ${leverage_cost_daily:.2f}")
            
            # Save state
            self._save_state()
            
            portfolio_value_after = self.get_portfolio_value()
            daily_return = (portfolio_value_after - portfolio_value_before - leverage_cost_daily) / portfolio_value_before if portfolio_value_before > 0 else 0.0
            
            self.logger.info(f"✅ Trading session complete:")
            self.logger.info(f"   Executed: {len(executed_trades)} trades")
            self.logger.info(f"   Skipped: {len(skipped_trades)} opportunities")
            self.logger.info(f"   Portfolio: ${portfolio_value_before:,.0f} → ${portfolio_value_after:,.0f}")
            self.logger.info(f"   Daily return: {daily_return:.2%}")
            
            return {
                "status": "completed",
                "trades_executed": len(executed_trades),
                "trades_skipped": len(skipped_trades),
                "executed_trades": executed_trades,
                "skipped_trades": skipped_trades,
                "portfolio_value_before": portfolio_value_before,
                "portfolio_value_after": portfolio_value_after,
                "daily_return": daily_return,
                "leverage_cost": leverage_cost_daily,
                "date": report_date.strftime('%Y-%m-%d')
            }
        
        except Exception as e:
            self.logger.error(f"Error processing daily report: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return {"status": "error", "message": str(e)}
    
    def _should_buy(self, symbol: str, signal_score: float, price: float, target_dollars: float,
                   time_horizon: TimeHorizon, asset_class: str) -> Dict[str, Any]:
        """
        Sophisticated buy decision logic with detailed reasoning
        
        Returns:
            Dict with 'should_buy' (bool), 'reason' (str), 'adjusted_size' (float)
        """
        strategy_params = self.time_horizon_params[time_horizon]
        asset_params = self.asset_risk_params.get(asset_class, self.asset_risk_params['equity'])
        
        # Check 1: Minimum trade size
        min_trade_size = 1000 if asset_class == 'equity' else 500
        if target_dollars < min_trade_size:
            return {
                'should_buy': False,
                'reason': f'Trade size ${target_dollars:.0f} below minimum ${min_trade_size:.0f}',
                'adjusted_size': 0
            }
        
        # Check 2: Position count limit
        if len(self.positions) >= self.max_positions:
            return {
                'should_buy': False,
                'reason': f'Portfolio has {len(self.positions)} positions (max: {self.max_positions})',
                'adjusted_size': 0
            }
        
        # Check 3: Signal strength threshold
        signal_threshold = strategy_params['min_signal_threshold']
        if abs(signal_score) < signal_threshold:
            return {
                'should_buy': False,
                'reason': f'Signal {signal_score:.2f} below threshold {signal_threshold:.2f}',
                'adjusted_size': 0
            }
        
        # Check 4: Asset class allocation limits (if multi-asset enabled)
        if self.enable_multi_asset:
            portfolio_value = self.get_portfolio_value()
            max_allocation = self.asset_allocation.get(asset_class, 0.05)
            
            current_asset_value = sum(
                pos_data['shares'] * price
                for pos_symbol, pos_data in self.positions.items()
                if pos_data.get('asset_class') == asset_class
            )
            
            current_allocation = current_asset_value / portfolio_value if portfolio_value > 0 else 0
            if current_allocation >= max_allocation:
                return {
                    'should_buy': False,
                    'reason': f'{asset_class} allocation {current_allocation:.1%} at limit {max_allocation:.1%}',
                    'adjusted_size': 0
                }
        
        # Check 5: Existing position concentration
        if symbol in self.positions:
            existing = self.positions[symbol]
            portfolio_value = self.get_portfolio_value()
            current_value = existing['shares'] * price
            current_weight = current_value / portfolio_value if portfolio_value > 0 else 0
            max_position = min(strategy_params['max_position'], asset_params['max_position'])
            
            if current_weight >= max_position * 0.8:
                return {
                    'should_buy': False,
                    'reason': f'Position {symbol} at {current_weight:.1%} near limit {max_position:.1%}',
                    'adjusted_size': 0
                }
        
        # Check 6: Fundamentals (for equities)
        if asset_class == 'equity':
            fundamentals_score = self._get_fundamentals_score(symbol)
            if fundamentals_score < 0.4:
                return {
                    'should_buy': False,
                    'reason': f'Poor fundamentals (score: {fundamentals_score:.2f})',
                    'adjusted_size': 0
                }
        elif asset_class in ['sector_etf', 'crypto_etf', 'international_etf', 'factor_etf']:
            # Use asset-specific fundamental scoring
            fundamentals_score = self._get_asset_fundamentals_score(symbol, asset_class)
            threshold = 0.3 if asset_class == 'crypto_etf' else 0.35
            if fundamentals_score < threshold:
                return {
                    'should_buy': False,
                    'reason': f'{asset_class} fundamentals below threshold',
                    'adjusted_size': 0
                }
        
        # Check 7: Cash availability
        total_cost = target_dollars + self.trading_fee
        if total_cost > self.cash_balance:
            available_for_stock = self.cash_balance - self.trading_fee
            if available_for_stock < min_trade_size:
                return {
                    'should_buy': False,
                    'reason': f'Insufficient cash (need ${total_cost:.0f}, have ${self.cash_balance:.0f})',
                    'adjusted_size': 0
                }
            target_dollars = available_for_stock
        
        # Adjust position size based on signal quality and fundamentals
        if asset_class == 'equity':
            fundamentals_score = self._get_fundamentals_score(symbol)
        else:
            fundamentals_score = self._get_asset_fundamentals_score(symbol, asset_class)
        
        quality_multiplier = (abs(signal_score) + fundamentals_score) / 2
        
        # Asset class specific multipliers
        asset_multipliers = {
            'equity': 1.0,
            'sector_etf': 1.2,
            'crypto_etf': 0.8,
            'international_etf': 1.0,
            'factor_etf': 1.1
        }
        
        asset_multiplier = asset_multipliers.get(asset_class, 1.0)
        adjusted_dollars = target_dollars * quality_multiplier * asset_multiplier
        
        return {
            'should_buy': True,
            'reason': f'Strong {asset_class} signal ({signal_score:.2f}) + fundamentals ({fundamentals_score:.2f})',
            'adjusted_size': adjusted_dollars
        }
    
    def _get_asset_fundamentals_score(self, symbol: str, asset_class: str) -> float:
        """Get fundamental score for different asset classes"""
        try:
            if asset_class == 'sector_etf':
                return self._get_sector_etf_score(symbol)
            elif asset_class == 'crypto_etf':
                return self._get_crypto_etf_score(symbol)
            else:
                return 0.6  # Neutral-positive for other ETFs
        except Exception as e:
            self.logger.warning(f"Could not get {asset_class} fundamentals for {symbol}: {e}")
            return 0.5
    
    def _get_sector_etf_score(self, symbol: str) -> float:
        """Score sector ETFs based on momentum and relative strength"""
        try:
            data = yf.download(symbol, period="3mo", interval="1d", progress=False)
            if data.empty or len(data) < 20:
                return 0.5
            
            current_price = data['Close'].iloc[-1]
            price_20d = data['Close'].iloc[-20] if len(data) >= 20 else data['Close'].iloc[0]
            price_60d = data['Close'].iloc[-60] if len(data) >= 60 else data['Close'].iloc[0]
            
            momentum_20d = (current_price - price_20d) / price_20d
            momentum_60d = (current_price - price_60d) / price_60d
            
            returns = data['Close'].pct_change().dropna()
            volatility = returns.std() * (252 ** 0.5)
            
            score = 0.5
            
            if momentum_20d > 0.10:
                score += 0.3
            elif momentum_20d > 0.05:
                score += 0.2
            elif momentum_20d > 0:
                score += 0.1
            else:
                score -= 0.2
            
            if momentum_60d > 0.15:
                score += 0.2
            elif momentum_60d < -0.15:
                score -= 0.2
            
            if volatility > 0.30:
                score -= 0.1
            
            return max(0.0, min(1.0, score))
        except Exception as e:
            self.logger.warning(f"Error scoring sector ETF {symbol}: {e}")
            return 0.5
    
    def _get_crypto_etf_score(self, symbol: str) -> float:
        """Score crypto ETFs with higher volatility considerations"""
        try:
            data = yf.download(symbol, period="2mo", interval="1d", progress=False)
            if data.empty or len(data) < 10:
                return 0.5
            
            current_price = data['Close'].iloc[-1]
            price_10d = data['Close'].iloc[-10] if len(data) >= 10 else data['Close'].iloc[0]
            price_30d = data['Close'].iloc[-30] if len(data) >= 30 else data['Close'].iloc[0]
            
            momentum_10d = (current_price - price_10d) / price_10d
            momentum_30d = (current_price - price_30d) / price_30d
            
            score = 0.5
            
            if momentum_10d > 0.15:
                score += 0.3
            elif momentum_10d > 0.05:
                score += 0.2
            elif momentum_10d < -0.20:
                score -= 0.3
            
            if momentum_30d > 0.20:
                score += 0.2
            elif momentum_30d < -0.30:
                score -= 0.2
            
            return max(0.0, min(1.0, score))
        except Exception as e:
            self.logger.warning(f"Error scoring crypto ETF {symbol}: {e}")
            return 0.5
    
    def _should_sell(self, symbol: str, current_price: float, signal_score: Optional[float] = None) -> Dict[str, Any]:
        """Sophisticated sell decision logic with asset-class specific parameters"""
        if symbol not in self.positions:
            return {'should_sell': False, 'reason': 'Not in portfolio', 'shares': 0}
        
        position = self.positions[symbol]
        asset_class = position.get('asset_class', 'equity')
        time_horizon_str = position.get('time_horizon', self.default_time_horizon.value)
        
        try:
            time_horizon = TimeHorizon(time_horizon_str)
        except ValueError:
            time_horizon = self.default_time_horizon
        
        strategy_params = self.time_horizon_params[time_horizon]
        asset_params = self.asset_risk_params.get(asset_class, self.asset_risk_params['equity'])
        
        entry_price = position['entry_price']
        shares = position['shares']
        
        # Calculate P&L
        current_value = shares * current_price
        cost_basis = shares * entry_price
        pnl_percent = (current_value - cost_basis) / cost_basis
        
        # Asset-specific stop loss and take profit
        stop_loss = -strategy_params['stop_loss']
        take_profit = strategy_params['take_profit']
        
        # Stop loss check
        if pnl_percent < stop_loss:
            return {
                'should_sell': True,
                'reason': f'{asset_class} stop loss triggered: {pnl_percent:.1%} loss',
                'shares': shares
            }
        
        # Take profit check
        if pnl_percent > take_profit:
            return {
                'should_sell': True,
                'reason': f'{asset_class} take profit triggered: {pnl_percent:.1%} gain',
                'shares': shares
            }
        
        # Signal-based sell
        if signal_score is not None:
            signal_thresholds = {
                'equity': -0.6,
                'sector_etf': -0.4,
                'crypto_etf': -0.3,
                'international_etf': -0.5,
                'factor_etf': -0.5
            }
            
            threshold = signal_thresholds.get(asset_class, -0.6)
            if signal_score < threshold:
                return {
                    'should_sell': True,
                    'reason': f'Strong {asset_class} sell signal: {signal_score:.2f}',
                    'shares': shares
                }
        
        # Fundamental deterioration (for equities)
        if asset_class == 'equity':
            fundamental_score = self._get_fundamentals_score(symbol)
            if fundamental_score < 0.3:
                return {
                    'should_sell': True,
                    'reason': f'Deteriorating fundamentals: {fundamental_score:.2f}',
                    'shares': shares
                }
        
        return {'should_sell': False, 'reason': 'Hold position', 'shares': 0}
    
    def _calculate_leverage_cost(self) -> float:
        """Calculate daily leverage borrowing cost"""
        if self.leverage_multiplier <= 1.0:
            return 0.0
        
        borrowed_amount = self.effective_capital - self.initial_capital
        if borrowed_amount > 0:
            daily_cost = borrowed_amount * (self.leverage_cost / 365)
            return daily_cost
        return 0.0
    
    def get_portfolio_value(self) -> float:
        """Calculate current portfolio value"""
        positions_value = 0.0
        
        for symbol, pos_data in self.positions.items():
            try:
                ticker = yf.Ticker(symbol)
                current_price = float(ticker.history(period="1d")['Close'].iloc[-1])
                positions_value += pos_data['shares'] * current_price
            except:
                # Fallback to entry price if can't get current price
                positions_value += pos_data['shares'] * pos_data['entry_price']
        
        return self.cash_balance + positions_value
    
    def get_portfolio_status(self) -> Dict[str, Any]:
        """Get comprehensive portfolio status"""
        current_value = self.get_portfolio_value()
        
        # Account for leverage in return calculation
        if self.leverage_multiplier > 1.0:
            effective_return = (current_value - self.effective_capital) / self.initial_capital
        else:
            effective_return = (current_value - self.initial_capital) / self.initial_capital
        
        # Calculate allocation by time horizon and asset class
        allocation_by_horizon = {"short": 0.0, "mid": 0.0, "long": 0.0}
        allocation_by_class = {}
        positions_detail = []
        total_position_value = 0.0
        
        portfolio_value = current_value
        for symbol, pos_data in self.positions.items():
            try:
                ticker = yf.Ticker(symbol)
                current_price = float(ticker.history(period="1d")['Close'].iloc[-1])
                position_value = pos_data['shares'] * current_price
                unrealized_pnl = position_value - pos_data.get('cost_basis', pos_data['shares'] * pos_data['entry_price'])
                unrealized_pnl_pct = (unrealized_pnl / pos_data.get('cost_basis', pos_data['shares'] * pos_data['entry_price'])) * 100 if pos_data.get('cost_basis', 0) > 0 else 0
            except:
                current_price = pos_data['entry_price']
                position_value = pos_data['shares'] * current_price
                unrealized_pnl = 0
                unrealized_pnl_pct = 0
            
            total_position_value += position_value
            
            time_horizon = pos_data.get('time_horizon', 'mid')
            asset_class = pos_data.get('asset_class', 'equity')
            
            if portfolio_value > 0:
                pct = position_value / portfolio_value
                allocation_by_horizon[time_horizon] = allocation_by_horizon.get(time_horizon, 0.0) + pct
                allocation_by_class[asset_class] = allocation_by_class.get(asset_class, 0.0) + pct
            
            positions_detail.append({
                'symbol': symbol,
                'shares': pos_data['shares'],
                'entry_price': pos_data['entry_price'],
                'current_price': current_price,
                'entry_date': pos_data.get('entry_date', self.start_date).strftime('%Y-%m-%d') if isinstance(pos_data.get('entry_date'), date) else str(pos_data.get('entry_date', '')),
                'cost_basis': pos_data.get('cost_basis', pos_data['shares'] * pos_data['entry_price']),
                'current_value': position_value,
                'unrealized_pnl': unrealized_pnl,
                'unrealized_pnl_percent': unrealized_pnl_pct,
                'weight': (position_value / portfolio_value) * 100 if portfolio_value > 0 else 0,
                'time_horizon': time_horizon,
                'asset_class': asset_class
            })
        
        # Calculate realized P&L
        realized_pnl = sum(trade.get('pnl', 0) for trade in self.trade_history if trade.get('action') == 'SELL')
        total_fees_paid = sum(trade.get('fees', self.trading_fee) for trade in self.trade_history)
        
        # Calculate leverage costs
        days_active = (date.today() - self.start_date).days
        total_leverage_cost = self._calculate_leverage_cost() * days_active if days_active > 0 else 0
        
        return {
            "initial_capital": self.initial_capital,
            "effective_capital": self.effective_capital if self.leverage_multiplier > 1.0 else self.initial_capital,
            "leverage_multiplier": self.leverage_multiplier,
            "current_value": current_value,
            "total_return": f"{effective_return:+.2%}",
            "total_return_num": effective_return,
            "cash_balance": self.cash_balance,
            "positions_value": total_position_value,
            "total_pnl": current_value - self.initial_capital,
            "realized_pnl": realized_pnl,
            "unrealized_pnl": current_value - self.initial_capital - realized_pnl,
            "total_fees_paid": total_fees_paid,
            "leverage_cost_total": total_leverage_cost,
            "positions_count": len(self.positions),
            "positions_detail": positions_detail,
            "total_trades": len(self.trade_history),
            "allocation_by_horizon": allocation_by_horizon,
            "allocation_by_class": allocation_by_class,
            "target_allocation": self.asset_allocation if self.enable_multi_asset else {'equity': 1.0},
            "paper_trading": self.paper_trading,
            "enable_multi_asset": self.enable_multi_asset,
            "start_date": self.start_date.strftime('%Y-%m-%d'),
            "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

