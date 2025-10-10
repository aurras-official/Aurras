"""
Settings Updater

This module provides functionality for updating specific settings using dot notation
with automatic save via context manager pattern.

Supports both core and plugin settings through the unified SettingsConstructor API.
"""

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from aurras.settings.constructor import SettingsConstructor


class SettingsValidationError(Exception):
    """Raised when trying to update an invalid settings key."""

    pass


class SettingsModifier:
    """
    Update specific settings using dot notation with auto-save via context manager.

    This class simplifies updating nested settings by:
    - Supporting both core and plugin settings
    - Supporting both kebab-case and snake_case key names
    - Validating that keys exist before updating
    - Using context manager for automatic TOML save

    Works with any SettingsConstructor (core or plugin).
    """

    def __init__(
        self, key_to_update: str, constructor: Optional["SettingsConstructor"] = None
    ) -> None:
        """
        Initialize the updater for a specific setting key.

        Args:
            key_to_update: Dot-separated key path (supports kebab-case or snake_case)
                          Example: "maximum-volume" or "event_system.enable_throttling"
            constructor: SettingsConstructor to use (core or plugin).
                        If None, uses core settings constructor for backward compatibility.
        """
        if constructor is None:
            from aurras.settings.constructor import core_settings_constructor

            constructor = core_settings_constructor

        self.constructor = constructor

        # Convert kebab-case to snake_case (Pydantic uses snake_case internally)
        self.key = self._kebab_to_snake_case(key_to_update)
        self.current_value = self._get_nested_value(self.constructor, self.key)
        self._verify_key_not_none()

        self.new_value = None

    def _kebab_to_snake_case(self, query: str) -> str:
        return query.replace("-", "_")

    def _verify_key_not_none(self) -> None:
        """Validate that the key exists in the settings model."""
        if self.current_value is None:
            raise SettingsValidationError(
                f"Setting key '{self.key.replace('_', '-')}' does not exist."
            )

    def _get_nested_value(
        self, constructor: SettingsConstructor, dotted_key: str
    ) -> Any:
        """
        Get a nested value from a Pydantic model using dot notation.

        Args:
            model: Pydantic model instance
            dotted_key: Dot-separated path (e.g., "event_system.enable_throttling")

        Returns:
            The value at the specified path, or None if not found
        """
        parts = dotted_key.split(".")
        model = constructor.model
        for part in parts:
            if hasattr(model, part):
                model = getattr(model, part)
            else:
                return None
        return model

    def _set_nested_value(
        self, constructor: SettingsConstructor, dotted_key: str, value: Any
    ) -> None:
        """
        Set a nested value in a Pydantic model using dot notation.

        Args:
            model: Pydantic model instance to update
            dotted_key: Dot-separated path (e.g., "event_system.enable_throttling")
            value: New value to set

        Raises:
            AttributeError: If the path doesn't exist in the model
        """
        parts = dotted_key.split(".")
        model = constructor.model

        for part in parts[:-1]:
            if hasattr(model, part):
                model = getattr(model, part)
            else:
                raise AttributeError(
                    f"Cannot find attribute '{part}' in path '{dotted_key}'"
                )

        final_key = parts[-1]
        if not hasattr(model, final_key):
            raise AttributeError(
                f"Cannot find attribute '{final_key}' in path '{dotted_key}'"
            )

        setattr(model, final_key, value)

    def _apply_update(self) -> None:
        """
        Apply the update and auto-save using context manager.

        This uses the context manager pattern to ensure settings are
        automatically saved to TOML on successful update.
        """
        with self.constructor as settings:
            self._set_nested_value(settings, self.key, self.new_value)

    def update_value(self, value: str) -> None:
        """
        Set the new value of the setting.

        Args:
            value: New value to set

        Uses context manager for automatic save to TOML.
        """
        self.new_value = value
        self._apply_update()
