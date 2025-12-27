# src/main.py

import asyncio
import logging
import sys
from datetime import datetime, timedelta, date
from pathlib import Path

# Optional imports - only needed for API server
try:
    import uvicorn
    from src.api.server import app
    API_AVAILABLE = True
except ImportError:
    uvicorn = None
    app = None
    API_AVAILABLE = False
try:
    from src.core.config import config
except ImportError:
    # Fallback to old location for backward compatibility
    from src.common.config import config
from src.common.db_manager import db_manager
from sqlalchemy import text
from src.data.ingestion.pipeline import run_data_ingestion_pipeline
from src.data.ingestion.incremental import incremental_backfill, get_symbols_needing_update
from src.features.momentum import calculate_momentum_features
from src.report.generator import generate_daily_report
from src.signals.blend import blend_signals_ic_weighted
from src.signals.rules import generate_signals

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PatternIQOrchestrator:
    """Main orchestrator for PatternIQ system"""

    def __init__(self):
        # Reload config to pick up any environment variable changes
        # This ensures config reflects env vars set after module import
        from src.core.config import load_config
        self.config = load_config()
        self.trading_bot = None
        self.api_server = None

    async def run_daily_pipeline(self) -> bool:
        """Run the complete daily pipeline"""
        try:
            logger.info("🚀 Starting PatternIQ daily pipeline...")

            # 1. Data ingestion (incremental update for daily runs)
            logger.info("📊 Step 1/7: Updating market data...")
            await self.run_incremental_data_update()

            # 2. Feature calculation
            logger.info("🔧 Step 2/7: Calculating features...")
            await asyncio.to_thread(calculate_momentum_features)

            # 3. Signal generation
            logger.info("📡 Step 3/7: Generating signals...")
            await asyncio.to_thread(generate_signals)

            # 4. Signal blending
            logger.info("🎯 Step 4/7: Blending signals...")
            await asyncio.to_thread(blend_signals_ic_weighted)

            # 5. Report generation
            if self.config.generate_reports:
                logger.info("📋 Step 5/7: Generating reports...")
                await asyncio.to_thread(generate_daily_report)
            else:
                logger.info("📋 Step 5/7: Skipping reports (disabled in config)")

            # 6. Trading simulation
            logger.info("💼 Step 6/7: Processing trading signals...")
            await self.run_trading()

            # 7. Telegram notifications
            if self.config.send_telegram_alerts and self.config.telegram_bot_token:
                logger.info("📱 Step 7/7: Sending Telegram alerts...")
                await self.send_telegram_alert()
            else:
                logger.info("📱 Step 7/7: Skipping Telegram (not configured)")

            logger.info("✅ Daily pipeline completed successfully!")
            return True

        except Exception as e:
            from src.core.exceptions import PatternIQException
            if isinstance(e, PatternIQException):
                logger.error(f"❌ Pipeline failed: {e}")
            else:
                logger.error(f"❌ Pipeline failed with unexpected error: {e}", exc_info=True)
            return False

    async def run_trading(self):
        """Initialize and run unified trading bot"""
        from src.core.exceptions import TradingBotError
        
        try:
            if not self.trading_bot:
                # Initialize unified trading bot
                from src.trading.bot import TradingBot

                self.trading_bot = TradingBot(
                    initial_capital=self.config.initial_capital,
                    paper_trading=self.config.paper_trading,
                    max_position_size=self.config.max_position_size,
                    enable_multi_asset=True,
                    leverage_multiplier=1.2,  # 20% conservative leverage
                    trading_fee_per_trade=0.0,
                    default_time_horizon="mid"
                )

                logger.info("🚀 Unified Trading Bot initialized")
                logger.info(f"   Base Capital: ${self.config.initial_capital:,.0f}")
                logger.info(f"   Effective Capital (1.2x leverage): ${self.trading_bot.effective_capital:,.0f}")
                logger.info("   Asset Classes: Stocks + Sector ETFs + Crypto ETFs + International")
                logger.info(f"   Default Time Horizon: {self.trading_bot.default_time_horizon.value.upper()}")

            # Process yesterday's report (reports are generated for previous trading day)
            current_date = date.today()
            result = self.trading_bot.process_daily_report(current_date)
            logger.info(f"Trading result: {result.get('status', 'completed')}")

            if result.get('status') == 'completed':
                logger.info(f"   Executed: {result.get('trades_executed', 0)} trades")
                logger.info(f"   Skipped: {result.get('trades_skipped', 0)} opportunities")

                # Log executed trades by asset class
                executed_trades = result.get('executed_trades', [])
                if executed_trades:
                    asset_class_trades = {}
                    for trade in executed_trades:
                        asset_class = trade.get('asset_class', 'unknown')
                        if asset_class not in asset_class_trades:
                            asset_class_trades[asset_class] = []
                        asset_class_trades[asset_class].append(trade)

                    for asset_class, trades in asset_class_trades.items():
                        logger.info(f"   {asset_class}: {len(trades)} trades")

            # Log portfolio status
            status = self.trading_bot.get_portfolio_status()
            logger.info(f"Portfolio: ${status['initial_capital']:,.0f} → ${status['current_value']:,.0f} ({status['total_return']})")

            # Log asset allocation
            allocation_by_class = status.get('allocation_by_class', {})
            if allocation_by_class:
                logger.info("   Current Allocation:")
                for asset_class, allocation in allocation_by_class.items():
                    if allocation > 0.01:  # Only show >1% allocations
                        logger.info(f"     {asset_class}: {allocation:.1%}")
            
            # Log time horizon allocation
            allocation_by_horizon = status.get('allocation_by_horizon', {})
            if allocation_by_horizon:
                logger.info("   Time Horizon Allocation:")
                for horizon, allocation in allocation_by_horizon.items():
                    if allocation > 0.01:
                        logger.info(f"     {horizon}: {allocation:.1%}")

        except TradingBotError as e:
            logger.error(f"Trading bot error: {e}")
            raise
        except Exception as e:
            logger.error(f"Trading simulation failed: {e}", exc_info=True)
            raise TradingBotError(f"Trading simulation failed: {e}") from e

    async def send_telegram_alert(self):
        """Send Telegram notification"""
        try:
            from src.telegram.bot import PatternIQBot
            bot = PatternIQBot()

            # Check if bot is properly initialized
            if not bot.bot:
                logger.error("❌ Telegram bot not initialized. Check configuration:")
                logger.error("   1. TELEGRAM_BOT_TOKEN must be set")
                logger.error("   2. python-telegram-bot package must be installed")
                return

            if not bot.chat_ids:
                logger.error("❌ No Telegram chat IDs configured:")
                logger.error("   Set TELEGRAM_CHAT_IDS environment variable")
                logger.error("   Example: export TELEGRAM_CHAT_IDS='123456789'")
                return

            # Use today's date (reports are generated for current date)
            report_date = date.today()
            
            # Also try yesterday in case report was generated yesterday
            yesterday_date = report_date - timedelta(days=1)
            
            # Verify report exists before sending
            reports_dir = Path("reports")
            report_file = reports_dir / f"patterniq_report_{report_date.strftime('%Y%m%d')}.json"
            yesterday_file = reports_dir / f"patterniq_report_{yesterday_date.strftime('%Y%m%d')}.json"
            
            # Try today's report first, then yesterday's
            target_date = None
            if report_file.exists():
                target_date = report_date
                logger.info(f"📱 Sending Telegram report for {report_date}")
            elif yesterday_file.exists():
                target_date = yesterday_date
                logger.info(f"📱 Sending Telegram report for {yesterday_date} (latest available)")
            else:
                logger.warning(f"⚠️  No report found for {report_date} or {yesterday_date}")
                # Try to find latest available report
                latest_json = sorted(reports_dir.glob("patterniq_report_*.json"))[-1] if list(reports_dir.glob("patterniq_report_*.json")) else None
                if latest_json:
                    # Extract date from filename
                    date_str = latest_json.stem.replace("patterniq_report_", "")
                    target_date = datetime.strptime(date_str, "%Y%m%d").date()
                    logger.info(f"📱 Using latest available report from {target_date}")
            
            if target_date:
                success = await bot.send_daily_report(target_date)
                if success:
                    logger.info("✅ Telegram alert sent successfully")
                else:
                    logger.error("❌ Failed to send Telegram alert")
            else:
                logger.error("❌ No reports available to send via Telegram")

        except Exception as e:
            logger.error(f"❌ Telegram alert failed: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def start_api_server(self):
        """Start the API server"""
        if not API_AVAILABLE:
            logger.error("❌ API server not available: uvicorn or FastAPI not installed")
            logger.error("   Install with: pip install uvicorn fastapi")
            raise ImportError("uvicorn and FastAPI are required for API server mode")
        
        try:
            logger.info(f"🌐 Starting API server on {self.config.api_host}:{self.config.api_port}")
            config_api = uvicorn.Config(
                app,
                host=self.config.api_host,
                port=self.config.api_port,
                log_level="info"
            )
            server = uvicorn.Server(config_api)
            await server.serve()
        except Exception as e:
            logger.error(f"API server failed: {e}")

    async def run_batch_mode(self):
        """Run once and exit (batch mode)"""
        print("🏃 Running in BATCH mode - will exit after completion")
        logger.info("🏃 Running in BATCH mode - will exit after completion")

        success = await self.run_daily_pipeline()

        print(f"Pipeline completed with success: {success}")

        if self.config.start_api_server:
            print("🌐 Starting API server as requested...")
            logger.info("🌐 Starting API server as requested...")
            await self.start_api_server()
        else:
            print("🏁 Batch mode completed. System will now exit.")
            logger.info("🏁 Batch mode completed. System will now exit.")
            # Don't exit immediately - let the function return normally
            return success

    async def run_always_on_mode(self):
        """Run continuously with scheduled execution"""
        logger.info("🔄 Running in ALWAYS-ON mode - will run continuously")

        # Start API server in background
        if self.config.start_api_server or True:  # Always start API in always-on mode
            api_task = asyncio.create_task(self.start_api_server())

        # Run initial pipeline
        await self.run_daily_pipeline()

        # Schedule daily execution (simplified version - runs every 24 hours)
        logger.info("⏰ Scheduling next run in 24 hours...")

        while True:
            await asyncio.sleep(24 * 60 * 60)  # Wait 24 hours
            logger.info("⏰ Starting scheduled daily pipeline...")
            await self.run_daily_pipeline()

    async def run(self):
        """Main entry point"""
        logger.info(f"🤖 PatternIQ starting...")

        # Setup database with migration handling
        logger.info("🗄️ Setting up database...")
        if not db_manager.setup_database():
            logger.error("❌ Database setup failed!")
            sys.exit(1)

        # Get database info for logging
        db_info = db_manager.get_database_info()

        logger.info(f"📋 Configuration:")
        logger.info(f"   - Mode: {'ALWAYS-ON' if self.config.always_on else 'BATCH'}")
        logger.info(f"   - Database: {db_info['database_type']} ({self.config.db_mode} mode)")
        logger.info(f"   - DB Records: {db_info.get('total_records', 'N/A')}")
        logger.info(f"   - Auto-migrate: {'YES' if self.config.auto_migrate else 'NO'}")
        logger.info(f"   - API Server: {'YES' if self.config.start_api_server or self.config.always_on else 'NO'}")
        logger.info(f"   - Telegram: {'YES' if self.config.send_telegram_alerts else 'NO'}")
        logger.info(f"   - Trading: {'PAPER' if self.config.paper_trading else 'LIVE'}")
        logger.info(f"   - Reports: {', '.join(self.config.report_formats) if self.config.generate_reports else 'DISABLED'}")

        if self.config.always_on:
            await self.run_always_on_mode()
        else:
            await self.run_batch_mode()

async def main():
    """Main entry point"""
    orchestrator = PatternIQOrchestrator()
    await orchestrator.run()

if __name__ == "__main__":
    asyncio.run(main())
