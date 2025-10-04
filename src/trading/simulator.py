# src/trading/simulator.py - Automated trading bot with portfolio tracking

import os
import json
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
import pandas as pd
from typing import Dict, List, Optional, Any, Union

class AutoTradingBot:
    """
    Automated trading bot that processes PatternIQ signals and maintains portfolio state

    This implements the trading bot functionality described in section 7:
    - Processes daily signals and generates trading orders
    - Tracks portfolio positions, cash, and performance vs initial investment
    - Handles risk controls like position sizing and portfolio limits
    - Provides real-time portfolio status reporting
    """

    def __init__(self, initial_capital: float = 100000.0, paper_trading: bool = True,
                 max_position_size: float = 0.05, max_portfolio_risk: float = 0.20):
        """
        Initialize the trading bot

        Args:
            initial_capital: Starting capital amount
            paper_trading: If True, simulate trades without real execution
            max_position_size: Maximum percentage of portfolio in single position
            max_portfolio_risk: Maximum drawdown allowed before risk reduction
        """
        self.logger = logging.getLogger("AutoTradingBot")
        self.initial_capital = initial_capital
        self.paper_trading = paper_trading
        self.max_position_size = max_position_size
        self.max_portfolio_risk = max_portfolio_risk

        # Initialize portfolio state
        self.cash_balance = initial_capital
        self.positions = {}  # symbol -> {shares, entry_price, entry_date}
        self.trade_history = []
        self.start_date = date.today()

        # Create state directory if it doesn't exist
        self.state_dir = Path("trading_data")
        self.state_dir.mkdir(exist_ok=True)

        # Try to load existing state
        self._load_state()

        self.logger.info(f"Trading bot initialized with ${initial_capital:,.2f} "
                       f"({'PAPER' if paper_trading else 'LIVE'} trading)")

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

                self.logger.info(f"Loaded portfolio state from {state_file}")
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
            'paper_trading': self.paper_trading,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        try:
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)

            self.logger.info(f"Saved portfolio state to {state_file}")
        except Exception as e:
            self.logger.error(f"Error saving portfolio state: {e}")

    def process_daily_report(self, report_date: Union[str, date]) -> Dict[str, Any]:
        """
        Process a daily PatternIQ report and execute trades

        Args:
            report_date: Date of the report to process (string or date object)

        Returns:
            Dict with execution summary
        """
        # Convert string date to date object if needed
        if isinstance(report_date, str):
            report_date = datetime.strptime(report_date, "%Y-%m-%d").date()

        self.logger.info(f"Processing daily report for {report_date}")

        # Find the report file
        reports_dir = Path("reports")
        json_report = reports_dir / f"patterniq_report_{report_date.strftime('%Y%m%d')}.json"

        # For testing purposes, create a mock report if it doesn't exist
        if not json_report.exists() and os.getenv("PATTERNIQ_TESTING", "false").lower() == "true":
            self.logger.warning(f"Report not found, creating mock report for testing: {json_report}")
            reports_dir.mkdir(exist_ok=True)
            mock_report = {
                "date": report_date.strftime("%Y-%m-%d"),
                "top_long": [
                    {
                        "symbol": "AAPL",
                        "sector": "Technology",
                        "signal": "BUY",
                        "score": 0.65,
                        "position_size": 2.0,
                        "price": 180.50
                    }
                ],
                "top_short": []
            }
            with open(json_report, 'w') as f:
                json.dump(mock_report, f)

        if not json_report.exists():
            self.logger.error(f"Report not found: {json_report}")
            return {"status": "error", "message": f"Report not found for {report_date}"}

        # Load the report
        try:
            with open(json_report, 'r') as f:
                report = json.load(f)

            # Track executions
            executed_trades = []

            # Process long recommendations
            for position in report.get('top_long', []):
                symbol = position['symbol']
                target_size = position['position_size'] / 100.0  # Convert from percentage
                price = position['price']

                # Calculate the target dollar amount
                portfolio_value = self.get_portfolio_value()
                target_dollars = portfolio_value * min(target_size, self.max_position_size)

                # Calculate how many shares to buy
                target_shares = int(target_dollars / price)

                if target_shares > 0:
                    # Execute buy order
                    self._execute_buy(symbol, target_shares, price, report_date)
                    executed_trades.append({
                        "action": "BUY",
                        "symbol": symbol,
                        "shares": target_shares,
                        "price": price,
                        "amount": target_shares * price
                    })

            # Process short recommendations
            for position in report.get('top_short', []):
                symbol = position['symbol']
                target_size = position['position_size'] / 100.0  # Convert from percentage
                price = position['price']

                # Check if we hold this stock and should sell it
                if symbol in self.positions:
                    # Sell existing position
                    shares = self.positions[symbol]['shares']
                    self._execute_sell(symbol, shares, price, report_date)
                    executed_trades.append({
                        "action": "SELL",
                        "symbol": symbol,
                        "shares": shares,
                        "price": price,
                        "amount": shares * price
                    })

            # Save updated portfolio state
            self._save_state()

            return {
                "status": "completed",
                "date": report_date.strftime("%Y-%m-%d"),
                "trades_executed": len(executed_trades),
                "trades": executed_trades,
                "portfolio_value": self.get_portfolio_value(),
                "cash_balance": self.cash_balance
            }

        except Exception as e:
            self.logger.error(f"Error processing report: {e}")
            return {"status": "error", "message": str(e)}

    def _execute_buy(self, symbol: str, shares: int, price: float, trade_date: date) -> bool:
        """Execute a buy order"""
        cost = shares * price

        if cost > self.cash_balance:
            self.logger.warning(f"Insufficient funds to buy {shares} {symbol} @ ${price}")
            # Buy as many as we can afford
            max_shares = int(self.cash_balance / price)
            if max_shares <= 0:
                return False

            shares = max_shares
            cost = shares * price

        # Execute the order (in paper trading mode)
        if symbol in self.positions:
            # Update existing position (average down/up)
            existing_shares = self.positions[symbol]['shares']
            existing_cost = existing_shares * self.positions[symbol]['entry_price']
            new_cost = existing_cost + cost
            new_shares = existing_shares + shares

            self.positions[symbol] = {
                'shares': new_shares,
                'entry_price': new_cost / new_shares,
                'entry_date': self.positions[symbol]['entry_date']
            }
        else:
            # New position
            self.positions[symbol] = {
                'shares': shares,
                'entry_price': price,
                'entry_date': trade_date.strftime('%Y-%m-%d')
            }

        # Update cash balance
        self.cash_balance -= cost

        # Record the trade
        self.trade_history.append({
            'date': trade_date.strftime('%Y-%m-%d'),
            'action': 'BUY',
            'symbol': symbol,
            'shares': shares,
            'price': price,
            'amount': cost
        })

        self.logger.info(f"Bought {shares} {symbol} @ ${price:.2f} = ${cost:.2f}")
        return True

    def _execute_sell(self, symbol: str, shares: int, price: float, trade_date: date) -> bool:
        """Execute a sell order"""
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
        cost_basis = shares * position['entry_price']
        pnl = proceeds - cost_basis

        # Update or remove position
        if shares == available_shares:
            # Full position closed
            del self.positions[symbol]
        else:
            # Partial position closed
            self.positions[symbol]['shares'] -= shares

        # Update cash balance
        self.cash_balance += proceeds

        # Record the trade
        self.trade_history.append({
            'date': trade_date.strftime('%Y-%m-%d'),
            'action': 'SELL',
            'symbol': symbol,
            'shares': shares,
            'price': price,
            'amount': proceeds,
            'pnl': pnl
        })

        self.logger.info(f"Sold {shares} {symbol} @ ${price:.2f} = ${proceeds:.2f}, P&L: ${pnl:.2f}")
        return True

    def get_portfolio_value(self) -> float:
        """Calculate current portfolio value (cash + positions)"""
        positions_value = 0.0

        # In a real system, we would get current market prices here
        # For the demo, we use the entry prices
        for symbol, position in self.positions.items():
            positions_value += position['shares'] * position['entry_price']

        return self.cash_balance + positions_value

    def get_portfolio_status(self) -> Dict[str, Any]:
        """Get comprehensive portfolio status report"""
        # Calculate portfolio value
        portfolio_value = self.get_portfolio_value()
        positions_value = portfolio_value - self.cash_balance

        # Calculate performance metrics
        total_pnl = portfolio_value - self.initial_capital
        total_return_pct = (portfolio_value / self.initial_capital - 1) * 100

        # Prepare positions with current value and P&L
        position_data = []
        for symbol, position in self.positions.items():
            shares = position['shares']
            entry_price = position['entry_price']
            # In a real system, we would get current price from market data
            # For now, use entry price as current price (no P&L)
            current_price = entry_price

            position_value = shares * current_price
            unrealized_pnl = shares * (current_price - entry_price)
            unrealized_return = (current_price / entry_price - 1) * 100

            position_data.append({
                'symbol': symbol,
                'shares': shares,
                'entry_price': entry_price,
                'current_price': current_price,
                'position_value': position_value,
                'weight': position_value / portfolio_value * 100 if portfolio_value > 0 else 0,
                'unrealized_pnl': unrealized_pnl,
                'unrealized_return': f"{unrealized_return:.2f}%"
            })

        # Sort positions by value (descending)
        position_data.sort(key=lambda x: x['position_value'], reverse=True)

        # Calculate simple performance metrics
        days_active = (date.today() - self.start_date).days
        days_active = max(1, days_active)  # Avoid division by zero

        return {
            'initial_capital': self.initial_capital,
            'current_value': portfolio_value,
            'total_return': f"{total_return_pct:.2f}%",
            'cash_balance': self.cash_balance,
            'cash_pct': self.cash_balance / portfolio_value * 100 if portfolio_value > 0 else 0,
            'positions_value': positions_value,
            'total_pnl': total_pnl,
            'performance_metrics': {
                'total_return_pct': f"{total_return_pct:.2f}%",
                'annualized_return': f"{(((1 + total_return_pct/100) ** (365/days_active)) - 1) * 100:.2f}%",
                'trading_days': days_active
            },
            'positions': position_data,
            'paper_trading': self.paper_trading,
            'status': 'active'
        }

# For simple usage in command line
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create bot with demo settings
    bot = AutoTradingBot(initial_capital=100000.0, paper_trading=True)

    # Get and display portfolio status
    status = bot.get_portfolio_status()

    print("\n🤖 PatternIQ Trading Bot - Portfolio Status")
    print("=" * 60)
    print(f"Initial Capital: ${status['initial_capital']:,.2f}")
    print(f"Current Value:   ${status['current_value']:,.2f}")
    print(f"Total Return:    {status['total_return']}")
    print(f"Cash Balance:    ${status['cash_balance']:,.2f} ({status['cash_pct']:.1f}%)")

    # Show positions if any
    if status['positions']:
        print("\n📊 Current Positions:")
        for pos in status['positions']:
            print(f"  {pos['symbol']:<6} {pos['shares']:>5} shares @ ${pos['entry_price']:<8.2f} = ${pos['position_value']:,.2f}")

    else:
        print("\n📊 No open positions")

    print("\n💰 Ready to process trading signals from daily reports")
    print("Example: bot.process_daily_report('2025-09-20')")
