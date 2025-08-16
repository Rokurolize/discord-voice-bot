#!/usr/bin/env python3
"""Migrate user settings to include engine information."""

import json
from pathlib import Path

from loguru import logger

# Enable detailed logging
logger.remove()
logger.add(lambda msg: print(msg, end=""), level="DEBUG", colorize=True)


def migrate_settings():
    """Migrate user settings to include engine information."""
    settings_file = Path("/home/ubuntu/.config/discord-voice-bot/user_settings.json")
    
    print(f"\n=== Settings Migration ===")
    print(f"Settings file: {settings_file}")
    
    if not settings_file.exists():
        print("No settings file found, nothing to migrate")
        return
    
    # Load current settings
    with open(settings_file, "r", encoding="utf-8") as f:
        settings = json.load(f)
    
    print(f"\nCurrent settings:")
    print(json.dumps(settings, indent=2, ensure_ascii=False))
    
    # Migrate each user's settings
    migrated = False
    for user_id, user_data in settings.items():
        if "engine" not in user_data:
            speaker_id = user_data.get("speaker_id")
            if speaker_id:
                # Determine engine based on speaker_id
                if speaker_id < 100:  # VOICEVOX IDs are typically < 100
                    user_data["engine"] = "voicevox"
                else:
                    user_data["engine"] = "aivis"
                
                migrated = True
                print(f"\nMigrated user {user_id}:")
                print(f"  Speaker: {user_data['speaker_name']} (ID: {speaker_id})")
                print(f"  Engine: {user_data['engine']}")
    
    if migrated:
        # Save updated settings
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Migration complete! Settings saved.")
        print(f"\nUpdated settings:")
        print(json.dumps(settings, indent=2, ensure_ascii=False))
    else:
        print(f"\n✅ All settings already have engine information.")


if __name__ == "__main__":
    migrate_settings()