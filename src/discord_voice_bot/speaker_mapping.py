"""Speaker mapping between different TTS engines."""

from typing import Any

# Mapping table between VOICEVOX and AivisSpeech speakers
# Based on voice characteristics and style
SPEAKER_MAPPING = {
    "voicevox_to_aivis": {
        # Zundamon variants
        3: 1512153250,  # Normal -> zunda_normal
        1: 1512153249,  # Sweet -> zunda_amai
        7: 1512153252,  # Tsundere -> zunda_tsun
        5: 1512153251,  # Seductive -> zunda_sexy
        22: 1512153253,  # Whisper -> zunda_whisper
        38: 1512153254,  # Murmur -> zunda_hisohiso
        75: 1512153250,  # Flirty -> zunda_normal (no direct match)
        76: 1512153250,  # Tearful -> zunda_normal (no direct match)
    },
    "aivis_to_voicevox": {
        # Reverse mapping
        1512153250: 3,  # zunda_normal -> Normal
        1512153249: 1,  # zunda_amai -> Sweet
        1512153252: 7,  # zunda_tsun -> Tsundere
        1512153251: 5,  # zunda_sexy -> Seductive
        1512153253: 22,  # zunda_whisper -> Whisper
        1512153254: 38,  # zunda_hisohiso -> Murmur
        1512153248: 3,  # zunda_reading -> Normal (no direct match)
        # Other AIVIS speakers map to VOICEVOX Zundamon Normal as fallback
        888753760: 3,  # anneli_normal -> Zundamon Normal
        888753761: 3,  # anneli_normal2 -> Zundamon Normal
        888753762: 3,  # anneli_tension -> Zundamon Normal
        888753763: 3,  # anneli_calm -> Zundamon Normal
        888753764: 3,  # anneli_happy -> Zundamon Normal
        888753765: 3,  # anneli_angry -> Zundamon Normal
        1431611904: 3,  # Mai -> Zundamon Normal
        604166016: 3,  # Chuunibyou -> Zundamon Normal
    },
}


def get_compatible_speaker(speaker_id: int, from_engine: str, to_engine: str, engine_configs: dict[str, dict[str, Any]]) -> int | None:
    """Get compatible speaker ID for different engine.

    Args:
        speaker_id: Original speaker ID
        from_engine: Source engine name (voicevox or aivis)
        to_engine: Target engine name (voicevox or aivis)
        engine_configs: Engine configuration dictionary from config

    Returns:
        Compatible speaker ID for target engine, or None if same engine

    """
    # If same engine, no mapping needed
    if from_engine == to_engine:
        return speaker_id

    # Get mapping key
    mapping_key = f"{from_engine}_to_{to_engine}"

    # Check if mapping exists
    if mapping_key in SPEAKER_MAPPING:
        mapping = SPEAKER_MAPPING[mapping_key]
        # Return mapped speaker or default
        if speaker_id in mapping:
            return mapping[speaker_id]

    # Return default speaker for target engine
    return engine_configs.get(to_engine, {}).get("default_speaker")


def get_speaker_info(speaker_id: int, engine: str) -> dict[str, Any]:
    """Get speaker information for given ID and engine.

    Args:
        speaker_id: Speaker ID
        engine: Engine name (voicevox or aivis)

    Returns:
        Speaker information dict with name and engine

    """
    # Speaker information database
    speaker_db = {
        "voicevox": {
            1: {"name": "Zundamon (Sweet)", "character": "Zundamon"},
            3: {"name": "Zundamon (Normal)", "character": "Zundamon"},
            5: {"name": "Zundamon (Seductive)", "character": "Zundamon"},
            7: {"name": "Zundamon (Tsundere)", "character": "Zundamon"},
            22: {"name": "Zundamon (Whisper)", "character": "Zundamon"},
            38: {"name": "Zundamon (Murmur)", "character": "Zundamon"},
            75: {"name": "Zundamon (Flirty)", "character": "Zundamon"},
            76: {"name": "Zundamon (Tearful)", "character": "Zundamon"},
        },
        "aivis": {
            1512153248: {"name": "Unofficial Zundamon (Reading)", "character": "Zundamon"},
            1512153249: {"name": "Unofficial Zundamon (Sweet)", "character": "Zundamon"},
            1512153250: {"name": "Unofficial Zundamon (Normal)", "character": "Zundamon"},
            1512153251: {"name": "Unofficial Zundamon (Seductive)", "character": "Zundamon"},
            1512153252: {"name": "Unofficial Zundamon (Tsundere)", "character": "Zundamon"},
            1512153253: {"name": "Unofficial Zundamon (Whisper)", "character": "Zundamon"},
            1512153254: {"name": "Unofficial Zundamon (Murmur)", "character": "Zundamon"},
            888753760: {"name": "Anneli (Normal)", "character": "Anneli"},
            888753761: {"name": "Anneli (Standard)", "character": "Anneli"},
            888753762: {"name": "Anneli (High Tension)", "character": "Anneli"},
            888753763: {"name": "Anneli (Calm)", "character": "Anneli"},
            888753764: {"name": "Anneli (Happy)", "character": "Anneli"},
            888753765: {"name": "Anneli (Angry/Sad)", "character": "Anneli"},
            1431611904: {"name": "Mai", "character": "Mai"},
            604166016: {"name": "Chuunibyou", "character": "Chuunibyou"},
        },
    }

    engine_speakers = speaker_db.get(engine, {})
    return engine_speakers.get(
        speaker_id,
        {"name": f"Unknown ({speaker_id})", "character": "Unknown"},
    )
