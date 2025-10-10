"""
Settings Package

This module provides a unified settings API for both core and plugin settings
with full type safety using Python generics.

Usage:
    # Core settings - Read access
    from aurras.core.settings import SETTINGS
    print(SETTINGS.maximum_volume)  # Access like a normal object
    print(SETTINGS.download_path)

    # Core settings - Update with context manager (auto-save):
    from aurras.core.settings import SETTINGS

    with SETTINGS as settings:
        settings.maximum_volume = 150
        settings.download_path = "/music"
    # Auto-saved to TOML on exit!

    # Reload settings from disk:
    SETTINGS.reload()

    # Plugin settings:
    from aurras.core.settings import SettingsConstructor
    from my_plugin.models import PluginSettings

    plugin_settings_constructor = SettingsConstructor[PluginSettings]("my_plugin", PluginSettings)
    PLUGIN_SETTINGS = plugin_settings_constructor.model

    # Read
    print(PLUGIN_SETTINGS.api_key)

    # Update with context manager
    with PLUGIN_SETTINGS as settings:
        settings.api_key = "new_key"
    # Auto-saved!

Note:
    Always use the context manager pattern for updates to ensure changes are
    saved to TOML automatically. Direct attribute assignment without the
    context manager will modify the in-memory model but won't persist to disk.
"""

from aurras.settings.constructor import (
    SettingsConstructor,
    core_settings_constructor,
)
from aurras.utils.telelog_config import get_logger

logger = get_logger("aurras.core.settings")

# Core settings instance to use throughout the application
SETTINGS = core_settings_constructor.model
logger.debug_with(
    "Core SETTINGS instance initialized",
    {
        "settings_type": str(type(SETTINGS)),
        "settings_fields": str(list(SETTINGS.__pydantic_fields__.keys())),
    },
)

__all__ = [
    "SETTINGS",
    "SettingsConstructor",
]
