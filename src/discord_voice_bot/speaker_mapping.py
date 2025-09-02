"""Speaker mapping between different TTS engines."""

from types import MappingProxyType
from typing import Any, Literal

# Narrow engine names used across the module
Engine = Literal["aivis", "voicevox"]

_AIVIS_ID_MIN = 100_000

_V2A_BASE: dict[int, int] = {
    # Zundamon variants
    3: 1512153250,  # Normal -> zunda_normal
    1: 1512153249,  # Sweet -> zunda_amai
    7: 1512153252,  # Tsundere -> zunda_tsun
    5: 1512153251,  # Seductive -> zunda_sexy
    22: 1512153253,  # Whisper -> zunda_whisper
    38: 1512153254,  # Murmur -> zunda_hisohiso
    75: 1512153250,  # Flirty -> zunda_normal (no direct match)
    76: 1512153250,  # Tearful -> zunda_normal (no direct match)
}

# Auto-generated reverse mapping from base
_A2V_AUTO: dict[int, int] = {v: k for k, v in _V2A_BASE.items()}

# Explicit reverse overrides and fallbacks not representable by inversion
_A2V_EX: dict[int, int] = {
    # Canonical reverse for Zundamon Normal; avoid auto-inversion collision picking 75/76
    1512153250: 3,
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
}

SPEAKER_MAPPING = MappingProxyType(
    {
        "voicevox_to_aivis": MappingProxyType(_V2A_BASE),
        "aivis_to_voicevox": MappingProxyType({**_A2V_AUTO, **_A2V_EX}),
    }
)

# Centralized defaults per engine
DEFAULT_SPEAKERS = MappingProxyType(
    {
        "voicevox": 3,  # Zundamon (Normal)
        "aivis": 1512153250,  # Unofficial Zundamon (Normal)
    }
)


def detect_engine(speaker_id: int) -> Engine:
    """
    Return the TTS engine corresponding to a speaker ID.

    Determines whether a numeric speaker_id belongs to "aivis" (IDs >= 100000) or "voicevox" (IDs < 100000). Centralizes the heuristic so the threshold can be changed in one place.

    Args:
        speaker_id: Numeric speaker identifier.

    Returns:
        Engine: "aivis" or "voicevox".

    """
    return "aivis" if speaker_id >= _AIVIS_ID_MIN else "voicevox"


def get_compatible_speaker(
    speaker_id: int,
    from_engine: Engine,
    to_engine: Engine,
    engine_configs: dict[str, dict[str, Any]] | None = None,
) -> int | None:
    """
    Return a speaker ID on the target TTS engine that is compatible with the given source speaker.

    If from_engine == to_engine, returns the original speaker_id. Otherwise attempts to map via the shared SPEAKER_MAPPING; if no mapping exists, returns a default speaker for the target engine — preferring engine_configs[to_engine]["default_speaker"] when provided, then the module-wide DEFAULT_SPEAKERS. Returns None if no default is available.

    Args:
        speaker_id: Source engine speaker identifier.
        from_engine: Source engine ("voicevox" or "aivis").
        to_engine: Target engine ("voicevox" or "aivis").
        engine_configs: Optional per-engine configuration dict; used to read an explicit "default_speaker" for the target engine.

    Returns:
        int | None: Speaker ID valid for the target engine, or None if no compatible ID or default is available.

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

    # Return default speaker for target engine (prefer explicit config default if provided)
    raw_default = (engine_configs or {}).get(to_engine, {}).get("default_speaker")
    try:
        specified_default = int(raw_default) if raw_default is not None else None
    except (TypeError, ValueError):
        specified_default = None
    return specified_default if specified_default is not None else DEFAULT_SPEAKERS.get(to_engine)


# Read-only speaker information database
SPEAKER_DB = MappingProxyType(
    {
        "voicevox": MappingProxyType(
            {
                1: {"name": "Zundamon (Sweet)", "character": "Zundamon"},
                3: {"name": "Zundamon (Normal)", "character": "Zundamon"},
                5: {"name": "Zundamon (Seductive)", "character": "Zundamon"},
                7: {"name": "Zundamon (Tsundere)", "character": "Zundamon"},
                22: {"name": "Zundamon (Whisper)", "character": "Zundamon"},
                38: {"name": "Zundamon (Murmur)", "character": "Zundamon"},
                75: {"name": "Zundamon (Flirty)", "character": "Zundamon"},
                76: {"name": "Zundamon (Tearful)", "character": "Zundamon"},
            }
        ),
        "aivis": MappingProxyType(
            {
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
            }
        ),
    }
)


def get_speaker_info(speaker_id: int, engine: Engine) -> dict[str, Any]:
    """
    Return speaker metadata for the given speaker ID and engine.

    If the ID is not present in the engine's speaker database, returns a fallback
    dictionary with "name" set to "Unknown (<id>)" and "character" set to "Unknown".

    Args:
        speaker_id: Numeric speaker identifier.
        engine: "voicevox" or "aivis".

    Returns:
        dict[str, Any]: Speaker info with at least the keys "name" and "character".

    """
    speaker_db = SPEAKER_DB

    engine_speakers = speaker_db.get(engine, {})
    return engine_speakers.get(
        speaker_id,
        {"name": f"Unknown ({speaker_id})", "character": "Unknown"},
    )
