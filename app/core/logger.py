import logging
import sys
import os
from pathlib import Path
from app.core.config import settings

# Create logs directory
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

class Logger:
    def __init__(self, name: str, log_file: str = "app.log"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(settings.LOG_LEVEL)
        
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        
        # File Handler
        file_handler = logging.FileHandler(log_dir / log_file)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Stream Handler (Console)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        self.logger.addHandler(stream_handler)

    def info(self, msg: str):
        self.logger.info(msg)
    
    def error(self, msg: str):
        self.logger.error(msg)
        
    def warning(self, msg: str):
        self.logger.warning(msg)
        
    def debug(self, msg: str):
        self.logger.debug(msg)
    
    def exception(self, msg: str):
        self.logger.exception(msg)

# Create global logger instance
logger = Logger(settings.APP_NAME)
