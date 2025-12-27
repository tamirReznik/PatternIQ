# src/telegram/bot.py - Telegram bot for daily PatternIQ reports

import logging
import asyncio
import os
from datetime import datetime, date, timedelta
from typing import Optional
import json
from pathlib import Path

try:
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logging.warning("python-telegram-bot not available. Install with: pip install python-telegram-bot")

class PatternIQBot:
    """
    Telegram bot for sending daily PatternIQ reports
    Sends formatted trading signals and market analysis to registered users
    """

    def __init__(self):
        self.logger = logging.getLogger("PatternIQBot")

        if not TELEGRAM_AVAILABLE:
            self.logger.error("Telegram bot functionality not available")
            self.bot = None
            return

        # Get bot token from environment
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.bot_token:
            self.logger.error("TELEGRAM_BOT_TOKEN not set in environment")
            self.bot = None
            return

        self.bot = Bot(token=self.bot_token)

        # Default chat IDs (can be configured)
        self.chat_ids = self._load_chat_ids()

    def _load_chat_ids(self) -> list:
        """Load registered chat IDs from environment or config file"""

        # Try environment variable first (comma-separated)
        env_chats = os.getenv("TELEGRAM_CHAT_IDS", "")
        if env_chats:
            return [int(chat_id.strip()) for chat_id in env_chats.split(",") if chat_id.strip()]

        # Try config file
        config_file = "telegram_chats.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    return config.get("chat_ids", [])
            except Exception as e:
                self.logger.error(f"Error loading chat IDs from file: {e}")

        return []

    def add_chat_id(self, chat_id: int, description: str = ""):
        """Add a new chat ID to receive reports"""

        if chat_id not in self.chat_ids:
            self.chat_ids.append(chat_id)
            self._save_chat_ids()
            self.logger.info(f"Added chat ID {chat_id}: {description}")
            return True
        return False

    def remove_chat_id(self, chat_id: int):
        """Remove a chat ID from receiving reports"""

        if chat_id in self.chat_ids:
            self.chat_ids.remove(chat_id)
            self._save_chat_ids()
            self.logger.info(f"Removed chat ID {chat_id}")
            return True
        return False

    def _save_chat_ids(self):
        """Save chat IDs to config file"""

        config = {
            "chat_ids": self.chat_ids,
            "last_updated": datetime.now().isoformat()
        }

        with open("telegram_chats.json", 'w') as f:
            json.dump(config, f, indent=2)

    def format_telegram_message(self, report_data: dict) -> str:
        """Format report data for Telegram message"""

        # Handle the actual report structure from PatternIQ
        date = report_data.get("date", "Unknown")
        market_overview = report_data.get("market_overview", {})
        top_long = report_data.get("top_long", [])
        top_short = report_data.get("top_short", [])

        message = f"🤖 *PatternIQ Daily Report*\n"
        message += f"📅 {date}\n\n"

        # Add Trading Bot Performance Section
        bot_performance = self._get_bot_performance()
        if bot_performance:
            message += f"💼 *Trading Bot Performance*\n"
            message += f"• Portfolio Value: ${bot_performance['current_value']:,.0f}\n"
            message += f"• Total Return: {bot_performance['total_return']}\n"
            message += f"• Cash Balance: ${bot_performance['cash_balance']:,.0f}\n"
            message += f"• Active Positions: {bot_performance['positions_count']}\n"
            message += f"• Total Trades: {bot_performance['total_trades']}\n"

            # Add recent trades if any
            if bot_performance.get('recent_trades'):
                message += f"• Recent Trades: {len(bot_performance['recent_trades'])}\n"
                for trade in bot_performance['recent_trades'][:2]:  # Show last 2 trades
                    pnl_emoji = "📈" if trade.get('pnl', 0) >= 0 else "📉"
                    message += f"  {pnl_emoji} {trade.get('action', 'N/A')} {trade.get('symbol', 'N/A')} @ ${trade.get('price', 0):.2f}\n"

            message += "\n"

        # Market Overview
        message += f"📊 *Market Overview*\n"
        message += f"• Regime: {market_overview.get('regime', 'N/A')}\n"
        message += f"• Signal Strength: {market_overview.get('signal_strength', 0)}%\n"
        message += f"• Total Recommendations: {market_overview.get('total_recommendations', 0)}\n"
        message += f"• High Conviction: {market_overview.get('high_conviction', 0)}\n\n"

        # Long Recommendations
        if top_long:
            message += f"📈 *Top Long Picks ({len(top_long)})*\n"
            for stock in top_long[:3]:  # Top 3 to save space
                score_emoji = "🔥" if stock.get("score", 0) > 0.7 else "📈" if stock.get("score", 0) > 0.5 else "↗️"
                message += f"{score_emoji} *{stock.get('symbol', 'N/A')}* ({stock.get('sector', 'N/A')}) - {stock.get('signal', 'N/A')}\n"
                message += f"   Score: {stock.get('score', 0):.3f} | Size: {stock.get('position_size', 0)}% | ${stock.get('price', 0):.2f}\n"
            message += "\n"

        # Short Recommendations
        if top_short:
            message += f"📉 *Top Short Picks ({len(top_short)})*\n"
            for stock in top_short[:3]:  # Top 3 to save space
                score_emoji = "🔥" if stock.get("score", 0) < -0.7 else "📉" if stock.get("score", 0) < -0.5 else "↘️"
                message += f"{score_emoji} *{stock.get('symbol', 'N/A')}* ({stock.get('sector', 'N/A')}) - {stock.get('signal', 'SELL')}\n"
                message += f"   Score: {stock.get('score', 0):.3f} | Size: {stock.get('position_size', 0)}% | ${stock.get('price', 0):.2f}\n"
            message += "\n"

        # Footer
        message += f"⏰ Generated: {datetime.now().strftime('%H:%M ET')}\n"
        message += f"🔗 Full report available in dashboard\n\n"
        message += "_Trading involves substantial risk. Past performance doesn't guarantee future results._"

        return message

    def _get_bot_performance(self) -> dict:
        """Get trading bot performance data"""
        try:
            portfolio_file = Path("trading_data/portfolio_state.json")
            if not portfolio_file.exists():
                return None

            with open(portfolio_file, 'r') as f:
                data = json.load(f)

            # Calculate current portfolio value
            positions_value = 0
            for symbol, pos_data in data.get('positions', {}).items():
                shares = pos_data.get('shares', 0)
                entry_price = pos_data.get('entry_price', 0)
                positions_value += shares * entry_price

            current_value = data.get('cash_balance', 0) + positions_value
            initial_capital = data.get('initial_capital', 100000)
            total_return_num = (current_value - initial_capital) / initial_capital * 100

            # Get recent trades (last 5)
            recent_trades = data.get('trade_history', [])[-5:] if data.get('trade_history') else []

            return {
                "current_value": current_value,
                "total_return": f"{total_return_num:+.2f}%",
                "total_return_num": total_return_num,
                "cash_balance": data.get('cash_balance', 0),
                "positions_count": len(data.get('positions', {})),
                "total_trades": len(data.get('trade_history', [])),
                "recent_trades": recent_trades,
                "paper_trading": data.get('paper_trading', True),
                "start_date": data.get('start_date', 'Unknown')
            }

        except Exception as e:
            self.logger.error(f"Error loading bot performance: {e}")
            return None

    async def send_daily_report(self, report_date: Optional[date] = None) -> bool:
        """Send daily report to all registered chat IDs"""

        if not self.bot:
            self.logger.error("Telegram bot not initialized")
            return False

        if not self.chat_ids:
            self.logger.warning("No chat IDs registered for reports")
            return False

        if not report_date:
            report_date = date.today() - timedelta(days=1)  # Use yesterday's date

        try:
            # Load report data directly from file instead of using ReportGenerator class
            reports_dir = Path("reports")
            report_file = reports_dir / f"patterniq_report_{report_date.strftime('%Y%m%d')}.json"

            if not report_file.exists():
                self.logger.error(f"Report file not found: {report_file}")
                return False

            with open(report_file, 'r') as f:
                report_data = json.load(f)

            # Format message
            message = self.format_telegram_message(report_data)

            # Send to all registered chats
            successful_sends = 0
            failed_sends = 0

            for chat_id in self.chat_ids:
                try:
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode='Markdown',
                        disable_web_page_preview=True
                    )
                    successful_sends += 1
                    self.logger.info(f"Report sent to chat {chat_id}")

                except TelegramError as e:
                    failed_sends += 1
                    self.logger.error(f"Failed to send to chat {chat_id}: {e}")

                # Small delay between messages
                await asyncio.sleep(0.5)

            self.logger.info(f"Telegram report sent: {successful_sends} successful, {failed_sends} failed")
            return successful_sends > 0

        except Exception as e:
            self.logger.error(f"Error sending Telegram report: {e}")
            return False

    async def send_alert(self, message: str, priority: str = "normal") -> bool:
        """Send urgent alert to all registered chats"""

        if not self.bot or not self.chat_ids:
            return False

        alert_emoji = "🚨" if priority == "high" else "⚠️" if priority == "medium" else "ℹ️"
        formatted_message = f"{alert_emoji} *PatternIQ Alert*\n\n{message}\n\n_{datetime.now().strftime('%Y-%m-%d %H:%M ET')}_"

        successful_sends = 0
        for chat_id in self.chat_ids:
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=formatted_message,
                    parse_mode='Markdown'
                )
                successful_sends += 1
            except TelegramError as e:
                self.logger.error(f"Failed to send alert to chat {chat_id}: {e}")

        return successful_sends > 0

    async def test_connection(self, chat_id: int) -> bool:
        """Test bot connection with a specific chat"""

        if not self.bot:
            return False

        try:
            test_message = f"🤖 *PatternIQ Bot Test*\n\nConnection successful!\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M ET')}"

            await self.bot.send_message(
                chat_id=chat_id,
                text=test_message,
                parse_mode='Markdown'
            )

            self.logger.info(f"Test message sent to chat {chat_id}")
            return True

        except TelegramError as e:
            self.logger.error(f"Test failed for chat {chat_id}: {e}")
            return False


