"""
Configuration management for ProtDomRetriever Suite.

This module handles all configuration aspects of the application, including:
- File paths and directories
- API endpoints and settings
- Processing parameters
- Caching behavior

The configuration system is based on three levels:
1. BaseConfig: Basic settings for all components
2. ProcessorConfig: Extended settings for data processors
3. APIConfig: Specific settings for API interactions

Configuration can be loaded from a JSON file or uses sensible defaults.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any
import json
import os

@dataclass
class BaseConfig:
    """Base configuration for all components.
    
    This class defines the fundamental settings needed by all components
    of the application.
    
    Attributes:
        output_dir: Directory where all output files will be saved
        log_dir: Directory for log files. If None, logs go to default location
        max_retries: Number of times to retry failed operations
        timeout: Maximum time in seconds to wait for operations
    """
    output_dir: Path
    log_dir: Optional[Path] = None
    max_retries: int = 3
    timeout: int = 300

@dataclass
class ProcessorConfig(BaseConfig):
    """Extended configuration for data processors with advanced features.
    
    Extends BaseConfig with settings for batch processing and caching.
    Used by all processor components (InterPro, FASTA, AlphaFold, PDB).
    
    Attributes:
        batch_size: Number of items to process in one batch for memory efficiency
        cache_enabled: Whether to cache results to avoid redundant processing
        cache_ttl: Time-to-live for cached items in seconds (default 24 hours)
        
    Inherits all attributes from BaseConfig.
    """
    batch_size: int = 100
    cache_enabled: bool = True
    cache_ttl: int = 86400  # 24 hours

@dataclass
class APIConfig:
    """Configuration for external API interactions.
    
    Manages settings for all external API communications including
    endpoints, timeouts, and retry policies.
    
    Attributes:
        interpro_api_url: Base URL for InterPro API
        uniprot_api_url: Base URL for UniProt API
        alphafold_api_url: Base URL for AlphaFold API
        request_timeout: Timeout for individual API requests
        max_retries: Number of times to retry failed API calls
        retry_delay: Delay between retries in seconds
        batch_size: Number of items per API request
    """
    interpro_api_url: str = "https://www.ebi.ac.uk/interpro/api"
    uniprot_api_url: str = "https://rest.uniprot.org"
    alphafold_api_url: str = "https://alphafold.ebi.ac.uk/api"
    request_timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 5
    batch_size: int = 100

class ConfigManager:
    """Manages application configuration settings.
    
    This class handles loading, saving, and providing access to all
    configuration settings. It supports both file-based configuration
    and default values.
    
    Usage:
        config_manager = ConfigManager()
        processor_config = config_manager.get_processor_config()
        api_config = config_manager.get_api_config()
    """
    
    def __init__(self, config_file: Optional[Path] = None):
        """Initialize configuration manager.
        
        Args:
            config_file: Path to JSON configuration file.
                        If None, uses 'config.json' in current directory.
        """
        self.config_file = config_file or Path("config.json")
        self.config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self):
        """Load configuration from file or create default if file doesn't exist."""
        if self.config_file.exists():
            with open(self.config_file) as f:
                self.config = json.load(f)
        else:
            self.config = self._get_default_config()
            self._save_config()

    def _save_config(self):
        """Save current configuration to JSON file."""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values.
        
        Returns:
            Dictionary containing default configuration settings for all components.
        """
        return {
            'paths': {
                'output_dir': 'output',      # Default output directory
                'log_dir': 'logs',           # Default log directory
                'cache_dir': 'cache'         # Default cache directory
            },
            'api': {
                'interpro_api_url': "https://www.ebi.ac.uk/interpro/api",
                'uniprot_api_url': "https://rest.uniprot.org",
                'alphafold_api_url': "https://alphafold.ebi.ac.uk/api",
                'request_timeout': 30,        # API request timeout in seconds
                'max_retries': 3,            # Number of API retry attempts
                'retry_delay': 5,            # Delay between retries in seconds
                'batch_size': 100            # Items per API request
            },
            'processing': {
                'max_workers': os.cpu_count() or 1,  # Number of concurrent workers
                'batch_size': 100,                   # Processing batch size
                'cache_enabled': True,               # Enable result caching
                'cache_ttl': 86400                   # Cache timeout (24 hours)
            }
        }

    def get_base_config(self) -> BaseConfig:
        """Get basic configuration settings.
        
        Returns:
            BaseConfig instance with core settings.
        """
        return BaseConfig(
            output_dir=Path(self.config['paths']['output_dir']),
            log_dir=Path(self.config['paths']['log_dir']),
            max_retries=self.config['api']['max_retries'],
            timeout=self.config['api']['request_timeout']
        )

    def get_processor_config(self) -> ProcessorConfig:
        """Get processor-specific configuration.
        
        Returns:
            ProcessorConfig instance with all processor settings.
        """
        base_config = self.get_base_config()
        return ProcessorConfig(
            output_dir=base_config.output_dir,
            log_dir=base_config.log_dir,
            max_retries=base_config.max_retries,
            timeout=base_config.timeout,
            batch_size=self.config['processing']['batch_size'],
            cache_enabled=self.config['processing']['cache_enabled'],
            cache_ttl=self.config['processing']['cache_ttl']
        )

    def get_api_config(self) -> APIConfig:
        """Get API-specific configuration.
        
        Returns:
            APIConfig instance with all API-related settings.
        """
        return APIConfig(
            interpro_api_url=self.config['api']['interpro_api_url'],
            uniprot_api_url=self.config['api']['uniprot_api_url'],
            alphafold_api_url=self.config['api']['alphafold_api_url'],
            request_timeout=self.config['api']['request_timeout'],
            max_retries=self.config['api']['max_retries'],
            retry_delay=self.config['api']['retry_delay'],
            batch_size=self.config['api']['batch_size']
        )

    def update_config(self, updates: Dict[str, Any]):
        """Update configuration with new values.
        
        Args:
            updates: Dictionary containing section updates.
                    Format: {'section_name': {setting: value}}
        """
        for section, values in updates.items():
            if section in self.config:
                self.config[section].update(values)
        self._save_config()
