"""Configuration management for iCloud Photo Downloader."""

import os
import yaml
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class Config:
    """Configuration manager for iCloud Photo Downloader."""
    
    def __init__(self, config_path: str = None):
        """Initialize configuration manager.
        
        Args:
            config_path: Path to custom config file. If None, use default config.
        """
        self.config: Dict[str, Any] = {}
        self.config_path = config_path
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        # Load default configuration
        default_config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'config',
            'default_config.yml'
        )
        
        try:
            with open(default_config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading default config: {e}")
            raise
        
        # Load custom configuration if provided
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    custom_config = yaml.safe_load(f)
                    # Update default config with custom settings
                    self._update_recursive(self.config, custom_config)
            except Exception as e:
                logger.error(f"Error loading custom config from {self.config_path}: {e}")
                raise
    
    def _update_recursive(self, base: Dict, update: Dict) -> None:
        """Recursively update a dictionary with another dictionary.
        
        Args:
            base: Base dictionary to update
            update: Dictionary with update values
        """
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._update_recursive(base[key], value)
            else:
                base[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key.
        
        Args:
            key: Configuration key (e.g., 'download.default_path')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        try:
            value = self.config
            for k in key.split('.'):
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value.
        
        Args:
            key: Configuration key (e.g., 'download.default_path')
            value: Value to set
        """
        keys = key.split('.')
        current = self.config
        for k in keys[:-1]:
            current = current.setdefault(k, {})
        current[keys[-1]] = value
    
    @property
    def download_path(self) -> str:
        """Get the configured download path."""
        path = self.get('download.default_path')
        return os.path.expanduser(path) if path else os.path.expanduser('~/Pictures/iCloud_Photos')