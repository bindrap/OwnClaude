"""Configuration management for PBOS AI."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, validator


class OllamaLocalConfig(BaseModel):
    """Local Ollama configuration."""
    host: str = "http://localhost:11434"
    model: str = "llama3.2"
    temperature: float = 0.7
    top_p: float = 0.9
    timeout: int = 300  # Increased from 90 to 300 seconds (5 minutes)


class OllamaCloudConfig(BaseModel):
    """Cloud Ollama configuration."""
    api_key: str
    endpoint: str = "https://cloud.ollama.ai"
    model: str = "llama3.2"
    temperature: float = 0.7
    top_p: float = 0.9
    timeout: int = 300  # Increased from 120 to 300 seconds (5 minutes)


class OllamaConfig(BaseModel):
    """Ollama configuration container."""
    local: OllamaLocalConfig
    cloud: OllamaCloudConfig


class ConfirmationSettings(BaseModel):
    """Confirmation requirements for operations."""
    file_deletion: bool = True
    app_closure: bool = False
    system_commands: bool = True
    file_modification: bool = False


class SystemPermissions(BaseModel):
    """System permissions configuration."""
    allow_app_control: bool = True
    allow_file_operations: bool = True
    allow_browser_control: bool = True
    allow_system_commands: bool = False
    require_confirmation: ConfirmationSettings


class InterfaceConfig(BaseModel):
    """Interface configuration."""
    theme: str = "dark"
    show_timestamps: bool = True
    show_token_usage: bool = False
    auto_save_history: bool = True
    history_limit: int = 1000
    ask_destination: bool = False


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    file: str = "logs/ownclaude.log"
    max_size_mb: int = 10
    backup_count: int = 5
    log_operations: bool = True


class SecurityConfig(BaseModel):
    """Security configuration."""
    enable_rollback: bool = True
    max_rollback_operations: int = 10
    sensitive_paths: list[str] = Field(default_factory=list)


class FeaturesConfig(BaseModel):
    """Features configuration."""
    enable_voice_input: bool = False
    enable_auto_completion: bool = True
    enable_context_awareness: bool = True
    enable_task_planning: bool = False  # Disabled by default for speed
    enable_code_analysis: bool = True
    enable_git_integration: bool = True
    max_context_messages: int = 10  # Reduced for faster responses
    project_scan_depth: int = 5
    code_search_max_results: int = 50


class ModelRoutingConfig(BaseModel):
    """Model routing configuration."""
    default_model: str = "qwen2.5:7b"
    models: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic config."""
        extra = "allow"


class Config(BaseModel):
    """Main configuration model."""
    model_type: str = "local"
    enable_model_routing: bool = False
    ollama: OllamaConfig
    model_routing: Optional[ModelRoutingConfig] = None
    system_permissions: SystemPermissions
    interface: InterfaceConfig
    logging: LoggingConfig
    security: SecurityConfig
    features: FeaturesConfig

    @validator("model_type")
    def validate_model_type(cls, v):
        """Validate model type."""
        if v not in ["local", "cloud"]:
            raise ValueError("model_type must be 'local' or 'cloud'")
        return v


class ConfigManager:
    """Manages application configuration."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration manager.

        Args:
            config_path: Path to config file. Defaults to config.json in project root.
        """
        self.config_path = config_path or Path("config.json")
        self._config: Optional[Config] = None

    def load(self) -> Config:
        """Load configuration from file.

        Returns:
            Loaded configuration.

        Raises:
            FileNotFoundError: If config file doesn't exist.
            ValueError: If config is invalid.
        """
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}\n"
                "Please copy config.example.json to config.json and configure it."
            )

        with open(self.config_path, 'r') as f:
            config_data = json.load(f)

        self._config = Config(**config_data)
        return self._config

    def get(self) -> Config:
        """Get current configuration.

        Returns:
            Current configuration.

        Raises:
            RuntimeError: If config hasn't been loaded.
        """
        if self._config is None:
            raise RuntimeError("Configuration not loaded. Call load() first.")
        return self._config

    def reload(self) -> Config:
        """Reload configuration from file.

        Returns:
            Reloaded configuration.
        """
        return self.load()

    def save(self, config: Config) -> None:
        """Save configuration to file.

        Args:
            config: Configuration to save.
        """
        with open(self.config_path, 'w') as f:
            json.dump(config.dict(), f, indent=2)
        self._config = config

    @staticmethod
    def create_default_config(output_path: Path) -> None:
        """Create a default configuration file.

        Args:
            output_path: Path where to create the config file.
        """
        default_config = {
            "model_type": "local",
            "ollama": {
                "local": {
                    "host": "http://localhost:11434",
                    "model": "llama3.2",
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "timeout": 300
                },
                "cloud": {
                    "api_key": "your-api-key-here",
                    "endpoint": "https://cloud.ollama.ai",
                    "model": "llama3.2",
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "timeout": 300
                }
            },
            "system_permissions": {
                "allow_app_control": True,
                "allow_file_operations": True,
                "allow_browser_control": True,
                "allow_system_commands": False,
                "require_confirmation": {
                    "file_deletion": True,
                    "app_closure": False,
                    "system_commands": True,
                    "file_modification": False
                }
            },
            "interface": {
                "theme": "dark",
                "show_timestamps": True,
                "show_token_usage": False,
                "auto_save_history": True,
                "history_limit": 1000,
                "ask_destination": True
            },
            "logging": {
                "level": "INFO",
                "file": "logs/ownclaude.log",
                "max_size_mb": 10,
                "backup_count": 5,
                "log_operations": True
            },
            "security": {
                "enable_rollback": True,
                "max_rollback_operations": 10,
                "sensitive_paths": [
                    "/etc",
                    "/sys",
                    "/boot",
                    "C:\\Windows",
                    "C:\\Program Files"
                ]
            },
            "features": {
                "enable_voice_input": False,
                "enable_auto_completion": True,
                "enable_context_awareness": True,
                "max_context_messages": 20
            }
        }

        with open(output_path, 'w') as f:
            json.dump(default_config, f, indent=2)