def setup_telegram_bot():
    """Setup Telegram bot with configuration instructions"""

    print("🤖 PatternIQ Telegram Bot Setup")
    print("=" * 40)

    if not TELEGRAM_AVAILABLE:
        print("❌ Telegram bot not available")
        print("Install with: pip install python-telegram-bot")
        return None

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("⚠️  TELEGRAM_BOT_TOKEN not found in environment")
        print("\nTo setup Telegram bot:")
        print("1. Message @BotFather on Telegram")
        print("2. Send: /newbot")
        print("3. Follow instructions to create bot")
        print("4. Copy the token and set environment variable:")
        print("   export TELEGRAM_BOT_TOKEN='your_token_here'")
        print("5. Get your chat ID by messaging @userinfobot")
        print("6. Set chat IDs: export TELEGRAM_CHAT_IDS='123456789,987654321'")
        return None

    # Initialize bot
    bot = PatternIQBot()

    if bot.bot:
        print("✅ Telegram bot initialized successfully")
        print(f"📱 Registered chats: {len(bot.chat_ids)}")

        if bot.chat_ids:
            print("Chat IDs:")
            for i, chat_id in enumerate(bot.chat_ids, 1):
                print(f"  {i}. {chat_id}")
        else:
            print("⚠️  No chat IDs registered")
            print("Add chat IDs with: bot.add_chat_id(your_chat_id)")

        return bot
    else:
        print("❌ Failed to initialize Telegram bot")
        return None


async def test_telegram_bot():
    """Demo: Send test Telegram report"""

    print("📱 PatternIQ Telegram Bot Demo")
    print("=" * 40)

    bot = setup_telegram_bot()

    if not bot or not bot.bot:
        print("❌ Telegram bot not available for demo")
        return

    if not bot.chat_ids:
        print("⚠️  No chat IDs registered. Add with:")
        print("bot.add_chat_id(your_chat_id, 'Your Name')")
        return

    try:
        # Send daily report
        print("📤 Sending daily report...")
        success = await bot.send_daily_report()

        if success:
            print("✅ Daily report sent successfully!")
        else:
            print("❌ Failed to send daily report")

        # Send test alert
        print("📤 Sending test alert...")
        alert_success = await bot.send_alert(
            "This is a test alert from PatternIQ system. All systems operational.",
            priority="normal"
        )

        if alert_success:
            print("✅ Test alert sent successfully!")
        else:
            print("❌ Failed to send test alert")

    except Exception as e:
        print(f"❌ Error in Telegram bot demo: {e}")


if __name__ == "__main__":
    if TELEGRAM_AVAILABLE:
        asyncio.run(demo_telegram_bot())
    else:
        setup_telegram_bot()
