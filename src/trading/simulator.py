# src/trading/simulator.py - Automated trading simulator based on daily reports

import logging
import json
import uuid
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import create_engine, text
from dataclasses import dataclass
import os

@dataclass
class Position:
    symbol: str
    shares: float
    entry_price: float
    entry_date: date
    current_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0

    def update_market_value(self, current_price: float):
        self.current_price = current_price
        self.market_value = self.shares * current_price
        self.unrealized_pnl = (current_price - self.entry_price) * self.shares

@dataclass
class TradeOrder:
    symbol: str
    action: str  # BUY or SELL
    shares: float
    order_type: str  # MARKET or LIMIT
    price: Optional[float] = None
    created_at: datetime = None
    filled_at: Optional[datetime] = None
    status: str = "PENDING"  # PENDING, FILLED, CANCELLED

class AutoTradingBot:
    """
    Automated trading bot that reacts to PatternIQ daily reports

    Features:
    - Processes daily signals and creates trading orders
    - Tracks portfolio performance vs initial investment
    - Risk management and position sizing
    - Paper trading mode for safe testing
    """

    def __init__(self, initial_capital: float = 100000.0, paper_trading: bool = True):
        self.logger = logging.getLogger("AutoTradingBot")
        db_url = os.getenv("PATTERNIQ_DB_URL", "postgresql://admin:secret@localhost:5432/patterniq")
        self.engine = create_engine(db_url)

        # Trading state
        self.bot_id = str(uuid.uuid4())
        self.initial_capital = initial_capital
        self.current_cash = initial_capital
        self.paper_trading = paper_trading

        # Portfolio tracking
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[TradeOrder] = []
        self.daily_portfolio_values: List[Dict] = []

        # Risk parameters
        self.max_position_size = 0.05  # 5% max per position
        self.max_portfolio_risk = 0.20  # 20% max drawdown stop
        self.min_signal_threshold = 0.3  # Minimum signal strength to trade

        self.logger.info(f"AutoTradingBot initialized: ${initial_capital:,.2f} capital, Paper={paper_trading}")

    def get_current_prices(self, symbols: List[str], date: date) -> Dict[str, float]:
        """Get current market prices for symbols"""

        with self.engine.connect() as conn:
            placeholders = ','.join([f"'{symbol}'" for symbol in symbols])
            result = conn.execute(text(f"""
                SELECT symbol, adj_c
                FROM bars_1d
                WHERE symbol IN ({placeholders})
                AND t::date = :date
            """), {"date": date})

            prices = {row[0]: float(row[1]) for row in result.fetchall()}

        return prices

    def process_daily_report(self, report_date: date) -> Dict[str, any]:
        """Process daily report and generate trading orders"""

        self.logger.info(f"Processing daily report for {report_date}")

        # Get signals from database
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT symbol, score, rank
                FROM signals_daily
                WHERE signal_name = 'combined_ic_weighted'
                AND d = :report_date
                AND ABS(score) >= :min_threshold
                ORDER BY ABS(score) DESC
            """), {
                "report_date": report_date,
                "min_threshold": self.min_signal_threshold
            })

            signals = result.fetchall()

        if not signals:
            self.logger.warning(f"No actionable signals found for {report_date}")
            return {"status": "no_signals", "orders": []}

        # Get current prices
        symbols = [row[0] for row in signals]
        current_prices = self.get_current_prices(symbols, report_date)

        # Generate trading orders
        orders = []
        total_new_exposure = 0

        for symbol, score, rank in signals:
            if symbol not in current_prices:
                continue

            current_price = current_prices[symbol]

            # Calculate position size based on signal strength
            signal_strength = abs(float(score))
            base_position_size = min(signal_strength * 0.04, self.max_position_size)  # Max 4% for strongest signals

            # Calculate dollar amount
            position_value = self.current_cash * base_position_size
            shares = position_value / current_price

            # Check if we have enough cash and exposure limits
            if position_value > self.current_cash * 0.1:  # Don't use more than 10% cash per trade
                continue

            if total_new_exposure + base_position_size > 0.5:  # Don't exceed 50% total new exposure
                continue

            # Determine action
            action = "BUY" if score > 0 else "SELL"

            # Create order
            order = TradeOrder(
                symbol=symbol,
                action=action,
                shares=abs(shares),
                order_type="MARKET",
                price=current_price,
                created_at=datetime.now()
            )

            orders.append(order)
            total_new_exposure += base_position_size

            self.logger.info(f"Generated {action} order: {symbol} x{shares:.0f} @ ${current_price:.2f}")

        # Execute orders (in paper trading mode)
        executed_orders = []
        for order in orders[:10]:  # Limit to 10 orders per day
            if self.execute_order(order, report_date):
                executed_orders.append(order)

        # Update portfolio values
        self.update_portfolio_value(report_date)

        return {
            "status": "processed",
            "report_date": report_date.isoformat(),
            "signals_processed": len(signals),
            "orders_generated": len(orders),
            "orders_executed": len(executed_orders),
            "executed_orders": [
                {
                    "symbol": order.symbol,
                    "action": order.action,
                    "shares": order.shares,
                    "price": order.price,
                    "value": order.shares * order.price
                }
                for order in executed_orders
            ]
        }

    def execute_order(self, order: TradeOrder, trade_date: date) -> bool:
        """Execute trading order (paper trading)"""

        if not self.paper_trading:
            self.logger.warning("Live trading not implemented - use paper_trading=True")
            return False

        try:
            trade_value = order.shares * order.price

            if order.action == "BUY":
                # Check if we have enough cash
                if trade_value > self.current_cash:
                    self.logger.warning(f"Insufficient cash for {order.symbol}: need ${trade_value:.2f}, have ${self.current_cash:.2f}")
                    return False

                # Execute buy
                self.current_cash -= trade_value

                # Add to positions
                if order.symbol in self.positions:
                    # Average down/up existing position
                    existing = self.positions[order.symbol]
                    total_shares = existing.shares + order.shares
                    avg_price = ((existing.shares * existing.entry_price) + (order.shares * order.price)) / total_shares

                    existing.shares = total_shares
                    existing.entry_price = avg_price
                else:
                    # New position
                    self.positions[order.symbol] = Position(
                        symbol=order.symbol,
                        shares=order.shares,
                        entry_price=order.price,
                        entry_date=trade_date,
                        current_price=order.price
                    )

            elif order.action == "SELL":
                # Check if we have the position
                if order.symbol not in self.positions:
                    self.logger.warning(f"Cannot sell {order.symbol}: no position")
                    return False

                existing = self.positions[order.symbol]
                if order.shares > existing.shares:
                    self.logger.warning(f"Cannot sell {order.shares} shares of {order.symbol}: only have {existing.shares}")
                    return False

                # Execute sell
                self.current_cash += trade_value
                existing.shares -= order.shares

                # Remove position if fully sold
                if existing.shares <= 0:
                    del self.positions[order.symbol]

            # Mark order as filled
            order.filled_at = datetime.now()
            order.status = "FILLED"

            # Add to trade history
            self.trade_history.append(order)

            self.logger.info(f"Executed {order.action}: {order.symbol} x{order.shares:.0f} @ ${order.price:.2f}")
            return True

        except Exception as e:
            self.logger.error(f"Error executing order for {order.symbol}: {e}")
            order.status = "FAILED"
            return False

    def update_portfolio_value(self, valuation_date: date):
        """Update portfolio valuation with current market prices"""

        if not self.positions:
            total_value = self.current_cash
        else:
            symbols = list(self.positions.keys())
            current_prices = self.get_current_prices(symbols, valuation_date)

            # Update each position
            total_position_value = 0
            for symbol, position in self.positions.items():
                if symbol in current_prices:
                    position.update_market_value(current_prices[symbol])
                    total_position_value += position.market_value

            total_value = self.current_cash + total_position_value

        # Calculate performance metrics
        total_return = (total_value - self.initial_capital) / self.initial_capital
        unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())

        # Record daily value
        daily_record = {
            "date": valuation_date.isoformat(),
            "total_value": total_value,
            "cash": self.current_cash,
            "positions_value": total_value - self.current_cash,
            "total_return": total_return,
            "unrealized_pnl": unrealized_pnl,
            "position_count": len(self.positions)
        }

        self.daily_portfolio_values.append(daily_record)

        self.logger.info(f"Portfolio value {valuation_date}: ${total_value:,.2f} ({total_return:+.2%})")

    def get_portfolio_status(self) -> Dict[str, any]:
        """Get current portfolio status and performance"""

        if not self.daily_portfolio_values:
            latest_value = self.initial_capital
            total_return = 0.0
        else:
            latest = self.daily_portfolio_values[-1]
            latest_value = latest["total_value"]
            total_return = latest["total_return"]

        # Position summary
        position_summary = []
        total_position_value = 0

        for symbol, position in self.positions.items():
            position_summary.append({
                "symbol": symbol,
                "shares": position.shares,
                "entry_price": position.entry_price,
                "current_price": position.current_price,
                "market_value": position.market_value,
                "unrealized_pnl": position.unrealized_pnl,
                "unrealized_return": position.unrealized_pnl / (position.shares * position.entry_price) if position.shares > 0 else 0
            })
            total_position_value += position.market_value

        # Performance metrics
        if len(self.daily_portfolio_values) > 1:
            returns = []
            for i in range(1, len(self.daily_portfolio_values)):
                prev_val = self.daily_portfolio_values[i-1]["total_value"]
                curr_val = self.daily_portfolio_values[i]["total_value"]
                daily_return = (curr_val - prev_val) / prev_val
                returns.append(daily_return)

            import numpy as np
            volatility = np.std(returns) * np.sqrt(252) if returns else 0  # Annualized
            sharpe = (np.mean(returns) * 252) / volatility if volatility > 0 else 0
        else:
            volatility = 0
            sharpe = 0

        return {
            "bot_id": self.bot_id,
            "initial_capital": self.initial_capital,
            "current_value": latest_value,
            "cash_balance": self.current_cash,
            "positions_value": total_position_value,
            "total_return": total_return,
            "total_pnl": latest_value - self.initial_capital,
            "performance_metrics": {
                "total_return_pct": f"{total_return:.2%}",
                "annualized_volatility": f"{volatility:.2%}",
                "sharpe_ratio": f"{sharpe:.2f}",
                "trading_days": len(self.daily_portfolio_values)
            },
            "positions": position_summary,
            "trade_count": len(self.trade_history),
            "paper_trading": self.paper_trading,
            "status": "active"
        }

    def save_state(self, filename: Optional[str] = None):
        """Save bot state to JSON file"""

        if not filename:
            filename = f"trading_bot_state_{self.bot_id[:8]}.json"

        state = {
            "bot_id": self.bot_id,
            "initial_capital": self.initial_capital,
            "current_cash": self.current_cash,
            "paper_trading": self.paper_trading,
            "positions": {
                symbol: {
                    "shares": pos.shares,
                    "entry_price": pos.entry_price,
                    "entry_date": pos.entry_date.isoformat(),
                    "current_price": pos.current_price
                }
                for symbol, pos in self.positions.items()
            },
            "daily_values": self.daily_portfolio_values,
            "trade_history": [
                {
                    "symbol": trade.symbol,
                    "action": trade.action,
                    "shares": trade.shares,
                    "price": trade.price,
                    "created_at": trade.created_at.isoformat() if trade.created_at else None,
                    "filled_at": trade.filled_at.isoformat() if trade.filled_at else None,
                    "status": trade.status
                }
                for trade in self.trade_history
            ],
            "saved_at": datetime.now().isoformat()
        }

        with open(filename, 'w') as f:
            json.dump(state, f, indent=2)

        self.logger.info(f"Bot state saved to {filename}")
        return filename


def demo_auto_trading():
    """Demo: Automated trading bot responding to daily reports"""

    print("🤖 PatternIQ Automated Trading Bot Demo")
    print("=" * 50)

    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

    # Initialize trading bot with $100K paper money
    bot = AutoTradingBot(initial_capital=100000.0, paper_trading=True)

    try:
        # Get available signal dates
        with bot.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT d 
                FROM signals_daily 
                WHERE signal_name = 'combined_ic_weighted'
                ORDER BY d DESC 
                LIMIT 5
            """))

            available_dates = [row[0] for row in result.fetchall()]

        if not available_dates:
            print("❌ No signal data found for trading simulation")
            return

        print(f"💰 Starting Capital: ${bot.initial_capital:,.2f}")
        print(f"📊 Paper Trading: {bot.paper_trading}")
        print(f"📅 Available dates: {len(available_dates)}")

        # Process each day's signals
        for i, trade_date in enumerate(reversed(available_dates), 1):
            print(f"\n📅 Day {i}: {trade_date}")
            print("-" * 30)

            # Process daily report
            result = bot.process_daily_report(trade_date)

            print(f"📊 Signals processed: {result['signals_processed']}")
            print(f"📋 Orders generated: {result['orders_generated']}")
            print(f"✅ Orders executed: {result['orders_executed']}")

            if result['executed_orders']:
                print("📈 Executed trades:")
                for order in result['executed_orders']:
                    print(f"   {order['action']} {order['symbol']} x{order['shares']:.0f} @ ${order['price']:.2f}")

        # Final portfolio status
        print(f"\n📊 Final Portfolio Status")
        print("=" * 50)

        status = bot.get_portfolio_status()

        print(f"💰 Portfolio Performance:")
        print(f"   Initial Capital:    ${status['initial_capital']:,.2f}")
        print(f"   Current Value:      ${status['current_value']:,.2f}")
        print(f"   Cash Balance:       ${status['cash_balance']:,.2f}")
        print(f"   Positions Value:    ${status['positions_value']:,.2f}")
        print(f"   Total Return:       {status['performance_metrics']['total_return_pct']}")
        print(f"   Total P&L:          ${status['total_pnl']:,.2f}")

        print(f"\n📈 Risk Metrics:")
        print(f"   Volatility:         {status['performance_metrics']['annualized_volatility']}")
        print(f"   Sharpe Ratio:       {status['performance_metrics']['sharpe_ratio']}")
        print(f"   Trading Days:       {status['performance_metrics']['trading_days']}")

        print(f"\n🎯 Current Positions ({len(status['positions'])}):")
        for pos in status['positions']:
            pnl_pct = pos['unrealized_return']
            print(f"   {pos['symbol']}: {pos['shares']:.0f} shares @ ${pos['current_price']:.2f} ({pnl_pct:+.2%})")

        print(f"\n💼 Trading Activity:")
        print(f"   Total Trades:       {status['trade_count']}")
        print(f"   Active Positions:   {len(status['positions'])}")
        print(f"   Paper Trading:      {status['paper_trading']}")

        # Save bot state
        state_file = bot.save_state()
        print(f"\n💾 Bot state saved: {state_file}")

        print(f"\n✅ Automated trading demo completed!")
        print(f"Features demonstrated:")
        print(f"  ✅ Daily signal processing")
        print(f"  ✅ Automated order generation")
        print(f"  ✅ Portfolio management")
        print(f"  ✅ Risk controls and position sizing")
        print(f"  ✅ Performance tracking")
        print(f"  ✅ Paper trading simulation")

    except Exception as e:
        print(f"❌ Error in automated trading demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    demo_auto_trading()
