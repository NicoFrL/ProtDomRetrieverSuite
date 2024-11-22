import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

class LoggerSetup:
    """Handles logging configuration for the application"""
    
    def __init__(self, log_dir: Optional[Path] = None):
        """
        Initialize logger setup
        
        Args:
            log_dir: Directory for log files. If None, logs only to console.
        """
        self.log_dir = log_dir
        if log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)

    def setup_logger(self, name: str = "ProtDomRetriever") -> logging.Logger:
        """
        Configure and return a logger instance
        
        Args:
            name: Logger name
            
        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers to avoid duplicates
        logger.handlers.clear()
        
        # Console handler with INFO level
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler with DEBUG level if log_dir is provided
        if self.log_dir:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = self.log_dir / f"{name}_{timestamp}.log"
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        
        return logger

    @staticmethod
    def get_logger(name: str = "ProtDomRetriever") -> logging.Logger:
        """
        Get existing logger or create new one
        
        Args:
            name: Logger name
            
        Returns:
            Logger instance
        """
        logger = logging.getLogger(name)
        if not logger.handlers:
            LoggerSetup().setup_logger(name)
        return logger
