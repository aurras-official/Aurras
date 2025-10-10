"""
Event System Settings Model

Core event system configuration with default fallback values.
Plugins define their own event optimization in their settings.
"""

from pydantic import BaseModel, Field


class EventSystemSettings(BaseModel):
    """
    Core event system configuration.

    Provides:
    - Default fallback values for event optimization
    - System configuration (queue size, timeouts)

    Individual event optimization is defined by plugins in their own settings.
    """

    # ========================================================================
    # DEFAULT OPTIMIZATION VALUES (Fallbacks when plugin doesn't specify)
    # ========================================================================

    default_throttle_interval: float = Field(
        default=0.0,
        ge=0.0,
        description="Default throttle interval in seconds (0 = no throttling)",
    )

    default_sample_rate: int = Field(
        default=1,
        ge=1,
        description="Default sample rate (1 = emit all, 5 = emit every 5th)",
    )

    default_state_threshold: float = Field(
        default=0.0,
        ge=0.0,
        description="Default threshold for numeric value changes (0 = any change)",
    )

    # ========================================================================
    # SYSTEM SETTINGS (Internal configuration)
    # ========================================================================

    max_queue_size: int = Field(
        default=10000,
        ge=1,
        description="Maximum number of events in the queue",
    )

    worker_timeout: float = Field(
        default=1.0,
        ge=0.1,
        description="Event worker poll timeout in seconds",
    )

    error_handler_timeout: float = Field(
        default=5.0,
        ge=0.1,
        description="Timeout for error handler execution in seconds",
    )

    max_handler_execution_time: float = Field(
        default=30.0,
        ge=0.1,
        description="Maximum time for event handler execution (seconds)",
    )
