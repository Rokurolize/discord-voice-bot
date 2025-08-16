#!/usr/bin/env python3
"""Check current user settings and mapping."""

from src.config import config
from src.user_settings import user_settings

print("=== Current Settings Check ===\n")

print(f"Current TTS Engine: {config.tts_engine}")
print(f"Current API URL: {config.api_url}")

# Check your settings
your_user_id = "176716772664279040"
print(f"\nYour settings (user {your_user_id}):")

# Get raw settings
raw_settings = user_settings.get_user_settings(your_user_id)
print(f"Raw settings: {raw_settings}")

# Get speaker for current engine
current_engine_speaker = user_settings.get_user_speaker(your_user_id, config.tts_engine)
print(f"Speaker ID for {config.tts_engine}: {current_engine_speaker}")

# Check other user too
other_user_id = "729142264303059065"
print(f"\nOther user settings (user {other_user_id}):")
other_raw = user_settings.get_user_settings(other_user_id)
print(f"Raw settings: {other_raw}")
other_speaker = user_settings.get_user_speaker(other_user_id, config.tts_engine)
print(f"Speaker ID for {config.tts_engine}: {other_speaker}")

# Show all settings
print(f"\nAll current settings:")
all_settings = user_settings.list_all_settings()
for uid, settings in all_settings.items():
    print(f"  {uid}: {settings}")

print(f"\nCompatibility info for {config.tts_engine}:")
compat = user_settings.get_engine_compatibility_info(config.tts_engine)
print(f"Compatible users: {compat['total_compatible']}")
print(f"Mapped users: {compat['total_mapped']}")

if compat['mapped_users']:
    for user in compat['mapped_users']:
        print(f"  User {user['user_id']}: {user['original_engine']} ID {user['original_speaker_id']} -> {user['current_engine']} ID {user['mapped_speaker_id']}")