from enum import Enum


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


def get_log_level(log_level_str: str) -> LogLevel:
    try:
        if log_level_str:
            return LogLevel[log_level_str.upper()]
    except Exception:
        return LogLevel.INFO
    return LogLevel.INFO