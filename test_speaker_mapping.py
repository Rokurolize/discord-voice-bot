#!/usr/bin/env python3
"""Test script for speaker mapping functionality."""

from src.config import config
from src.user_settings import user_settings

def main():
    print("=== Speaker Mapping Test ===")
    print(f"Current TTS Engine: {config.tts_engine}")
    print()
    
    # Show all user settings
    print("Current User Settings:")
    all_settings = user_settings.list_all_settings()
    for user_id, settings in all_settings.items():
        print(f"  User {user_id}:")
        print(f"    Speaker ID: {settings.get('speaker_id')}")
        print(f"    Speaker Name: {settings.get('speaker_name')}")
        print(f"    Engine: {settings.get('engine', 'unknown')}")
    print()
    
    # Test speaker mapping for each user
    print("Speaker Mapping Results:")
    for user_id in all_settings.keys():
        original_speaker = user_settings.settings.get(user_id, {}).get('speaker_id')
        original_engine = user_settings.settings.get(user_id, {}).get('engine', 'unknown')
        mapped_speaker = user_settings.get_user_speaker(user_id, config.tts_engine)
        speaker_name = user_settings.settings.get(user_id, {}).get('speaker_name', 'Unknown')
        
        if original_speaker != mapped_speaker:
            print(f"  User {user_id} ({speaker_name}):")
            print(f"    {original_engine} ID {original_speaker} → {config.tts_engine} ID {mapped_speaker}")
        else:
            print(f"  User {user_id} ({speaker_name}): No mapping needed (native {original_engine})")
    print()
    
    # Show statistics
    print("Statistics:")
    stats = user_settings.get_stats()
    print(f"  Total Users: {stats['total_users']}")
    print(f"  Engine Distribution: {stats['engine_distribution']}")
    print(f"  Speaker Distribution: {stats['speaker_distribution']}")
    print()
    
    # Show compatibility info
    print("Engine Compatibility Info:")
    compat_info = user_settings.get_engine_compatibility_info(config.tts_engine)
    print(f"  Current Engine: {compat_info['current_engine']}")
    print(f"  Native Compatible Users: {compat_info['total_compatible']}")
    print(f"  Mapped Users: {compat_info['total_mapped']}")
    
    if compat_info['mapped_users']:
        print("  Mapped User Details:")
        for user_info in compat_info['mapped_users']:
            print(f"    User {user_info['user_id']} ({user_info['speaker_name']}):")
            print(f"      {user_info['original_engine']} ID {user_info['original_speaker_id']} → {user_info['current_engine']} ID {user_info['mapped_speaker_id']}")

if __name__ == "__main__":
    main()