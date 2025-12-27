#!/usr/bin/env python3
"""
Cloud deployment script for PatternIQ
Runs batch mode and uploads results to cloud storage
"""

import os
import json
import asyncio
import logging
from datetime import datetime, date
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Setup logging for cloud environment
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('patterniq_batch.log')
    ]
)
logger = logging.getLogger(__name__)

class CloudBatchRunner:
    """Batch runner optimized for cloud deployment"""

    def __init__(self):
        self.run_date = date.today()
        self.reports_dir = Path("reports")
        self.trading_dir = Path("trading_data")

    async def run_batch_with_cloud_features(self):
        """Run batch mode with cloud-specific enhancements"""
        logger.info("🚀 Starting PatternIQ Cloud Batch Mode")
        logger.info(f"📅 Run Date: {self.run_date}")

        # Set environment for batch mode
        os.environ['PATTERNIQ_ALWAYS_ON'] = 'false'
        os.environ['DB_MODE'] = 'auto'
        os.environ['GENERATE_REPORTS'] = 'true'
        os.environ['SEND_TELEGRAM_ALERTS'] = 'false'
        os.environ['START_API_SERVER'] = 'false'

        try:
            # Import and run main pipeline
            from src.main import main
            logger.info("📦 Running PatternIQ main pipeline...")
            await main()

            # Generate summary for cloud monitoring
            await self.generate_execution_summary()

            # Upload results to cloud storage (placeholder)
            await self.upload_results_to_cloud()

            logger.info("✅ Cloud batch execution completed successfully!")
            return True

        except Exception as e:
            logger.error(f"❌ Cloud batch execution failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def generate_execution_summary(self):
        """Generate a summary of the batch execution"""
        summary = {
            "execution_date": self.run_date.isoformat(),
            "execution_time": datetime.now().isoformat(),
            "status": "completed"
        }

        # Check for latest report
        latest_reports = list(self.reports_dir.glob("*.json"))
        if latest_reports:
            latest_report = max(latest_reports, key=lambda x: x.stat().st_mtime)
            summary["latest_report"] = str(latest_report.name)

            # Extract key metrics from report
            try:
                with open(latest_report, 'r') as f:
                    report_data = json.load(f)

                summary["report_metrics"] = {
                    "report_date": report_data.get("date"),
                    "market_sentiment": report_data.get("market_sentiment", {}).get("overall_signal", "N/A"),
                    "top_recommendations": len(report_data.get("top_long", [])),
                    "portfolio_return": report_data.get("portfolio_metrics", {}).get("total_return", "N/A")
                }
            except Exception as e:
                logger.warning(f"Could not extract report metrics: {e}")

        # Check portfolio status
        portfolio_file = self.trading_dir / "portfolio_state.json"
        if portfolio_file.exists():
            try:
                with open(portfolio_file, 'r') as f:
                    portfolio_data = json.load(f)

                summary["portfolio_status"] = {
                    "total_value": portfolio_data.get("cash_balance", 0) + sum(
                        pos.get("shares", 0) * pos.get("entry_price", 0)
                        for pos in portfolio_data.get("positions", {}).values()
                    ),
                    "cash_balance": portfolio_data.get("cash_balance", 0),
                    "positions_count": len(portfolio_data.get("positions", {})),
                    "total_trades": len(portfolio_data.get("trade_history", []))
                }
            except Exception as e:
                logger.warning(f"Could not extract portfolio metrics: {e}")

        # Save summary
        summary_file = Path("execution_summary.json")
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"📊 Execution summary saved to {summary_file}")
        return summary

    async def upload_results_to_cloud(self):
        """Upload reports and portfolio data to cloud storage"""
        # This is a placeholder for cloud storage integration
        # You would implement actual cloud storage upload here

        files_to_upload = []

        # Collect latest reports
        for report_file in self.reports_dir.glob("*.json"):
            if report_file.stat().st_mtime > (datetime.now().timestamp() - 86400):  # Last 24 hours
                files_to_upload.append(report_file)

        for report_file in self.reports_dir.glob("*.html"):
            if report_file.stat().st_mtime > (datetime.now().timestamp() - 86400):  # Last 24 hours
                files_to_upload.append(report_file)

        # Collect portfolio data
        portfolio_file = self.trading_dir / "portfolio_state.json"
        if portfolio_file.exists():
            files_to_upload.append(portfolio_file)

        # Collect execution summary
        summary_file = Path("execution_summary.json")
        if summary_file.exists():
            files_to_upload.append(summary_file)

        logger.info(f"📤 Would upload {len(files_to_upload)} files to cloud storage:")
        for file_path in files_to_upload:
            logger.info(f"   - {file_path}")

        # TODO: Implement actual cloud storage upload
        # Example for GCP Cloud Storage:
        # from google.cloud import storage
        # client = storage.Client()
        # bucket = client.bucket('patterniq-reports')
        # for file_path in files_to_upload:
        #     blob = bucket.blob(f"{self.run_date}/{file_path.name}")
        #     blob.upload_from_filename(file_path)

async def main():
    """Main entry point for cloud batch execution"""
    runner = CloudBatchRunner()
    success = await runner.run_batch_with_cloud_features()

    if success:
        print("🎯 Cloud batch execution completed successfully!")
        sys.exit(0)
    else:
        print("❌ Cloud batch execution failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
