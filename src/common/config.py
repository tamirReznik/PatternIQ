# src/common/config.py

import os
from typing import Optional
from dataclasses import dataclass

@dataclass
class PatternIQConfig:
    """Configuration for PatternIQ system"""

    # Database Configuration
    db_url: str = "postgresql://admin:secret@localhost:5432/patterniq"
    db_mode: str = "auto"  # "auto", "file", "postgres", "sqlite"
    sqlite_path: str = "data/patterniq.db"
    auto_migrate: bool = True  # Auto-migrate data when switching modes

    # System Mode
    always_on: bool = False  # If False, runs once and exits (batch mode)

    # API Server
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    start_api_server: bool = False  # Only start if always_on=True or explicitly requested

    # Telegram
    telegram_bot_token: Optional[str] = None
    telegram_chat_ids: Optional[str] = None
    send_telegram_alerts: bool = False

    # Trading
    paper_trading: bool = True
    initial_capital: float = 100000.0
    max_position_size: float = 0.05  # 5%

    # Reports
    generate_reports: bool = True
    report_formats: list = None  # ["json", "html", "pdf"]

    # Data
    universe: str = "SP500"
    lookback_days: int = 1800  # ~5 years

    def __post_init__(self):
        if self.report_formats is None:
            self.report_formats = ["json", "html"]

    def get_effective_db_url(self) -> str:
        """Get the effective database URL based on mode and configuration"""
        if self.db_mode == "auto":
            # Auto-select based on always_on mode
            if self.always_on:
                return self.db_url  # Use PostgreSQL for always-on
            else:
                # Use SQLite for batch mode
                os.makedirs(os.path.dirname(self.sqlite_path), exist_ok=True)
                return f"sqlite:///{self.sqlite_path}"
        elif self.db_mode == "file" or self.db_mode == "sqlite":
            os.makedirs(os.path.dirname(self.sqlite_path), exist_ok=True)
            return f"sqlite:///{self.sqlite_path}"
        elif self.db_mode == "postgres":
            return self.db_url
        else:
            raise ValueError(f"Invalid db_mode: {self.db_mode}")

    def is_using_sqlite(self) -> bool:
        """Check if currently using SQLite"""
        return self.get_effective_db_url().startswith("sqlite://")

    def is_using_postgres(self) -> bool:
        """Check if currently using PostgreSQL"""
        return self.get_effective_db_url().startswith("postgresql://")

def load_config() -> PatternIQConfig:
    """Load configuration from environment variables"""
    return PatternIQConfig(
        # Database
        db_url=os.getenv("PATTERNIQ_DB_URL", "postgresql://admin:secret@localhost:5432/patterniq"),
        db_mode=os.getenv("DB_MODE", "auto").lower(),
        sqlite_path=os.getenv("SQLITE_PATH", "data/patterniq.db"),
        auto_migrate=os.getenv("AUTO_MIGRATE", "true").lower() == "true",

        # System Mode
        always_on=os.getenv("PATTERNIQ_ALWAYS_ON", "false").lower() == "true",

        # API
        api_host=os.getenv("API_HOST", "127.0.0.1"),
        api_port=int(os.getenv("API_PORT", "8000")),
        start_api_server=os.getenv("START_API_SERVER", "false").lower() == "true",

        # Telegram
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        telegram_chat_ids=os.getenv("TELEGRAM_CHAT_IDS"),
        send_telegram_alerts=os.getenv("SEND_TELEGRAM_ALERTS", "false").lower() == "true",

        # Trading
        paper_trading=os.getenv("PAPER_TRADING", "true").lower() == "true",
        initial_capital=float(os.getenv("INITIAL_CAPITAL", "100000.0")),
        max_position_size=float(os.getenv("MAX_POSITION_SIZE", "0.05")),

        # Reports
        generate_reports=os.getenv("GENERATE_REPORTS", "true").lower() == "true",
        report_formats=os.getenv("REPORT_FORMATS", "json,html").split(","),

        # Data
        universe=os.getenv("UNIVERSE", "SP500"),
        lookback_days=int(os.getenv("LOOKBACK_DAYS", "1800")),
    )

# Global config instance
config = load_config()
