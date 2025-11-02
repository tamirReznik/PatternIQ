# src/trading/simulator.py - Enhanced automated trading bot with sophisticated decision making

import os
import json
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
import pandas as pd
from typing import Dict, List, Optional, Any, Union

class AutoTradingBot:
    """
    Enhanced automated trading bot with sophisticated decision-making

    Features:
    - Trading fees consideration (simulates real brokerage costs)
    - Fundamental analysis filters (avoid overvalued stocks)
    - Position sizing with risk management
    - Smart entry/exit logic (don't always follow signals blindly)
    - Portfolio concentration limits
    - Transaction cost optimization
    """

    def __init__(self, initial_capital: float = 100000.0, paper_trading: bool = True,
                 max_position_size: float = 0.05, max_portfolio_risk: float = 0.20,
                 trading_fee_per_trade: float = 0.0, expense_ratio: float = 0.0005):
        """
        Initialize the enhanced trading bot

        Args:
            initial_capital: Starting capital amount
            paper_trading: If True, simulate trades without real execution
            max_position_size: Maximum percentage of portfolio in single position (5% default)
            max_portfolio_risk: Maximum drawdown allowed before risk reduction
            trading_fee_per_trade: Fee per trade (e.g., $0 for most modern brokers)
            expense_ratio: Annual expense ratio (0.05% default, like ETF fees)
        """
        self.logger = logging.getLogger("AutoTradingBot")
        self.initial_capital = initial_capital
        self.paper_trading = paper_trading
        self.max_position_size = max_position_size
        self.max_portfolio_risk = max_portfolio_risk
        self.trading_fee = trading_fee_per_trade
        self.expense_ratio = expense_ratio

        # Enhanced risk management
        self.max_positions = 20  # Maximum number of positions
        self.min_trade_size = 1000  # Minimum trade size to justify fees
        self.rebalance_threshold = 0.02  # 2% deviation triggers rebalance

        # Initialize portfolio state
        self.cash_balance = initial_capital
        self.positions = {}  # symbol -> {shares, entry_price, entry_date, cost_basis}
        self.trade_history = []
        self.start_date = date.today()

        # Performance tracking
        self.daily_returns = []
        self.max_drawdown = 0.0

        # Create state directory if it doesn't exist
        self.state_dir = Path("trading_data")
        self.state_dir.mkdir(exist_ok=True)

        # Try to load existing state
        self._load_state()

        self.logger.info(f"Enhanced trading bot initialized:")
        self.logger.info(f"  Capital: ${initial_capital:,.2f}")
        self.logger.info(f"  Mode: {'PAPER' if paper_trading else 'LIVE'}")
        self.logger.info(f"  Max position size: {max_position_size:.1%}")
        self.logger.info(f"  Trading fee: ${trading_fee_per_trade:.2f}")
        self.logger.info(f"  Min trade size: ${self.min_trade_size:,.0f}")

    def _load_state(self) -> None:
        """Load portfolio state from disk if available"""
        state_file = self.state_dir / "portfolio_state.json"
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)

                # Restore state
                self.initial_capital = state.get('initial_capital', self.initial_capital)
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

        # Prepare state for saving
        state = {
            'initial_capital': self.initial_capital,
            'cash_balance': self.cash_balance,
            'positions': self.positions,
            'trade_history': self.trade_history,
            'start_date': self.start_date.strftime('%Y-%m-%d'),
            'daily_returns': self.daily_returns,
            'max_drawdown': self.max_drawdown,
            'paper_trading': self.paper_trading,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        try:
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)

            self.logger.info(f"Saved portfolio state to {state_file}")
        except Exception as e:
            self.logger.error(f"Error saving portfolio state: {e}")

    def _get_fundamentals_score(self, symbol: str) -> float:
        """
        Get fundamental quality score for a stock (0-1, higher is better)
        This helps avoid overvalued or risky stocks
        """
        try:
            from src.providers.sp500_provider import SP500Provider
            provider = SP500Provider()
            fundamentals = provider.get_fundamentals(symbol)

            if not fundamentals:
                return 0.5  # Neutral score if no data

            score = 0.5  # Start neutral

            # P/E ratio check (prefer reasonable valuations)
            pe = fundamentals.get('pe_ratio')
            if pe and pe > 0:
                if pe < 15:
                    score += 0.2  # Undervalued
                elif pe < 25:
                    score += 0.1  # Reasonable
                elif pe > 40:
                    score -= 0.2  # Overvalued

            # Profit margins (prefer profitable companies)
            margins = fundamentals.get('profit_margins')
            if margins and margins > 0:
                if margins > 0.15:
                    score += 0.2  # High margins
                elif margins > 0.05:
                    score += 0.1  # Decent margins
                else:
                    score -= 0.1  # Low margins

            # Debt to equity (prefer lower debt)
            debt_ratio = fundamentals.get('debt_to_equity')
            if debt_ratio and debt_ratio >= 0:
                if debt_ratio < 0.3:
                    score += 0.1  # Low debt
                elif debt_ratio > 1.0:
                    score -= 0.2  # High debt

            # Return on equity (prefer efficient companies)
            roe = fundamentals.get('return_on_equity')
            if roe and roe > 0:
                if roe > 0.15:
                    score += 0.1  # High ROE
                elif roe < 0.05:
                    score -= 0.1  # Low ROE

            return max(0.0, min(1.0, score))  # Clamp to 0-1

        except Exception as e:
            self.logger.warning(f"Could not get fundamentals for {symbol}: {e}")
            return 0.5  # Neutral if error

    def _should_buy(self, symbol: str, signal_score: float, price: float, target_dollars: float) -> Dict[str, Any]:
        """
        Sophisticated decision logic for whether to buy a stock

        Returns:
            Dict with 'should_buy' (bool), 'reason' (str), 'adjusted_size' (float)
        """
        reasons = []

        # Check 1: Minimum trade size (avoid tiny trades that are eaten by fees)
        if target_dollars < self.min_trade_size:
            return {
                'should_buy': False,
                'reason': f'Trade size ${target_dollars:.0f} below minimum ${self.min_trade_size:.0f}',
                'adjusted_size': 0
            }

        # Check 2: Portfolio concentration (don't over-concentrate)
        if len(self.positions) >= self.max_positions:
            return {
                'should_buy': False,
                'reason': f'Portfolio already has {len(self.positions)} positions (max: {self.max_positions})',
                'adjusted_size': 0
            }

        # Check 3: Already own this stock
        if symbol in self.positions:
            current_value = self.positions[symbol]['shares'] * price
            portfolio_value = self.get_portfolio_value()
            current_weight = current_value / portfolio_value

            if current_weight > self.max_position_size * 0.8:  # Already near max
                return {
                    'should_buy': False,
                    'reason': f'Already own {current_weight:.1%} of {symbol} (near max {self.max_position_size:.1%})',
                    'adjusted_size': 0
                }

        # Check 4: Signal strength threshold
        if signal_score < 0.6:  # Only trade on strong signals
            return {
                'should_buy': False,
                'reason': f'Signal score {signal_score:.2f} below threshold 0.6',
                'adjusted_size': 0
            }

        # Check 5: Fundamental quality
        fundamental_score = self._get_fundamentals_score(symbol)
        if fundamental_score < 0.4:  # Avoid fundamentally weak stocks
            return {
                'should_buy': False,
                'reason': f'Poor fundamentals (score: {fundamental_score:.2f})',
                'adjusted_size': 0
            }

        # Check 6: Cash availability (including fees)
        total_cost = target_dollars + self.trading_fee
        if total_cost > self.cash_balance:
            # Adjust size to fit available cash
            available_for_stock = self.cash_balance - self.trading_fee
            if available_for_stock < self.min_trade_size:
                return {
                    'should_buy': False,
                    'reason': f'Insufficient cash (need ${total_cost:.0f}, have ${self.cash_balance:.0f})',
                    'adjusted_size': 0
                }
            target_dollars = available_for_stock

        # Adjust position size based on signal and fundamental quality
        quality_multiplier = (signal_score + fundamental_score) / 2
        adjusted_dollars = target_dollars * quality_multiplier

        return {
            'should_buy': True,
            'reason': f'Strong signal ({signal_score:.2f}) + good fundamentals ({fundamental_score:.2f})',
            'adjusted_size': adjusted_dollars
        }

    def _should_sell(self, symbol: str, current_price: float, signal_score: float = None) -> Dict[str, Any]:
        """
        Sophisticated decision logic for whether to sell a stock
        """
        if symbol not in self.positions:
            return {'should_sell': False, 'reason': 'Not in portfolio', 'shares': 0}

        position = self.positions[symbol]
        entry_price = position['entry_price']
        shares = position['shares']

        # Calculate current P&L
        current_value = shares * current_price
        cost_basis = shares * entry_price
        pnl_percent = (current_value - cost_basis) / cost_basis

        # Sell trigger 1: Stop loss (protect against big losses)
        if pnl_percent < -0.15:  # 15% stop loss
            return {
                'should_sell': True,
                'reason': f'Stop loss triggered: {pnl_percent:.1%} loss',
                'shares': shares
            }

        # Sell trigger 2: Take profit (lock in big gains)
        if pnl_percent > 0.30:  # 30% take profit
            return {
                'should_sell': True,
                'reason': f'Take profit triggered: {pnl_percent:.1%} gain',
                'shares': shares
            }

        # Sell trigger 3: Strong sell signal
        if signal_score and signal_score < -0.6:
            return {
                'should_sell': True,
                'reason': f'Strong sell signal: {signal_score:.2f}',
                'shares': shares
            }

        # Sell trigger 4: Deteriorating fundamentals
        fundamental_score = self._get_fundamentals_score(symbol)
        if fundamental_score < 0.3:
            return {
                'should_sell': True,
                'reason': f'Deteriorating fundamentals: {fundamental_score:.2f}',
                'shares': shares
            }

        return {'should_sell': False, 'reason': 'Hold position', 'shares': 0}

    def process_daily_report(self, report_date: Union[str, date]) -> Dict[str, Any]:
        """
        Process a daily PatternIQ report with sophisticated trading logic
        """
        # Convert string date to date object if needed
        if isinstance(report_date, str):
            report_date = datetime.strptime(report_date, "%Y-%m-%d").date()

        self.logger.info(f"🤖 Processing daily trading signals for {report_date}")

        # Find the report file
        reports_dir = Path("reports")
        json_report = reports_dir / f"patterniq_report_{report_date.strftime('%Y%m%d')}.json"

        if not json_report.exists():
            self.logger.error(f"Report not found: {json_report}")
            return {"status": "error", "message": f"Report not found for {report_date}"}

        # Load the report
        try:
            with open(json_report, 'r') as f:
                report = json.load(f)

            # Track trading decisions
            executed_trades = []
            skipped_trades = []

            portfolio_value_before = self.get_portfolio_value()

            # Process long recommendations with sophisticated logic
            for position in report.get('top_long', []):
                symbol = position['symbol']
                signal_score = position.get('score', 0.5)
                price = position['price']
                suggested_size = position.get('position_size', 2.0) / 100.0  # Convert from percentage

                # Calculate target dollar amount
                portfolio_value = self.get_portfolio_value()
                target_dollars = portfolio_value * min(suggested_size, self.max_position_size)

                # Sophisticated buy decision
                decision = self._should_buy(symbol, signal_score, price, target_dollars)

                if decision['should_buy']:
                    adjusted_dollars = decision['adjusted_size']
                    shares = int(adjusted_dollars / price)

                    if shares > 0:
                        success = self._execute_buy(symbol, shares, price, report_date)
                        if success:
                            executed_trades.append({
                                "action": "BUY",
                                "symbol": symbol,
                                "shares": shares,
                                "price": price,
                                "amount": shares * price,
                                "reason": decision['reason'],
                                "signal_score": signal_score
                            })
                else:
                    skipped_trades.append({
                        "action": "SKIP_BUY",
                        "symbol": symbol,
                        "reason": decision['reason'],
                        "signal_score": signal_score
                    })

            # Process sell recommendations and position management
            for position in report.get('top_short', []):
                symbol = position['symbol']
                signal_score = position.get('score', -0.5)
                price = position['price']

                # Check if we should sell existing position
                if symbol in self.positions:
                    decision = self._should_sell(symbol, price, signal_score)

                    if decision['should_sell']:
                        success = self._execute_sell(symbol, decision['shares'], price, report_date)
                        if success:
                            executed_trades.append({
                                "action": "SELL",
                                "symbol": symbol,
                                "shares": decision['shares'],
                                "price": price,
                                "amount": decision['shares'] * price,
                                "reason": decision['reason'],
                                "signal_score": signal_score
                            })

            # Review all existing positions for risk management
            for symbol in list(self.positions.keys()):
                # Get current price (simplified - would use real market data)
                current_price = self._get_current_price(symbol)
                if current_price:
                    decision = self._should_sell(symbol, current_price)

                    if decision['should_sell']:
                        success = self._execute_sell(symbol, decision['shares'], current_price, report_date)
                        if success:
                            executed_trades.append({
                                "action": "RISK_SELL",
                                "symbol": symbol,
                                "shares": decision['shares'],
                                "price": current_price,
                                "amount": decision['shares'] * current_price,
                                "reason": decision['reason']
                            })

            # Save updated portfolio state
            self._save_state()

            portfolio_value_after = self.get_portfolio_value()
            daily_return = (portfolio_value_after - portfolio_value_before) / portfolio_value_before

            self.logger.info(f"✅ Trading session complete:")
            self.logger.info(f"   Executed: {len(executed_trades)} trades")
            self.logger.info(f"   Skipped: {len(skipped_trades)} opportunities")
            self.logger.info(f"   Portfolio value: ${portfolio_value_before:,.0f} → ${portfolio_value_after:,.0f}")
            self.logger.info(f"   Daily return: {daily_return:.2%}")

            return {
                "status": "completed",
                "date": report_date.strftime("%Y-%m-%d"),
                "trades_executed": len(executed_trades),
                "trades_skipped": len(skipped_trades),
                "executed_trades": executed_trades,
                "skipped_trades": skipped_trades,
                "portfolio_value_before": portfolio_value_before,
                "portfolio_value_after": portfolio_value_after,
                "daily_return": daily_return,
                "cash_balance": self.cash_balance,
                "positions_count": len(self.positions)
            }

        except Exception as e:
            self.logger.error(f"Error processing report: {e}")
            return {"status": "error", "message": str(e)}

    def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol (simplified implementation)"""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            if not hist.empty:
                return float(hist['Close'].iloc[-1])
        except:
            pass
        return None

    def _execute_buy(self, symbol: str, shares: int, price: float, trade_date: date) -> bool:
        """Execute a buy order with fees and sophisticated logic"""
        cost = shares * price
        total_cost = cost + self.trading_fee

        if total_cost > self.cash_balance:
            self.logger.warning(f"Insufficient funds to buy {shares} {symbol} @ ${price}")
            return False

        # Execute the order (in paper trading mode)
        if symbol in self.positions:
            # Update existing position (average cost)
            existing_shares = self.positions[symbol]['shares']
            existing_cost = existing_shares * self.positions[symbol]['entry_price']
            new_cost = existing_cost + cost
            new_shares = existing_shares + shares

            self.positions[symbol] = {
                'shares': new_shares,
                'entry_price': new_cost / new_shares,
                'entry_date': self.positions[symbol]['entry_date'],
                'cost_basis': new_cost
            }
        else:
            # New position
            self.positions[symbol] = {
                'shares': shares,
                'entry_price': price,
                'entry_date': trade_date.strftime('%Y-%m-%d'),
                'cost_basis': cost
            }

        # Update cash balance (subtract cost + fees)
        self.cash_balance -= total_cost

        # Record the trade
        self.trade_history.append({
            'date': trade_date.strftime('%Y-%m-%d'),
            'action': 'BUY',
            'symbol': symbol,
            'shares': shares,
            'price': price,
            'amount': cost,
            'fees': self.trading_fee,
            'total_cost': total_cost
        })

        self.logger.info(f"✅ Bought {shares} {symbol} @ ${price:.2f} = ${cost:.2f} (fees: ${self.trading_fee:.2f})")
        return True

    def _execute_sell(self, symbol: str, shares: int, price: float, trade_date: date) -> bool:
        """Execute a sell order with fees and P&L tracking"""
        if symbol not in self.positions:
            self.logger.warning(f"Cannot sell {symbol} - not in portfolio")
            return False

        position = self.positions[symbol]
        available_shares = position['shares']

        if shares > available_shares:
            self.logger.warning(f"Requested to sell {shares} {symbol} but only have {available_shares}")
            shares = available_shares

        # Calculate proceeds and P&L
        proceeds = shares * price
        net_proceeds = proceeds - self.trading_fee
        cost_basis = (shares / available_shares) * position['cost_basis']
        pnl = net_proceeds - cost_basis

        # Update or remove position
        if shares == available_shares:
            # Full position closed
            del self.positions[symbol]
        else:
            # Partial position closed - update remaining
            remaining_shares = available_shares - shares
            remaining_cost = position['cost_basis'] - cost_basis

            self.positions[symbol].update({
                'shares': remaining_shares,
                'cost_basis': remaining_cost
            })

        # Update cash balance
        self.cash_balance += net_proceeds

        # Record the trade
        self.trade_history.append({
            'date': trade_date.strftime('%Y-%m-%d'),
            'action': 'SELL',
            'symbol': symbol,
            'shares': shares,
            'price': price,
            'amount': proceeds,
            'fees': self.trading_fee,
            'net_proceeds': net_proceeds,
            'pnl': pnl,
            'pnl_percent': (pnl / cost_basis) * 100 if cost_basis > 0 else 0
        })

        self.logger.info(f"✅ Sold {shares} {symbol} @ ${price:.2f} = ${proceeds:.2f} (P&L: ${pnl:.2f})")
        return True

    def get_portfolio_value(self) -> float:
        """Calculate total portfolio value (cash + positions)"""
        total_value = self.cash_balance

        for symbol, position in self.positions.items():
            # Get current price for valuation
            current_price = self._get_current_price(symbol)
            if current_price:
                position_value = position['shares'] * current_price
                total_value += position_value
            else:
                # Fallback to entry price if can't get current price
                position_value = position['shares'] * position['entry_price']
                total_value += position_value

        return total_value

    def get_portfolio_status(self) -> Dict[str, Any]:
        """Get comprehensive portfolio status"""
        portfolio_value = self.get_portfolio_value()
        total_return = (portfolio_value - self.initial_capital) / self.initial_capital

        # Calculate position details
        positions_detail = []
        total_position_value = 0

        for symbol, position in self.positions.items():
            current_price = self._get_current_price(symbol)
            if current_price:
                current_value = position['shares'] * current_price
                unrealized_pnl = current_value - position['cost_basis']
                unrealized_pnl_percent = (unrealized_pnl / position['cost_basis']) * 100
            else:
                current_price = position['entry_price']
                current_value = position['cost_basis']
                unrealized_pnl = 0
                unrealized_pnl_percent = 0

            total_position_value += current_value

            positions_detail.append({
                'symbol': symbol,
                'shares': position['shares'],
                'entry_price': position['entry_price'],
                'current_price': current_price,
                'entry_date': position['entry_date'],
                'cost_basis': position['cost_basis'],
                'current_value': current_value,
                'unrealized_pnl': unrealized_pnl,
                'unrealized_pnl_percent': unrealized_pnl_percent,
                'weight': (current_value / portfolio_value) * 100 if portfolio_value > 0 else 0
            })

        # Calculate realized P&L from trade history
        realized_pnl = sum(trade.get('pnl', 0) for trade in self.trade_history if trade['action'] == 'SELL')
        total_fees_paid = sum(trade.get('fees', 0) for trade in self.trade_history)

        return {
            'initial_capital': self.initial_capital,
            'current_value': portfolio_value,
            'cash_balance': self.cash_balance,
            'total_return': f"{total_return:.2%}",
            'total_return_dollars': portfolio_value - self.initial_capital,
            'positions_count': len(self.positions),
            'positions_value': total_position_value,
            'cash_percent': (self.cash_balance / portfolio_value) * 100 if portfolio_value > 0 else 100,
            'positions_detail': positions_detail,
            'total_trades': len(self.trade_history),
            'realized_pnl': realized_pnl,
            'total_fees_paid': total_fees_paid,
            'start_date': self.start_date.strftime('%Y-%m-%d'),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance metrics suitable for reporting"""
        status = self.get_portfolio_status()

        # Calculate additional metrics
        days_active = (date.today() - self.start_date).days
        if days_active == 0:
            days_active = 1

        annualized_return = (status['current_value'] / self.initial_capital) ** (365 / days_active) - 1

        # Win rate calculation
        winning_trades = [t for t in self.trade_history if t['action'] == 'SELL' and t.get('pnl', 0) > 0]
        losing_trades = [t for t in self.trade_history if t['action'] == 'SELL' and t.get('pnl', 0) < 0]
        total_sell_trades = len(winning_trades) + len(losing_trades)
        win_rate = len(winning_trades) / total_sell_trades if total_sell_trades > 0 else 0

        return {
            'portfolio_value': status['current_value'],
            'total_return': status['total_return'],
            'total_return_dollars': status['total_return_dollars'],
            'annualized_return': f"{annualized_return:.2%}",
            'days_active': days_active,
            'positions_count': status['positions_count'],
            'cash_percent': f"{status['cash_percent']:.1f}%",
            'total_trades': status['total_trades'],
            'win_rate': f"{win_rate:.1%}",
            'realized_pnl': status['realized_pnl'],
            'fees_paid': status['total_fees_paid'],
            'largest_position': max([p['weight'] for p in status['positions_detail']], default=0),
            'start_date': status['start_date']
        }

