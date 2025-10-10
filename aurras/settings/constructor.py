"""
Settings Constructor

This module provides a constructor-based approach to loading settings
from specific file paths with auto-creation of files from model defaults.

Integrates with the ModelRegistry to ensure proper model management.
"""

from pathlib import Path
from typing import Any, Dict, Generic, Type, TypeVar

import tomli
import tomli_w
from pydantic import BaseModel

from aurras.settings.models.base import Settings
from aurras.settings.registry import get_model_registry
from aurras.utils.path_manager import PATH_MANAGER
from aurras.utils.telelog_config import get_logger

logger = get_logger("aurras.core.settings.constructor")

T = TypeVar("T", bound=BaseModel)


class SettingsConstructor(Generic[T]):
    """
    Unified settings loader that acts as a proxy to the underlying model instance.

    It provides a consistent API for both core and plugin settings:
    - Loads settings from TOML files
    - Auto-creates files from model defaults if they don't exist
    - Proxies attribute access to the underlying Pydantic model instance
    - Provides additional methods like reload(), save(), and context manager support

    Usage with type-safe API:
        ## For core settings:
            SETTINGS = SettingsConstructor[Settings]("core", Settings)
            SETTINGS.maximum_volume  # IDE knows this is Settings type!

        ## For plugin settings:
            spotify = SettingsConstructor[SpotifySettings]("spotify", SpotifySettings)
            spotify.api_key  # IDE knows this is SpotifySettings type!

        ## Context manager for auto-save:
            with SettingsConstructor[Settings]("core") as settings:
                settings.maximum_volume = 150  # Auto-saved on exit
    """

    def __init__(self, plugin_name: str, model_class: Type[T]):
        """
        Initialize the settings constructor and load the settings.

        Automatically registers the model in the internal registry for tracking.

        Args:
            plugin_name: Name of the plugin (or "core" for core settings)
            model_class: Pydantic model class for the settings

        Raises:
            ValueError: If the settings file is invalid or model validation fails
        """
        # Use object.__setattr__ to bypass our custom __setattr__
        object.__setattr__(self, "_plugin_name", plugin_name)
        object.__setattr__(self, "_settings_path", self._resolve_path(plugin_name))
        object.__setattr__(self, "_model_class", model_class)
        object.__setattr__(self, "_model_instance", None)

        registry = get_model_registry()
        if plugin_name != "core":
            registry.register_plugin(plugin_name, model_class)
            logger.debug(
                f"Registered plugin model '{plugin_name}' in internal registry"
            )

        self._load_and_validate()

    def _resolve_path(self, plugin_name: str) -> Path:
        """
        Resolve the settings path for the given plugin.

        Args:
            plugin_name: Name of the plugin (or "core" for core settings)

        Returns:
            Path to the settings.toml file for the specified plugin
        """
        if plugin_name == "core":
            return PATH_MANAGER.settings_file.expanduser().resolve()
        else:
            return (
                (PATH_MANAGER.plugin_dir / plugin_name / "settings.toml")
                .expanduser()
                .resolve()
            )

    def _load_and_validate(self) -> None:
        """
        Load settings from file and create a validated model instance.

        This method:
        1. Loads or creates the settings TOML file
        2. Validates the data and creates a model instance

        Raises:
            ValueError: If file is invalid or model validation fails
        """
        with logger.track_component(f"load_settings_{self._plugin_name}"):
            if self.file_path.exists():
                with logger.profile("load_from_file"):
                    settings_data = self._load_from_file()
            else:
                with logger.profile("create_from_model"):
                    settings_data = self._create_from_model()

            try:
                with logger.profile("validate_settings"):
                    instance = self._model_class(**settings_data)
                object.__setattr__(self, "_model_instance", instance)
                logger.info(
                    f"Successfully loaded settings for '{self._plugin_name}' from {self.file_path}"
                )
            except Exception as e:
                logger.error(
                    f"Error creating settings instance for '{self._plugin_name}': {e}"
                )
                raise ValueError(
                    f"Failed to create settings instance for '{self._plugin_name}': {e}"
                )

    def _load_from_file(self) -> Dict[str, Any]:
        """
        Load settings data from an existing TOML file.

        Returns:
            Settings data dictionary

        Raises:
            ValueError: If file is invalid or cannot be read
        """
        if not self.file_path.is_file():
            raise ValueError(f"Settings path is not a file: '{self.file_path}'")

        try:
            with open(self.file_path, "rb") as f:
                data = tomli.load(f)

            if not data:
                raise ValueError(f"Settings file is empty: {self.file_path}")

            logger.debug(f"Loaded settings from {self.file_path}")
            return data

        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Error loading settings file {self.file_path}: {e}")

    def _create_from_model(self) -> Dict[str, Any]:
        """
        Create settings file from model defaults.

        Returns:
            Settings data dictionary (kebab-case for TOML)

        Raises:
            ValueError: If file creation fails
        """
        logger.info(
            f"Settings file does not exist, creating from defaults: {self.file_path}"
        )
        try:
            # Save to TOML with kebab-case keys (by_alias=True)
            settings_dict_for_toml = self._model_class().model_dump(by_alias=True)

            file_path_parent_dir = self.file_path.parent
            file_path_parent_dir.mkdir(parents=True, exist_ok=True)

            with open(self.file_path, "wb") as f:
                tomli_w.dump(settings_dict_for_toml, f)

            logger.info(f"Created settings file from model: {self.file_path}")

            # Return the data (Pydantic will accept it with either case)
            return settings_dict_for_toml

        except Exception as e:
            logger.error(f"Error creating settings file from model: {e}")
            raise ValueError(f"Failed to create settings from model: {e}")

    def reload(self) -> None:
        """
        Reload settings from the file and re-validate.

        Raises:
            ValueError: If reloading or validation fails
        """
        logger.info(
            f"Reloading settings for '{self._plugin_name}' from {self.file_path}"
        )
        self._load_and_validate()

    def model_dump(self) -> Dict[str, Any]:
        """
        Get the settings as a dictionary (delegates to the model instance).

        Returns:
            Dictionary containing all settings
        """
        return self._model_instance.model_dump()

    def model_dump_json(self, **kwargs) -> str:
        """
        Get the settings as a JSON string (delegates to the model instance).

        Args:
            **kwargs: Additional arguments to pass to model_dump_json

        Returns:
            JSON string containing all settings
        """
        return self._model_instance.model_dump_json(**kwargs)

    @property
    def _instance(self) -> T:
        """
        Access the underlying model instance directly.

        Returns:
            The Pydantic model instance with proper generic type
        """
        return self._model_instance

    @property
    def model(self) -> T:
        """
        Access the underlying model instance with full type information.

        This property provides better type inference than direct attribute access.

        Returns:
            The Pydantic model instance with proper generic type

        Example:
            settings = SettingsConstructor[Settings]("core")
            volume = settings.model.maximum_volume  # Full type safety!
        """
        return self._model_instance

    @property
    def file_path(self) -> Path:
        """
        Get the path to the settings file.

        Returns:
            Resolved path to the settings TOML file
        """
        return self._settings_path.expanduser().resolve()

    def __enter__(self) -> T:
        """
        Enter context manager - returns the model instance.

        Returns:
            The underlying Pydantic model instance

        Example:
            with SettingsConstructor[Settings]("core") as settings:
                settings.maximum_volume = 150
            # Auto-saved on exit!
        """
        return self._model_instance

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit context manager - automatically saves settings.

        Args:
            exc_type: Exception type if an error occurred
            exc_val: Exception value if an error occurred
            exc_tb: Exception traceback if an error occurred
        """
        # Only save if no exception occurred
        if exc_type is None:
            try:
                with logger.profile(f"save_settings_{self._plugin_name}"):
                    # Save with kebab-case keys for TOML
                    settings_dict = self._model_instance.model_dump(by_alias=True)

                    self.file_path.parent.mkdir(parents=True, exist_ok=True)

                    with open(self.file_path, "wb") as f:
                        tomli_w.dump(settings_dict, f)

                    logger.debug(
                        f"Auto-saved settings for '{self._plugin_name}' on context exit"
                    )
            except Exception as e:
                logger.error(
                    f"Error auto-saving settings for '{self._plugin_name}': {e}"
                )
                # Don't raise - let the context manager exit gracefully

    def __getattr__(self, name: str) -> Any:
        """
        Proxy attribute access to the underlying model instance.

        This allows the constructor to act like the model itself,
        providing direct access to all settings attributes.

        Args:
            name: Attribute name to access

        Returns:
            The attribute value from the model instance

        Raises:
            AttributeError: If attribute doesn't exist on the model
        """
        # Avoid recursion by checking if _model_instance exists
        if "_model_instance" in object.__getattribute__(self, "__dict__"):
            return getattr(self._model_instance, name)
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Proxy attribute setting to the underlying model instance.

        Private attributes (starting with _) are set on the constructor itself,
        while public attributes are set on the model instance.

        Args:
            name: Attribute name to set
            value: Value to set

        Raises:
            AttributeError: If trying to set an invalid attribute
        """
        # Private attributes go to the constructor itself
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        else:
            # Public attributes go to the model instance
            if "_model_instance" in object.__getattribute__(self, "__dict__"):
                setattr(self._model_instance, name, value)
            else:
                raise AttributeError(
                    f"Cannot set attribute '{name}' before model instance is initialized"
                )

    def __repr__(self) -> str:
        """String representation of the settings constructor."""
        return f"SettingsConstructor(plugin='{self._plugin_name}', path='{self.file_path}')"

    def __str__(self) -> str:
        """Human-readable string representation."""
        if self._model_instance:
            field_count = len(self._model_instance.model_fields)
            return f"Settings[{self._plugin_name}] ({field_count} fields)"
        return f"Settings[{self._plugin_name}] (not loaded)"


# Public API for core settings constructor with full type safety
core_settings_constructor = SettingsConstructor[Settings]("core", Settings)
