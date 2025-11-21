from loguru import logger
import sys
import os
import threading
from datetime import datetime
from pathlib import Path
from ai_app.logger.thread_local_context import get_txid
from ai_app.logger.log_level import LogLevel


def app_record(record):
    record = extra_record(record)
    return record["extra"].get("logger_name") == "app_logger"


def access_record(record):
    record = extra_record(record)
    return record["extra"].get("logger_name") == "access_logger"


def outbound_access_record(record):
    record = extra_record(record)
    return record["extra"].get("logger_name") == "outbound_access_logger"


def extra_record(record):
    record["extra"]["processname"] = os.getpid()
    record["extra"]["processid"] = os.getpid()
    record["extra"]["threadname"] = threading.current_thread().name
    record["extra"]["threadid"] = threading.get_ident()
    record["extra"]["txid"] = get_txid()
    return record


class CustomFormatter:
    def __init__(self, format_str):
        self.format_str = format_str

    def __call__(self, record):
        time_str = datetime.fromtimestamp(record["time"].timestamp()).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        milliseconds = int(record["time"].microsecond / 1000)
        time_str_with_ms = f"{time_str}.{milliseconds:03d}"
        return self.format_str.format(
            time=time_str_with_ms,
            level=record["level"].name,
            module=record["module"],
            function=record["function"],
            processname=record["extra"].get("processname", "N/A"),
            processid=record["extra"].get("processid", "N/A"),
            threadname=record["extra"].get("threadname", "N/A"),
            threadid=record["extra"].get("threadid", "N/A"),
            txid=record["extra"].get("txid", "N/A"),
            message=record["message"],  # escaped_message,
        )


access_format = "{time} {txid} {{message}}\n"
outbound_access_format = "{time} {txid} {{message}}\n"
app_format = (
    "{time} {level} {processid} "
    "{threadname} {threadid} {{module}} {{function}} {txid} {{message}}\n"
)


def configure_logging(
    app_log_path: str = "app.log",
    access_log_path: str = "inbound_access.log",
    outbound_access_log_path: str = "outbound_access.log",
    app_file_log_level: LogLevel = LogLevel.INFO,
    app_console_log_level: LogLevel = LogLevel.INFO,
    enable_app_console_logging: bool = True,
    enable_access_logging: bool = True,
    enable_access_console_logging: bool = True,
    enable_outbound_access_logging: bool = True,
    enable_outbound_access_console_logging: bool = True,
    log_retention_in_days: int = 30,
    enable_json_logging: bool = False,
):
    """
    Sets logger for file based application logging, console based application logging,
    file based access logging and console based access logging based on arguments.
    Log levels are supported for Application logging.
    Support json format logging.
    Args:
        app_log_path (str, optional): relative or absolute application log path. Defaults to "app.log".
        access_log_path (str, optional): relative or absolute access log path. Defaults to "access.log".
        outbound_access_log_path (str, optional): relative or absolute outbound access log path. Defaults to "outbound_access.log".
        app_file_log_level (LogLevel, optional): File log level. Defaults to LogLevel.INFO.Supported values - DEBUG, INFO, WARNING, ERROR, CRITICAL
        app_console_log_level (LogLevel, optional): Console log level. Defaults to LogLevel.INFO.Supported values - DEBUG, INFO, WARNING, ERROR, CRITICAL
        enable_app_console_logging (bool, optional): Enable or Disable console based application logging. Defaults to True.
        enable_access_logging (bool, optional): Enable or Disable access logging. Defaults to True.
        enable_access_console_logging (bool, optional): Enable or Disable access console logging. Defaults to True.
        enable_outbound_access_logging (bool, optional): Enable or Disable outbound access logging. Defaults to True.
        enable_outbound_access_console_logging (bool, optional): Enable or Disable outbound access console logging. Defaults to True.
        log_retention_in_days (int, optional): Log rentention in days. Defaults to 30.
        enable_json_logging (bool, optional): Print log statements in json format. Defaults to False.
    """
    setup_logging(
        app_log_path,
        access_log_path,
        app_file_log_level,
        app_console_log_level,
        enable_app_console_logging,
        enable_access_logging,
        enable_access_console_logging,
        log_retention_in_days,
        enable_json_logging,
    )
    # logger.remove()

    # Path(app_log_path).parent.mkdir(parents=True, exist_ok=True)
    # Path(access_log_path).parent.mkdir(parents=True, exist_ok=True)
    Path(outbound_access_log_path).parent.mkdir(parents=True, exist_ok=True)

    if enable_outbound_access_logging:
        logger.add(
            outbound_access_log_path,
            rotation="00:00",
            retention=str(log_retention_in_days) + " days",
            level="INFO",
            encoding="utf-8",
            format=CustomFormatter(outbound_access_format),
            filter=outbound_access_record,
            enqueue=True,
            colorize=True,
            serialize=enable_json_logging,
        )
        if enable_outbound_access_console_logging:
            logger.add(
                sys.stdout,
                level="INFO",
                format=CustomFormatter(outbound_access_format),
                filter=outbound_access_record,
                enqueue=True,
                colorize=True,
                serialize=enable_json_logging,
            )


