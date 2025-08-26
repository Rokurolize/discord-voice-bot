"""User-specific settings management for Discord Voice TTS Bot."""

import json
import os
from pathlib import Path
from threading import RLock
from typing import Any

from loguru import logger

from .speaker_mapping import DEFAULT_SPEAKERS, SPEAKER_MAPPING, detect_engine


class UserSettings:
    """Manages user-specific settings like voice preferences."""

    def __init__(self, settings_file: str | None = None) -> None:
        """Initialize user settings manager.

        Args:
            settings_file: Path to JSON file for persistent storage

        """
        super().__init__()
        if settings_file is None:
            if os.name == "nt":
                base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
            else:
                base = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))
            settings_file = str(base / "discord-voice-bot" / "user_settings.json")
        self.settings_file = Path(settings_file)
        self.settings: dict[str, dict[str, Any]] = {}
        self._lock = RLock()

        # Ensure directory exists
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing settings
        self._load_settings()

        # Initialize default users if this is first run
        self._initialize_defaults()

        logger.info(f"User settings initialized with {len(self.settings)} users")

    def _load_settings(self) -> None:
        """Load settings from JSON file."""
        with self._lock:
            if self.settings_file.exists():
                try:
                    with open(self.settings_file, encoding="utf-8") as f:
                        loaded_settings = json.load(f)
                    # Only update if file has changed
                    if loaded_settings != self.settings:
                        self.settings = loaded_settings
                        logger.debug(f"Reloaded settings for {len(self.settings)} users")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse settings file: {e}")
                    # Don't clear existing settings on parse error
                except Exception as e:
                    logger.error(f"Failed to load settings: {e}")
                    # Don't clear existing settings on load error
            else:
                logger.debug("No existing settings file, starting fresh")
                self.settings = {}

    def _save_settings(self) -> None:
        """Save settings to JSON file."""
        with self._lock:
            try:
                tmp_path = self.settings_file.with_suffix(self.settings_file.suffix + ".tmp")
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(self.settings, f, indent=2, ensure_ascii=False)
                # Atomic on POSIX and Windows
                os.replace(tmp_path, self.settings_file)
                logger.debug("Settings saved to file")
            except Exception as e:
                logger.error(f"Failed to save settings: {e}")

    def _initialize_defaults(self) -> None:
        """Initialize default user settings if not already set."""
        # Migrate existing settings to new format with engine info
        self._migrate_settings()

        # No hardcoded user-specific defaults anymore
        # All user settings are managed via:
        # 1. Discord commands: !tts voice <speaker>
        # 2. Direct editing of user_settings.json
        logger.info("User settings initialization complete")

    def _migrate_settings(self) -> None:
        """Migrate existing user settings to include engine information."""
        migrated = False
        with self._lock:
            for user_id, user_data in self.settings.items():
                if "engine" not in user_data:
                    speaker_id = user_data.get("speaker_id")
                    if speaker_id is not None:
                        try:
                            user_data["engine"] = detect_engine(int(speaker_id))
                            migrated = True
                            speaker_name = user_data.get("speaker_name", "Unknown")
                            logger.info(
                                f"Migrated user {user_id} settings: {speaker_name} -> engine: {user_data['engine']}"
                            )
                        except Exception as e:
                            logger.warning(f"Migration skipped for user {user_id}: invalid speaker_id {speaker_id} ({e})")
        if migrated:
            self._save_settings()
            logger.info("Settings migration completed")

    def get_user_speaker(self, user_id: str, current_engine: str | None = None) -> int | None:
        """Get speaker ID for a specific user, mapping to current engine if needed.

        Args:
            user_id: Discord user ID as string
            current_engine: Current TTS engine ('voicevox' or 'aivis')

        Returns:
            Speaker ID compatible with current engine, None if not set

        """
        # Reload settings from file to get latest changes
        self._load_settings()

        with self._lock:
            user_settings = self.settings.get(str(user_id))
            if not user_settings:
                return None
            speaker_id = user_settings.get("speaker_id")
            user_engine = user_settings.get("engine", "voicevox")  # Default to voicevox for old settings

        if not speaker_id:
            return None

        # If no current engine specified or engines match, return original
        if not current_engine or user_engine == current_engine:
            return speaker_id

        # Map speaker ID to current engine
        mapped_id = self._map_speaker_to_engine(speaker_id, user_engine, current_engine)
        if mapped_id != speaker_id:
            logger.info(f"Mapped user {user_id} speaker from {user_engine} ID {speaker_id} to {current_engine} ID {mapped_id}")

        return mapped_id

    def _map_speaker_to_engine(self, speaker_id: int, from_engine: str, to_engine: str) -> int:
        """Map speaker ID from one engine to another.

        Args:
            speaker_id: Original speaker ID
            from_engine: Source engine
            to_engine: Target engine

        Returns:
            Mapped speaker ID, or original if no mapping available

        """
        if from_engine == to_engine:
            return speaker_id

        mapping_key = f"{from_engine}_to_{to_engine}"
        mapping = SPEAKER_MAPPING.get(mapping_key, {})

        mapped_id = mapping.get(speaker_id)
        if mapped_id is not None:
            return mapped_id

        # No direct mapping found, use engine defaults from mapping module
        return DEFAULT_SPEAKERS.get(to_engine, speaker_id)

    def set_user_speaker(self, user_id: str, speaker_id: int, speaker_name: str = "", engine: str | None = None) -> bool:
        """Set speaker preference for a user.

        Args:
            user_id: Discord user ID as string
            speaker_id: TTS speaker ID
            speaker_name: Human-readable speaker name
            engine: TTS engine the speaker belongs to (auto-detected if None)

        Returns:
            True if successful

        """
        try:
            user_id = str(user_id)

            # Auto-detect/validate engine
            if engine is None:
                engine = detect_engine(speaker_id)
            else:
                engine = engine.lower()
                if engine not in ("voicevox", "aivis"):
                    logger.error(f"Invalid engine '{engine}' provided; expected 'voicevox' or 'aivis'")
                    return False

            with self._lock:
                self.settings[user_id] = {
                    "speaker_id": speaker_id,
                    "speaker_name": speaker_name,
                    "engine": engine,
                }
                self._save_settings()
            logger.info(f"Set speaker for user {user_id}: {speaker_name} ({speaker_id}) on {engine} engine")
            return True
        except Exception as e:
            logger.error(f"Failed to set user speaker: {e}")
            return False

    def remove_user_speaker(self, user_id: str) -> bool:
        """Remove speaker preference for a user.

        Args:
            user_id: Discord user ID as string

        Returns:
            True if removed, False if not found

        """
        user_id = str(user_id)
        with self._lock:
            if user_id in self.settings:
                del self.settings[user_id]
                self._save_settings()
                logger.info(f"Removed speaker preference for user {user_id}")
                return True
        return False

    def get_user_settings(self, user_id: str) -> dict[str, Any] | None:
        """Get all settings for a user.

        Args:
            user_id: Discord user ID as string

        Returns:
            User settings dict or None

        """
        # Reload to get latest settings
        self._load_settings()
        data = self.settings.get(str(user_id))
        return None if data is None else data.copy()

    def list_all_settings(self) -> dict[str, dict[str, Any]]:
        """Get all user settings.

        Returns:
            Dictionary of all user settings

        """
        # Reload to get latest settings
        self._load_settings()
        import copy
        return copy.deepcopy(self.settings)

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about user settings.

        Returns:
            Statistics dictionary

        """
        # Reload to get latest settings
        self._load_settings()
        speaker_counts: dict[str, int] = {}
        engine_counts: dict[str, int] = {}

        for user_data in self.settings.values():
            speaker_name = user_data.get("speaker_name", "Unknown")
            engine = user_data.get("engine", "unknown")

            speaker_counts[speaker_name] = speaker_counts.get(speaker_name, 0) + 1
            engine_counts[engine] = engine_counts.get(engine, 0) + 1

        return {
            "total_users": len(self.settings),
            "speaker_distribution": speaker_counts,
            "engine_distribution": engine_counts,
        }

    def get_engine_compatibility_info(self, current_engine: str) -> dict[str, Any]:
        """Get information about engine compatibility for all users.

        Args:
            current_engine: Current TTS engine

        Returns:
            Dictionary with compatibility information

        """
        # Reload to get latest settings
        self._load_settings()
        compatible_users: list[dict[str, Any]] = []
        mapped_users: list[dict[str, Any]] = []

        for user_id, user_data in self.settings.items():
            user_engine = user_data.get("engine", "voicevox")
            speaker_id = user_data.get("speaker_id")
            speaker_name = user_data.get("speaker_name", "Unknown")

            if user_engine == current_engine:
                compatible_users.append(
                    {
                        "user_id": user_id,
                        "speaker_id": speaker_id,
                        "speaker_name": speaker_name,
                        "engine": user_engine,
                    }
                )
            else:
                if speaker_id is not None:
                    mapped_id = self._map_speaker_to_engine(speaker_id, user_engine, current_engine)
                    mapped_users.append(
                        {
                            "user_id": user_id,
                            "original_speaker_id": speaker_id,
                            "mapped_speaker_id": mapped_id,
                            "speaker_name": speaker_name,
                            "original_engine": user_engine,
                            "current_engine": current_engine,
                        }
                    )

        return {
            "current_engine": current_engine,
            "compatible_users": compatible_users,
            "mapped_users": mapped_users,
            "total_compatible": len(compatible_users),
            "total_mapped": len(mapped_users),
        }


def get_user_settings() -> UserSettings:
    """Create new user settings instance."""
    return UserSettings()
