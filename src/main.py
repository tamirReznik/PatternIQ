# src/main.py

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

import uvicorn

from src.api.server import app
from src.common.config import config
from src.common.db_manager import db_manager
from src.data.demo_full_pipeline import demo_full_data_ingestion
from src.features.momentum import demo_momentum_features
from src.report.generator import generate_daily_report
from src.signals.blend import blend_signals_ic_weighted
from src.signals.rules import demo_signal_generation
from src.trading.simulator import AutoTradingBot

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PatternIQOrchestrator:
    """Main orchestrator for PatternIQ system"""

    def __init__(self):
        self.config = config
        self.trading_bot = None
        self.api_server = None

    async def run_daily_pipeline(self) -> bool:
        """Run the complete daily pipeline"""
        try:
            logger.info("🚀 Starting PatternIQ daily pipeline...")

            # 1. Data ingestion
            logger.info("📊 Step 1/7: Ingesting market data...")
            await asyncio.to_thread(demo_full_data_ingestion)

            # 2. Feature calculation
            logger.info("🔧 Step 2/7: Calculating features...")
            await asyncio.to_thread(demo_momentum_features)

            # 3. Signal generation
            logger.info("📡 Step 3/7: Generating signals...")
            await asyncio.to_thread(demo_signal_generation)

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
            logger.error(f"❌ Pipeline failed: {e}")
            return False

    async def run_trading(self):
        """Initialize and run trading bot"""
        try:
            if not self.trading_bot:
                self.trading_bot = AutoTradingBot(
                    initial_capital=self.config.initial_capital,
                    paper_trading=self.config.paper_trading,
                    max_position_size=self.config.max_position_size
                )

            # Process today's signals
            result = self.trading_bot.process_daily_report(datetime.now().date())
            logger.info(f"Trading result: {result.get('status', 'completed')}")

            # Log portfolio status
            status = self.trading_bot.get_portfolio_status()
            logger.info(f"Portfolio: ${status['initial_capital']:,.0f} → ${status['current_value']:,.0f} ({status['total_return']})")

        except Exception as e:
            logger.error(f"Trading simulation failed: {e}")

    async def send_telegram_alert(self):
        """Send Telegram notification"""
        try:
            from src.telegram.bot import PatternIQBot
            bot = PatternIQBot()

            # Get latest report data for notification
            reports_dir = Path("reports")
            latest_json = sorted(reports_dir.glob("*.json"))[-1] if reports_dir.glob("*.json") else None

            if latest_json:
                await bot.send_daily_report(latest_json)
                logger.info("Telegram alert sent successfully")
            else:
                logger.warning("No report found for Telegram alert")

        except Exception as e:
            logger.error(f"Telegram alert failed: {e}")

    async def start_api_server(self):
        """Start the API server"""
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
