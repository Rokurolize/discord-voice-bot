"""Protocol definitions for Discord Voice TTS Bot components."""

from typing import Any, Protocol


class ConfigManager(Protocol):
    """Protocol for configuration management to avoid circular imports."""

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        ...

    def get_api_url(self) -> str:
        """Get TTS API URL."""
        ...

    def get_speaker_id(self) -> int:
        """Get default speaker ID."""
        ...

    def get_tts_engine(self) -> str:
        """Get TTS engine name."""
        ...

    def get_audio_sample_rate(self) -> int:
        """Get audio sample rate."""
        ...

    def get_audio_channels(self) -> int:
        """Get audio channels."""
        ...

    def get_log_level(self) -> str:
        """Get logging level."""
        ...

    def validate(self) -> None:
        """Validate configuration."""
        ...

    def get_discord_token(self) -> str:
        """Get Discord bot token."""
        ...

    def get_target_guild_id(self) -> int:
        """Get target guild ID."""
        ...

    def get_target_voice_channel_id(self) -> int:
        """Get target voice channel ID."""
        ...

    def get_command_prefix(self) -> str:
        """Get command prefix."""
        ...

    def get_engine_config(self) -> dict[str, Any]:
        """Get current TTS engine configuration."""
        ...

    def get_engines(self) -> dict[str, dict[str, Any]]:
        """Get all engine configurations."""
        ...

    def get_max_message_length(self) -> int:
        """Get maximum message length."""
        ...

    def get_message_queue_size(self) -> int:
        """Get message queue size."""
        ...

    def get_reconnect_delay(self) -> int:
        """Get reconnect delay."""
        ...

    def get_rate_limit_messages(self) -> int:
        """Get rate limit messages."""
        ...

    def get_rate_limit_period(self) -> int:
        """Get rate limit period."""
        ...

    def get_log_file(self) -> str | None:
        """Get log file path."""
        ...

    def is_debug(self) -> bool:
        """Check if debug mode is enabled."""
        ...

    def get_intents(self) -> Any:
        """Get Discord intents."""
        ...

    def get_enable_self_message_processing(self) -> bool:
        """Check if self-message processing is enabled."""
        ...


class HasConfig(Protocol):
    """Protocol for objects that have configuration."""

    config: Any


class HasVoiceHandler(Protocol):
    """Protocol for objects that have voice handler."""

    voice_handler: Any


class HasHealthMonitor(Protocol):
    """Protocol for objects that have health monitor."""

    health_monitor: Any


class HasStatusManager(Protocol):
    """Protocol for objects that have status manager."""

    status_manager: Any


class HasEventHandler(Protocol):
    """Protocol for objects that have event handler."""

    event_handler: Any


class HasCommandHandler(Protocol):
    """Protocol for objects that have command handler."""

    command_handler: Any


class HasSlashHandler(Protocol):
    """Protocol for objects that have slash command handler."""

    slash_handler: Any


class HasMessageValidator(Protocol):
    """Protocol for objects that have message validator."""

    message_validator: Any


class HasConfigManager(Protocol):
    """Protocol for objects that have configuration manager."""

    config_manager: "ConfigManager"


# DiscordVoiceBotTTS protocol removed - using structural subtyping instead
# Classes with the required attributes will be compatible automatically


class DiscordBotClient(Protocol):
    """Protocol for Discord bot client interface required by HealthMonitor."""

    @property
    def guilds(self) -> Any:
        """List of guilds the bot is in."""
        ...

    def get_channel(self, channel_id: int) -> Any:
        """Get a channel by ID."""
        ...

    def is_closed(self) -> bool:
        """Check if the client is closed."""
        ...

    async def close(self) -> None:
        """Close the client connection."""
        ...

    # Optional attributes for voice handler access
    def __getattr__(self, name: str) -> Any:
        """Allow dynamic attribute access for optional components."""
        ...


class StatsLike(Protocol):
    """Minimal stats mapping used by StartupManager."""

    def __getitem__(self, key: str) -> Any: ...
    def __setitem__(self, key: str, value: Any) -> None: ...
    def get(self, key: str, default: Any = ...) -> Any: ...


class StartupBot(Protocol):
    """Protocol capturing the attributes StartupManager needs to access on the bot."""

    user: Any | None
    tree: Any
    guilds: Any
    stats: StatsLike
    startup_complete: bool
    startup_connection_failures: int
    monitor_task: Any | None

    async def change_presence(self, *, status: Any, activity: Any) -> None: ...
    def get_channel(self, channel_id: int) -> Any: ...
    # Optional components accessed defensively at runtime
    def __getattr__(self, name: str) -> Any: ...
