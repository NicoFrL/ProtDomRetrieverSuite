# src/processors/base_processor.py
from typing import Optional, Callable
from dataclasses import dataclass
from pathlib import Path
import logging

from ..utils.errors import ProcessingError, handle_processing_errors
from ..utils.logger import LoggerSetup
from ..utils.config import BaseConfig, ConfigManager

@dataclass
class BaseConfig:
    """Base configuration for all components."""
    output_dir: Path
    log_dir: Optional[Path] = None
    max_retries: int = 3
    timeout: int = 300

@dataclass
class ProcessorConfig(BaseConfig):
    """Extended configuration for processors with caching and batch processing.
    
    Attributes:
        batch_size: Number of items to process in one batch
        cache_enabled: Whether to cache results
        cache_ttl: Time-to-live for cached items in seconds
    """
    batch_size: int = 100
    cache_enabled: bool = True
    cache_ttl: int = 86400  # 24 hours
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        super().__post_init__() if hasattr(BaseConfig, '__post_init__') else None
        if self.batch_size < 1:
            raise ValueError("batch_size must be positive")
        if self.cache_ttl < 0:
            raise ValueError("cache_ttl must be non-negative")

class BaseProcessor:
    """Base class for all processors"""
    
    def __init__(self,
                 config: Optional[ProcessorConfig] = None,
                 logger: Optional[logging.Logger] = None,
                 callback: Optional[Callable[[str, float], None]] = None):
        """Initialize base processor.
        
        Args:
            config: Processor configuration. If None, loads from config manager
            logger: Optional custom logger. If None, creates from logger setup
            callback: Optional progress callback function
        """
        if config is None:
            config_manager = ConfigManager()
            base_config = config_manager.get_base_config()
            self.config = ProcessorConfig(
                output_dir=base_config.output_dir,
                log_dir=base_config.log_dir,
                max_retries=base_config.max_retries,
                timeout=base_config.timeout
            )
        else:
            self.config = config

        self.logger = logger or LoggerSetup(self.config.log_dir).get_logger(self.__class__.__name__)
        self.callback = callback
        
        # Validate configuration on initialization
        if not self.validate_config():
            raise ProcessingError("Invalid processor configuration")

    def validate_config(self) -> bool:
        """Validate processor configuration"""
        try:
            # Base validations
            if not self.config.output_dir:
                self.logger.error("No output directory specified")
                return False
                
            if not isinstance(self.config.max_retries, int) or self.config.max_retries < 1:
                self.logger.error("Invalid max_retries value")
                return False
                
            if not isinstance(self.config.timeout, int) or self.config.timeout < 1:
                self.logger.error("Invalid timeout value")
                return False
            
            # ProcessorConfig specific validations
            if hasattr(self.config, 'batch_size'):
                if not isinstance(self.config.batch_size, int) or self.config.batch_size < 1:
                    self.logger.error("Invalid batch_size value")
                    return False
                    
            if hasattr(self.config, 'cache_ttl'):
                if not isinstance(self.config.cache_ttl, int) or self.config.cache_ttl < 0:
                    self.logger.error("Invalid cache_ttl value")
                    return False
            
            # Create output directory if it doesn't exist
            try:
                self.config.output_dir.mkdir(parents=True, exist_ok=True)
                return True
            except Exception as e:
                self.logger.error(f"Failed to create output directory: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"Configuration validation error: {e}")
            return False

    def _should_use_cache(self) -> bool:
        """Helper to check if caching should be used"""
        return (
            hasattr(self.config, 'cache_enabled') and
            self.config.cache_enabled
        )

    def update_status(self, message: str, progress: float):
        """Update processing status
        
        Args:
            message: Status message
            progress: Progress percentage (0-100)
        """
        progress = max(0, min(100, progress))  # Clamp between 0-100
        self.logger.info(f"{message} - {progress:.1f}%")
        if self.callback:
            try:
                self.callback(message, progress)
            except Exception as e:
                self.logger.warning(f"Error in callback: {e}")

    @handle_processing_errors
    def process(self, *args, **kwargs):
        """Main processing method to be implemented by subclasses
        
        Raises:
            NotImplementedError: If not implemented by subclass
            ProcessingError: On processing errors
        """
        raise NotImplementedError("Subclasses must implement process method")

    def cleanup(self):
        """Cleanup method to be called when processing is complete
        Can be overridden by subclasses for specific cleanup needs
        """
        pass

    def __enter__(self):
        """Support for context manager protocol"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure cleanup is called when using context manager"""
        self.cleanup()
