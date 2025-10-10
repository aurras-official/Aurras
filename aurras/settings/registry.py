"""
Model Registry

This module provides a centralized registry for managing both core and plugin
settings models with strong typing for core and flexibility for plugins.
"""

from typing import Any, Dict, Optional, Type, TypeVar, Union

from pydantic import BaseModel

from aurras.settings.models.base import Settings, core_settings
from aurras.utils.telelog_config import get_logger

logger = get_logger("aurras.core.settings.registry")

T = TypeVar("T", bound=BaseModel)


class ModelRegistry:
    """
    Centralized registry for settings models.

    Provides strong typing for core Settings while maintaining flexibility
    for dynamically registered plugin models.
    """

    def __init__(self) -> None:
        """Initialize the model registry with core settings."""
        self._core_model: Type[Settings] = type(core_settings)
        self._plugin_models: Dict[str, Type[BaseModel]] = {}

    def get_core(self) -> Type[Settings]:
        """
        Always return the core Settings model (strongly typed).

        Returns:
            Core Settings model class with full type support
        """
        return self._core_model

    def register_plugin(self, name: str, model: Type[BaseModel]) -> None:
        """
        Register a plugin's settings model class dynamically.

        Args:
            name: Plugin name (used as identifier)
            model: Pydantic model class for the plugin's settings

        # Raises:
        #     ValueError: If plugin name is already registered
        """
        if name in self._plugin_models:
            logger.warning(f"Plugin model '{name}' already registered, overwriting")

        self._plugin_models[name] = model
        logger.info(f"Registered plugin model: {name} -> {model.__name__}")

    def unregister_plugin(self, name: str) -> bool:
        """
        Unregister a plugin's settings model.

        Args:
            name: Plugin name to unregister

        Returns:
            True if plugin was found and removed, False otherwise
        """
        if name in self._plugin_models:
            del self._plugin_models[name]
            logger.info(f"Unregistered plugin model: {name}")
            return True
        else:
            logger.debug(f"Plugin model '{name}' not found for unregistration")
            return False

    def get_plugin(self, name: str) -> Optional[Type[BaseModel]]:
        """
        Fetch a plugin's settings model class (dynamic).

        Args:
            name: Plugin name

        Returns:
            Plugin's BaseModel class or None if not found
        """
        model = self._plugin_models.get(name)
        if model is None:
            logger.debug_with(
                "Plugin model '{name}' not found in registry",
                {
                    "requested_plugin": name,
                    "available_plugins": str(list(self._plugin_models.keys())),
                },
            )
        else:
            logger.debug_with(
                "Retrieved plugin model '{name}'",
                {"plugin_name": name, "model_class": model.__name__},
            )
        return model

    def get_any(
        self, name: Optional[str] = None
    ) -> Optional[Union[Type[Settings], Type[BaseModel]]]:
        """
        Unified accessor for both core and plugin models.

        Args:
            name: Plugin name. If None, returns core Settings model

        Returns:
            Core Settings model if name is None, plugin model otherwise
        """
        if name is None:
            return self._core_model
        return self._plugin_models.get(name)

    def list_plugins(self) -> list[str]:
        """
        Get list of all registered plugin names.

        Returns:
            List of registered plugin names
        """
        plugins = list(self._plugin_models.keys())
        logger.debug_with(
            "Registry contains {count} plugin(s)",
            {"count": str(len(plugins)), "plugins": str(plugins)},
        )
        return plugins

    def has_plugin(self, name: str) -> bool:
        """
        Check if a plugin model is registered.

        Args:
            name: Plugin name to check

        Returns:
            True if plugin is registered, False otherwise
        """
        exists = name in self._plugin_models
        logger.debug_with(
            "Plugin '{name}' {status} in registry",
            {"plugin_name": name, "status": "found" if exists else "not found"},
        )
        return exists

    def create_plugin_instance(self, name: str, **kwargs) -> Optional[BaseModel]:
        """
        Create an instance of a plugin's settings model.

        Args:
            name: Plugin name
            **kwargs: Keyword arguments to pass to the model constructor

        Returns:
            Plugin settings instance or None if plugin not found
        """
        with logger.track_component("create_plugin_instance"):
            model_class = self._plugin_models.get(name)
            if model_class is None:
                logger.error(f"Cannot create instance: plugin '{name}' not registered")
                logger.debug_with(
                    "Instance creation failed: plugin '{name}' not found",
                    {
                        "requested_plugin": name,
                        "available_plugins": str(list(self._plugin_models.keys())),
                    },
                )
                return None

            try:
                with logger.profile(f"instantiate_plugin_{name}"):
                    instance = model_class(**kwargs)
                logger.debug_with(
                    "Created instance for plugin '{name}'",
                    {
                        "plugin_name": name,
                        "model_class": model_class.__name__,
                        "kwargs_keys": str(list(kwargs.keys())),
                    },
                )
                return instance
            except Exception as e:
                logger.error(f"Error creating instance for plugin '{name}': {e}")
                logger.debug_with(
                    "Instance creation error for plugin '{name}': {error}",
                    {
                        "plugin_name": name,
                        "error_type": type(e).__name__,
                        "kwargs": str(kwargs),
                        "error": str(e),
                    },
                )
                return None

    def validate_plugin_data(
        self, name: str, data: Dict[str, Any]
    ) -> Optional[BaseModel]:
        """
        Validate data against a plugin's model and return validated instance.

        Args:
            name: Plugin name
            data: Data dictionary to validate

        Returns:
            Validated plugin settings instance or None if validation fails
        """
        with logger.track_component("validate_plugin_data"):
            model_class = self._plugin_models.get(name)
            if model_class is None:
                logger.error(f"Cannot validate: plugin '{name}' not registered")
                logger.debug_with(
                    "Validation failed: plugin '{name}' not found",
                    {
                        "requested_plugin": name,
                        "available_plugins": str(list(self._plugin_models.keys())),
                    },
                )
                return None

            try:
                with logger.profile(f"validate_plugin_{name}"):
                    validated = model_class.model_validate(data)
                logger.debug_with(
                    "Validated data for plugin '{name}'",
                    {
                        "plugin_name": name,
                        "model_class": model_class.__name__,
                        "data_keys": str(list(data.keys())),
                    },
                )
                return validated
            except Exception as e:
                logger.error(f"Validation failed for plugin '{name}': {e}")
                logger.debug_with(
                    "Validation error details",
                    {
                        "plugin_name": name,
                        "error_type": type(e).__name__,
                        "data": str(data),
                    },
                )
                return None

    def get_model_info(self, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get information about a model (core or plugin).

        Args:
            name: Plugin name, or None for core model

        Returns:
            Dictionary with model information
        """
        if name is None:
            model = self._core_model
            model_type = "core"
        else:
            model = self._plugin_models.get(name)
            model_type = "plugin"

        if model is None:
            logger.debug_with(
                "Model info not found for '{name}'",
                {
                    "requested_model": str(name),
                    "available_plugins": str(list(self._plugin_models.keys())),
                },
            )
            return {"error": f"Model '{name}' not found"}

        info = {
            "name": name or "core",
            "type": model_type,
            "class_name": model.__name__,
            "module": model.__module__,
            "fields": list(model.model_fields.keys())
            if hasattr(model, "model_fields")
            else [],
        }

        logger.debug_with(
            "Retrieved model info for '{name or 'core'}'",
            {
                "name": str(name or "core"),
                "type": model_type,
                "class_name": model.__name__,
                "field_count": str(len(info["fields"])),
            },
        )

        return info

    def clear_plugins(self) -> None:
        """Clear all registered plugin models."""
        count = len(self._plugin_models)
        plugins_before = list(self._plugin_models.keys())

        logger.debug_with(
            "Clearing {count} plugin(s) from registry",
            {"plugins_to_clear": str(plugins_before), "count": str(count)},
        )

        self._plugin_models.clear()
        logger.info(f"Cleared {count} plugin models from registry")

    def __len__(self) -> int:
        """Return total number of registered models (core + plugins)."""
        return 1 + len(self._plugin_models)  # 1 for core + plugins

    def __contains__(self, name: str) -> bool:
        """Check if a model is registered (supports 'in' operator)."""
        return name == "core" or name in self._plugin_models

    def __repr__(self) -> str:
        """String representation of the registry."""
        plugin_count = len(self._plugin_models)
        return f"ModelRegistry(core=Settings, plugins={plugin_count})"


# Global model registry instance
_model_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    """
    Get the global model registry instance.

    Returns:
        Global ModelRegistry instance
    """
    global _model_registry
    if _model_registry is None:
        _model_registry = ModelRegistry()
    return _model_registry


def register_plugin_model(name: str, model: Type[BaseModel]) -> None:
    """
    Convenience function to register a plugin model.

    Args:
        name: Plugin name
        model: Plugin's Pydantic model class
    """
    registry = get_model_registry()
    registry.register_plugin(name, model)


def get_core_model() -> Type[Settings]:
    """
    Convenience function to get the core Settings model.

    Returns:
        Core Settings model class
    """
    registry = get_model_registry()
    return registry.get_core()


def get_plugin_model(name: str) -> Optional[Type[BaseModel]]:
    """
    Convenience function to get a plugin model.

    Args:
        name: Plugin name

    Returns:
        Plugin's BaseModel class or None if not found
    """
    registry = get_model_registry()
    return registry.get_plugin(name)