def setup_logging(
    app_log_path: str = "app.log",
    access_log_path: str = "access.log",
    app_file_log_level: LogLevel = LogLevel.INFO,
    app_console_log_level: LogLevel = LogLevel.INFO,
    enable_app_console_logging: bool = True,
    enable_access_logging: bool = True,
    enable_access_console_logging: bool = True,
    log_retention_in_days: int = 30,
    enable_json_logging: bool = False,
):
    """
    Sets logger for file based application logging, console based application logging,
    file based access logging and console based access logging based on arguments.
    Log levels are supported for Application logging.
    Support json format logging.
    Args:
        app_log_path (str, optional): relative or absolute application log path. Defaults to "app.log".
        access_log_path (str, optional): relative or absolute access log path. Defaults to "access.log".
        app_file_log_level (LogLevel, optional): File log level. Defaults to LogLevel.INFO.Supported values - DEBUG, INFO, WARNING, ERROR, CRITICAL
        app_console_log_level (LogLevel, optional): Console log level. Defaults to LogLevel.INFO.Supported values - DEBUG, INFO, WARNING, ERROR, CRITICAL
        enable_app_console_logging (bool, optional): Enable or Disable console based application logging. Defaults to True.
        enable_access_logging (bool, optional): Enable or Disable access logging. Defaults to True.
        enable_access_console_logging (bool, optional): Enable or Disable access console logging. Defaults to True.
        log_retention_in_days (int, optional): Log rentention in days. Defaults to 30.
        enable_json_logging (bool, optional): Print log statements in json format. Defaults to False.
    """
    logger.remove()

    Path(app_log_path).parent.mkdir(parents=True, exist_ok=True)
    Path(access_log_path).parent.mkdir(parents=True, exist_ok=True)

    if enable_access_logging:
        logger.add(
            access_log_path,
            rotation="00:00",
            retention=str(log_retention_in_days) + " days",
            level="INFO",
            encoding="utf-8",
            format=CustomFormatter(access_format),
            filter=access_record,
            enqueue=True,
            colorize=True,
            serialize=enable_json_logging,
        )
        if enable_access_console_logging:
            logger.add(
                sys.stdout,
                level="INFO",
                format=CustomFormatter(access_format),
                filter=access_record,
                enqueue=True,
                colorize=True,
                serialize=enable_json_logging,
            )

    logger.add(
        app_log_path,
        rotation="00:00",
        retention=str(log_retention_in_days) + " days",  # "30 days",
        level=app_file_log_level.value,
        encoding="utf-8",
        format=CustomFormatter(app_format),
        filter=app_record,
        enqueue=True,
        colorize=True,
        serialize=enable_json_logging,
    )
    if enable_app_console_logging:
        logger.add(
            sys.stdout,
            level=app_console_log_level.value,
            format=CustomFormatter(app_format),
            filter=app_record,
            enqueue=True,
            colorize=True,
            serialize=enable_json_logging,
        )


def get_app_logger():
    return logger.bind(logger_name="app_logger")


def get_access_logger():
    return logger.bind(logger_name="access_logger")


def get_inbound_access_logger():
    return logger.bind(logger_name="access_logger")


def get_outbound_access_logger():
    return logger.bind(logger_name="outbound_access_logger")