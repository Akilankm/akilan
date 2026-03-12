from loguru import logger
import sys
from typing import Any


def setup_logger(level: str = "INFO"):
    logger.remove()

    logger.add(
        sys.stdout,
        level=level,
        enqueue=False,
        backtrace=True,
        diagnose=False,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
    )

    return logger


log = setup_logger()

def get_logger(**context: Any):
    return log.bind(**context)