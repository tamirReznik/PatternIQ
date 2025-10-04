#!/usr/bin/env python3
# run_patterniq.py - Simple CLI for PatternIQ

import asyncio
import argparse
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.main import main

def setup_environment(mode: str, **kwargs):
    """Setup environment variables based on mode"""

    if mode == "batch":
        os.environ["PATTERNIQ_ALWAYS_ON"] = "false"
        os.environ["START_API_SERVER"] = "false"
        print("🏃 Configured for BATCH mode (run once and exit)")

    elif mode == "always-on":
        os.environ["PATTERNIQ_ALWAYS_ON"] = "true"
        os.environ["START_API_SERVER"] = "true"
        print("🔄 Configured for ALWAYS-ON mode (continuous)")

    elif mode == "api-only":
        os.environ["PATTERNIQ_ALWAYS_ON"] = "false"
        os.environ["START_API_SERVER"] = "true"
        print("🌐 Configured for API-ONLY mode (server only, no pipeline)")

    # Database mode configuration
    if kwargs.get("db_mode"):
        os.environ["DB_MODE"] = kwargs["db_mode"]
        print(f"💾 Database mode: {kwargs['db_mode']}")

    if kwargs.get("sqlite_path"):
        os.environ["SQLITE_PATH"] = kwargs["sqlite_path"]
        print(f"📁 SQLite path: {kwargs['sqlite_path']}")

    if kwargs.get("no_migrate"):
        os.environ["AUTO_MIGRATE"] = "false"
        print("🚫 Auto-migration disabled")

    # Optional overrides
    if kwargs.get("telegram"):
        os.environ["SEND_TELEGRAM_ALERTS"] = "true"
        print("📱 Telegram alerts enabled")

    if kwargs.get("live_trading"):
        os.environ["PAPER_TRADING"] = "false"
        print("⚠️  LIVE TRADING enabled (use with caution!)")

    if kwargs.get("port"):
        os.environ["API_PORT"] = str(kwargs["port"])
        print(f"🌐 API server will run on port {kwargs['port']}")

def main_cli():
    parser = argparse.ArgumentParser(
        description="PatternIQ - Advanced Quantitative Trading System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_patterniq.py batch                    # Run once and exit
  python run_patterniq.py always-on               # Run continuously  
  python run_patterniq.py batch --telegram        # Run once with Telegram
  python run_patterniq.py always-on --port 9000   # Always-on mode on port 9000
  python run_patterniq.py api-only                # Start API server only
        """
    )

    parser.add_argument(
        "mode",
        choices=["batch", "always-on", "api-only"],
        help="Operating mode"
    )

    parser.add_argument(
        "--telegram",
        action="store_true",
        help="Enable Telegram notifications"
    )

    parser.add_argument(
        "--live-trading",
        action="store_true",
        help="Enable live trading (default: paper trading)"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="API server port (default: 8000)"
    )

    # Database configuration arguments
    parser.add_argument(
        "--db-mode",
        choices=["auto", "file", "sqlite", "postgres"],
        default="auto",
        help="Database mode: auto (default), file/sqlite, or postgres"
    )

    parser.add_argument(
        "--sqlite-path",
        default="data/patterniq.db",
        help="Path for SQLite database file (default: data/patterniq.db)"
    )

    parser.add_argument(
        "--no-migrate",
        action="store_true",
        help="Disable automatic database migration"
    )

    args = parser.parse_args()

    # Setup environment
    setup_environment(
        args.mode,
        telegram=args.telegram,
        live_trading=args.live_trading,
        port=args.port,
        db_mode=args.db_mode,
        sqlite_path=args.sqlite_path,
        no_migrate=args.no_migrate
    )

    print(f"\n🤖 Starting PatternIQ in {args.mode.upper()} mode...")
    print("   Press Ctrl+C to stop\n")

    # Run the system
    if args.mode == "api-only":
        # Special case: just start API server
        import uvicorn
        from src.api.server import app
        uvicorn.run(app, host="127.0.0.1", port=args.port)
    else:
        asyncio.run(main())

if __name__ == "__main__":
    main_cli()
