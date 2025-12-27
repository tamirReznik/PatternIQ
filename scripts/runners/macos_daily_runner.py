#!/usr/bin/env python3
"""
Enhanced batch runner for local macOS execution
Runs PatternIQ batch mode and generates static dashboard
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, date, timezone, timedelta
from pathlib import Path
import pytz

# Add project root to path (go up from scripts/runners/ to project root)
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('patterniq_daily.log')
    ]
)
logger = logging.getLogger(__name__)

class MacOSBatchRunner:
    """Batch runner optimized for macOS daily execution"""

    def __init__(self):
        self.run_date = date.today()
        # Get project root (go up from scripts/runners/ to project root)
        self.project_dir = Path(__file__).parent.parent.parent
        self.et_timezone = pytz.timezone('US/Eastern')
    
    def is_market_hours(self) -> bool:
        """Check if current time is during market hours (9:30 AM - 4:00 PM ET)"""
        et_now = datetime.now(self.et_timezone)
        market_open = et_now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = et_now.replace(hour=16, minute=0, second=0, microsecond=0)
        
        # Check if it's a weekday (Monday=0, Sunday=6)
        is_weekday = et_now.weekday() < 5
        
        return is_weekday and market_open <= et_now <= market_close
    
    def get_optimal_run_time(self) -> datetime:
        """Get optimal time to run (4:30 PM ET after market close)"""
        et_now = datetime.now(self.et_timezone)
        today_4_30_pm = et_now.replace(hour=16, minute=30, second=0, microsecond=0)
        
        # If it's before 4:30 PM today, use today
        # If it's after 4:30 PM, use tomorrow
        if et_now < today_4_30_pm:
            return today_4_30_pm
        else:
            return today_4_30_pm + timedelta(days=1)
    
    def should_wait_for_market_close(self) -> bool:
        """Determine if we should wait for market close before running"""
        if self.is_market_hours():
            logger.warning("⚠️  Running during market hours - data may not be complete")
            logger.info("💡 Consider scheduling runs after 4:30 PM ET for best results")
            return False  # Don't wait, but warn
        return False  # Not during market hours, proceed

    async def run_daily_batch(self):
        """Run complete daily batch with static dashboard generation"""
        logger.info("🚀 Starting PatternIQ Daily Batch (macOS)")
        logger.info(f"📅 Run Date: {self.run_date}")
        logger.info(f"📁 Project Directory: {self.project_dir}")
        
        # Check market hours and provide guidance
        et_now = datetime.now(self.et_timezone)
        logger.info(f"🕐 Current Time (ET): {et_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        if self.is_market_hours():
            logger.warning("⚠️  Running during market hours - EOD data may not be complete")
            logger.info("💡 Optimal run time: 4:30 PM ET (30 min after market close)")
        else:
            logger.info("✅ Running outside market hours - optimal for EOD data")

        try:
            # Step 1: Set environment for batch mode
            self.setup_environment()

            # Step 2: Run PatternIQ main pipeline
            logger.info("📊 Running PatternIQ main pipeline...")
            success = await self.run_patterniq_pipeline()

            if not success:
                logger.error("❌ PatternIQ pipeline failed!")
                return False

            # Step 3: Generate static dashboard
            logger.info("🌐 Generating static dashboard...")
            self.generate_static_dashboard()

            # Step 4: Log completion summary
            self.log_completion_summary()

            logger.info("✅ Daily batch completed successfully!")
            return True

        except Exception as e:
            logger.error(f"❌ Daily batch failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def setup_environment(self):
        """Setup environment variables for batch mode"""
        env_vars = {
            'PATTERNIQ_ALWAYS_ON': 'false',
            'DB_MODE': 'auto',
            'GENERATE_REPORTS': 'true',
            'SEND_TELEGRAM_ALERTS': 'true',  # Enable Telegram alerts
            'START_API_SERVER': 'false',
            'SQLITE_PATH': 'data/patterniq.db'
        }

        # Load environment variables from .env file if it exists
        env_file = self.project_dir / '.env'
        if env_file.exists():
            logger.info("📁 Loading environment variables from .env file...")
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value

        logger.info("🔧 Setting environment variables...")
        for key, value in env_vars.items():
            os.environ[key] = value
            logger.info(f"   {key} = {value}")

    async def run_patterniq_pipeline(self):
        """Run the main PatternIQ pipeline"""
        try:
            from src.main import main
            await main()
            return True
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Send error notification if possible
            try:
                from src.telegram.bot import PatternIQBot
                bot = PatternIQBot()
                if bot.bot and bot.chat_ids:
                    await bot.send_alert(
                        f"PatternIQ daily run failed: {str(e)}",
                        priority="high"
                    )
            except Exception as telegram_error:
                logger.warning(f"Could not send error notification: {telegram_error}")
            return False

    def generate_static_dashboard(self):
        """Generate static HTML dashboard"""
        try:
            # Add dashboard scripts to path
            dashboard_scripts = self.project_dir / "scripts" / "dashboard"
            if str(dashboard_scripts) not in sys.path:
                sys.path.insert(0, str(dashboard_scripts))
            from static_dashboard_generator import StaticReportGenerator
            generator = StaticReportGenerator()
            dashboard_file = generator.generate_static_dashboard()

            logger.info(f"📊 Static dashboard generated: {dashboard_file}")

            # Create a convenient link in the project root
            root_link = self.project_dir / "dashboard.html"
            if root_link.exists():
                root_link.unlink()

            # Create symbolic link for easy access
            try:
                root_link.symlink_to(dashboard_file.relative_to(self.project_dir))
                logger.info(f"🔗 Dashboard link created: {root_link}")
            except Exception as e:
                logger.warning(f"Could not create dashboard link: {e}")

        except Exception as e:
            logger.error(f"Dashboard generation failed: {e}")

    def log_completion_summary(self):
        """Log a summary of what was accomplished"""
        reports_dir = Path("reports")
        trading_dir = Path("trading_data")
        dashboard_dir = Path("dashboard_static")

        logger.info("📋 Execution Summary:")

        # Check reports
        if reports_dir.exists():
            recent_reports = [f for f in reports_dir.glob("*.json")
                            if f.stat().st_mtime > (datetime.now().timestamp() - 86400)]
            logger.info(f"   📊 Reports generated: {len(recent_reports)}")

        # Check portfolio
        portfolio_file = trading_dir / "portfolio_state.json"
        if portfolio_file.exists():
            try:
                import json
                with open(portfolio_file, 'r') as f:
                    portfolio = json.load(f)

                current_value = portfolio.get('cash_balance', 0)
                for pos in portfolio.get('positions', {}).values():
                    current_value += pos.get('shares', 0) * pos.get('entry_price', 0)

                trades_count = len(portfolio.get('trade_history', []))
                logger.info(f"   💼 Portfolio value: ${current_value:,.2f}")
                logger.info(f"   📈 Total trades: {trades_count}")
            except Exception as e:
                logger.warning(f"Could not read portfolio data: {e}")

        # Check dashboard
        if dashboard_dir.exists():
            dashboard_file = dashboard_dir / "index.html"
            if dashboard_file.exists():
                logger.info(f"   🌐 Dashboard: file://{dashboard_file.absolute()}")

async def main():
    """Main entry point for daily batch execution"""
    print("🤖 PatternIQ Daily Batch Runner (macOS)")
    print("=" * 50)

    runner = MacOSBatchRunner()
    success = await runner.run_daily_batch()

    if success:
        print("\\n🎯 Daily batch completed successfully!")
        print("🌐 Open dashboard: ./dashboard.html")
        sys.exit(0)
    else:
        print("\\n❌ Daily batch failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
