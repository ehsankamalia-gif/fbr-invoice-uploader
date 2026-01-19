import logging
import sys
from .config import settings

def setup_logger(name: str = "fbr_uploader"):
    logger = logging.getLogger(name)
    logger.setLevel(settings.LOG_LEVEL)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Console Handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File Handler
    fh = logging.FileHandler("fbr_uploader.log")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger

logger = setup_logger()
