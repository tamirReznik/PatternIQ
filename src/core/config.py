# src/core/config.py - Centralized configuration management

"""
Centralized configuration for PatternIQ system
Supports demo and production modes
"""

import os
from typing import Optional, List
from dataclasses import dataclass
from pathlib import Path

from src.core.exceptions import ConfigurationError


@dataclass
class PatternIQConfig:
    """Configuration for PatternIQ system"""

    # System Mode
    demo_mode: bool = False  # If True, uses sample data and limited processing
    always_on: bool = False  # If False, runs once and exits (batch mode)

    # Database Configuration
    db_url: str = "postgresql://admin:secret@localhost:5432/patterniq"
    db_mode: str = "auto"  # "auto", "file", "postgres", "sqlite"
    sqlite_path: str = "data/patterniq.db"
    auto_migrate: bool = True  # Auto-migrate data when switching modes

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
    max_position_size: float = 0.05
    enable_multi_asset: bool = True
    leverage_multiplier: float = 1.2

    # Reports
    generate_reports: bool = True
    report_formats: List[str] = None  # ["json", "html", "pdf"]

    # Data
    universe: str = "SP500"
    lookback_days: int = 1800  # ~5 years
    demo_symbols_limit: int = 5  # For demo mode
    
    # Data Quality Filters (for mid/long-term trading)
    min_daily_volume: float = 10_000_000  # $10M minimum daily volume
    min_market_cap: float = 1_000_000_000  # $1B minimum market cap
    min_days_listed: int = 90  # At least 90 days of trading history

    # Time Horizon Strategies
    enable_time_horizons: bool = True
    default_time_horizon: str = "mid"  # "short", "mid", "long"

    def __post_init__(self):
        if self.report_formats is None:
            self.report_formats = ["json", "html"]

    def validate(self) -> None:
        """Validate configuration and raise ConfigurationError if invalid"""
        errors = []

        # Validate database mode
        if self.db_mode not in ["auto", "file", "sqlite", "postgres"]:
            errors.append(f"Invalid db_mode: {self.db_mode}")

        # Validate API port
        if not (1 <= self.api_port <= 65535):
            errors.append(f"Invalid API port: {self.api_port}")

        # Validate trading parameters
        if self.initial_capital <= 0:
            errors.append(f"Initial capital must be positive: {self.initial_capital}")
        if not (0 < self.max_position_size <= 1.0):
            errors.append(f"Max position size must be between 0 and 1: {self.max_position_size}")
        if not (1.0 <= self.leverage_multiplier <= 2.0):
            errors.append(f"Leverage multiplier must be between 1.0 and 2.0: {self.leverage_multiplier}")

        # Validate time horizon
        if self.default_time_horizon not in ["short", "mid", "long"]:
            errors.append(f"Invalid default_time_horizon: {self.default_time_horizon}")

        # Validate Telegram if enabled
        if self.send_telegram_alerts:
            if not self.telegram_bot_token:
                errors.append("TELEGRAM_BOT_TOKEN required when send_telegram_alerts is True")
            if not self.telegram_chat_ids:
                errors.append("TELEGRAM_CHAT_IDS required when send_telegram_alerts is True")

        if errors:
            raise ConfigurationError(f"Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

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
            raise ConfigurationError(f"Invalid db_mode: {self.db_mode}")

    def is_using_sqlite(self) -> bool:
        """Check if currently using SQLite"""
        return self.get_effective_db_url().startswith("sqlite://")

    def is_using_postgres(self) -> bool:
        """Check if currently using PostgreSQL"""
        return self.get_effective_db_url().startswith("postgresql://")

    def get_telegram_chat_ids_list(self) -> List[int]:
        """Parse and return Telegram chat IDs as list"""
        if not self.telegram_chat_ids:
            return []
        return [int(chat_id.strip()) for chat_id in self.telegram_chat_ids.split(",") if chat_id.strip()]


def load_config() -> PatternIQConfig:
    """Load configuration from environment variables"""
    # Load .env file if it exists (before reading env vars)
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        # #region agent log
        DEBUG_LOG_PATH = "/Users/tamirreznik/code/private/PatternIQ/.cursor/debug.log"
        try:
            import json
            with open(DEBUG_LOG_PATH, "a") as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "D",
                    "location": "config.py:131",
                    "message": "Loading .env file",
                    "data": {
                        "env_file_path": str(env_file),
                        "file_exists": True
                    },
                    "timestamp": int(__import__('datetime').datetime.now().timestamp() * 1000)
                }) + "\n")
        except: pass
        # #endregion
        
        # Manually parse .env file (simple implementation)
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    # Only set if not already in environment (env vars take precedence)
                    if key not in os.environ:
                        os.environ[key] = value
                        # #region agent log
                        try:
                            with open(DEBUG_LOG_PATH, "a") as f:
                                f.write(json.dumps({
                                    "sessionId": "debug-session",
                                    "runId": "run1",
                                    "hypothesisId": "D",
                                    "location": "config.py:155",
                                    "message": "Loaded env var from .env",
                                    "data": {
                                        "key": key,
                                        "value_length": len(value),
                                        "value_preview": value[:20] + "..." if len(value) > 20 else value
                                    },
                                    "timestamp": int(__import__('datetime').datetime.now().timestamp() * 1000)
                                }) + "\n")
                        except: pass
                        # #endregion
    
    # #region agent log
    try:
        import json
        DEBUG_LOG_PATH = "/Users/tamirreznik/code/private/PatternIQ/.cursor/debug.log"
        with open(DEBUG_LOG_PATH, "a") as f:
            f.write(json.dumps({
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "D",
                "location": "config.py:170",
                "message": "Reading env vars for Telegram",
                "data": {
                    "TELEGRAM_BOT_TOKEN": "SET" if os.getenv("TELEGRAM_BOT_TOKEN") else "NOT SET",
                    "TELEGRAM_CHAT_IDS": "SET" if os.getenv("TELEGRAM_CHAT_IDS") else "NOT SET",
                    "SEND_TELEGRAM_ALERTS": os.getenv("SEND_TELEGRAM_ALERTS", "NOT SET")
                },
                "timestamp": int(__import__('datetime').datetime.now().timestamp() * 1000)
            }) + "\n")
    except: pass
    # #endregion
    
    config = PatternIQConfig(
        # System Mode
        demo_mode=os.getenv("DEMO_MODE", "false").lower() == "true",
        always_on=os.getenv("PATTERNIQ_ALWAYS_ON", "false").lower() == "true",

        # Database
        db_url=os.getenv("PATTERNIQ_DB_URL", "postgresql://admin:secret@localhost:5432/patterniq"),
        db_mode=os.getenv("DB_MODE", "auto").lower(),
        sqlite_path=os.getenv("SQLITE_PATH", "data/patterniq.db"),
        auto_migrate=os.getenv("AUTO_MIGRATE", "true").lower() == "true",

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
        enable_multi_asset=os.getenv("ENABLE_MULTI_ASSET", "true").lower() == "true",
        leverage_multiplier=float(os.getenv("LEVERAGE_MULTIPLIER", "1.2")),

        # Reports
        generate_reports=os.getenv("GENERATE_REPORTS", "true").lower() == "true",
        report_formats=os.getenv("REPORT_FORMATS", "json,html").split(","),

        # Data
        universe=os.getenv("UNIVERSE", "SP500"),
        lookback_days=int(os.getenv("LOOKBACK_DAYS", "1800")),
        demo_symbols_limit=int(os.getenv("DEMO_SYMBOLS_LIMIT", "5")),
        
        # Data Quality Filters
        min_daily_volume=float(os.getenv("MIN_DAILY_VOLUME", "10000000")),
        min_market_cap=float(os.getenv("MIN_MARKET_CAP", "1000000000")),
        min_days_listed=int(os.getenv("MIN_DAYS_LISTED", "90")),

        # Time Horizons
        enable_time_horizons=os.getenv("ENABLE_TIME_HORIZONS", "true").lower() == "true",
        default_time_horizon=os.getenv("DEFAULT_TIME_HORIZON", "mid").lower(),
    )

    # Validate configuration
    try:
        config.validate()
    except ConfigurationError as e:
        # Log but don't fail - allow system to start with warnings
        import logging
        logger = logging.getLogger("PatternIQConfig")
        logger.warning(f"Configuration validation warnings: {e}")

    return config


# Global config instance
config = load_config()

