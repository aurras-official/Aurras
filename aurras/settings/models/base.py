"""
Base Settings Model

This module defines the main Settings class that contains all application settings.
It provides a centralized Pydantic model for configuration management with proper
validation, type conversion, and serialization to/from TOML configuration files.
"""

from pydantic import BaseModel, Field, field_validator

from aurras.core.settings.models.appearance import AppearanceSettings
from aurras.core.settings.models.backup import BackupSettings
from aurras.core.settings.models.command import CommandSettings
from aurras.core.settings.models.events import EventSystemSettings
from aurras.core.settings.models.keyboard import KeyboardShortcuts
from aurras.core.settings.models.shorthand import ShortHandSettings
from aurras.core.settings.models.validators import validate_volume
from aurras.utils.path_manager import PATH_MANAGER


def to_kebab_case(field_name: str) -> str:
    """Convert snake_case to kebab-case for field aliases."""
    return field_name.replace("_", "-")


class Settings(BaseModel):
    # Playback settings
    maximum_volume: str = "130"
    default_volume: str = "100"

    # Download settings
    playlist_path: str = str(PATH_MANAGER.playlists_dir)
    download_path: str = str(PATH_MANAGER.downloaded_songs_dir)
    plugin_path: str = str(PATH_MANAGER.plugin_dir)
    download_format: str = "mp3"
    download_bitrate: str = "auto"
    maximum_retries: str = "3"

    # Recommendation settings
    enable_recommendations: str = "yes"
    maximum_recommendations: str = "3"

    # Command settings
    command: CommandSettings = Field(default_factory=CommandSettings)

    # Shorthand settings
    shorthand: ShortHandSettings = Field(default_factory=ShortHandSettings)

    # Keyboard shortcuts
    keyboard_shortcuts: KeyboardShortcuts = Field(default_factory=KeyboardShortcuts)

    # Appearance settings
    appearance_settings: AppearanceSettings = Field(default_factory=AppearanceSettings)

    # Backup settings
    backup: BackupSettings = Field(default_factory=BackupSettings)

    # Event system settings
    event_system: EventSystemSettings = Field(default_factory=EventSystemSettings)

    # Advanced settings
    command_palette_key: str = ">"
    options_menu_key: str = "?"
    log_level: str = "info"
    buffer_size_kb: str = "4096"
    enable_cache: str = "yes"
    cache_limit_mb: str = "1024"
    automatic_cache_clearing: str = "yes"
    cache_expiry_days: str = "30"

    model_config = {
        "populate_by_name": True,
        "alias_generator": to_kebab_case,
        "extra": "allow",
    }

    @field_validator("maximum_volume", "default_volume", mode="before")
    @classmethod
    def validate_volume_field(cls, v):
        """Validate volume settings are within acceptable range."""
        return validate_volume(v)


core_settings = Settings()
