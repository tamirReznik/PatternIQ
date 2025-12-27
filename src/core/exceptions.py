# src/core/exceptions.py - Custom exceptions for PatternIQ

"""
Custom exceptions for PatternIQ system
"""


class PatternIQException(Exception):
    """Base exception for all PatternIQ errors"""
    pass


class DataIngestionError(PatternIQException):
    """Error during data ingestion"""
    pass


class DatabaseError(PatternIQException):
    """Database operation error"""
    pass


class SignalGenerationError(PatternIQException):
    """Error during signal generation"""
    pass


class ReportGenerationError(PatternIQException):
    """Error during report generation"""
    pass


class TradingBotError(PatternIQException):
    """Error in trading bot operations"""
    pass


class ConfigurationError(PatternIQException):
    """Configuration error"""
    pass


class TelegramError(PatternIQException):
    """Telegram bot error"""
    pass


class BacktestError(PatternIQException):
    """Backtesting error"""
    pass


class ValidationError(PatternIQException):
    """Data validation error"""
    pass

