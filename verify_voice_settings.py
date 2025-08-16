#!/usr/bin/env python3
"""Verify current voice settings for all users."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from user_settings import user_settings
from config import config

def main():
    """Verify voice settings."""
    print("=== Current Voice Settings ===")
    
    # Get all user settings
    all_settings = user_settings.list_all_settings()
    
    for user_id, settings in all_settings.items():
        speaker_id = settings['speaker_id']
        speaker_name = settings['speaker_name']
        print(f"User {user_id}: {speaker_name} (ID: {speaker_id})")
        
        # Check if this is mimi
        if user_id == "729142264303059065":
            print(f"  ↳ 🎯 This is MIMI's setting")
            if speaker_id == 1512153249:
                print(f"  ↳ ✅ Correctly set to zunda_amai!")
            else:
                print(f"  ↳ ❌ Wrong speaker ID, should be 1512153249")
    
    print("\n=== Available zunda voices ===")
    aivis_speakers = config.engines["aivis"]["speakers"]
    for name, speaker_id in aivis_speakers.items():
        if "zunda" in name:
            print(f"  {name}: {speaker_id}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())