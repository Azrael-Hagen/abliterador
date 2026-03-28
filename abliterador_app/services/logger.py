import logging
import os
from logging.handlers import RotatingFileHandler


_LOGGER_NAME = "abliterador"
_LOG_PATH = os.path.join(os.getcwd(), "logs", "abliterador.log")


def setup_app_logging() -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers:
        return logger

    os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    file_handler = RotatingFileHandler(_LOG_PATH, maxBytes=1_000_000, backupCount=4, encoding="utf-8")
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.propagate = False
    logger.info("Logger inicializado. Ruta: %s", _LOG_PATH)
    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger(_LOGGER_NAME)


def get_log_path() -> str:
    return _LOG_PATH
