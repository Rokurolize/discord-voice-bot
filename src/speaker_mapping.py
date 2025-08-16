"""Speaker mapping between different TTS engines."""

from typing import Any

# Mapping table between VOICEVOX and AivisSpeech speakers
# Based on voice characteristics and style
SPEAKER_MAPPING = {
    "voicevox_to_aivis": {
        # ずんだもん variants
        3: 1512153250,  # ノーマル -> zunda_normal
        1: 1512153249,  # あまあま -> zunda_amai
        7: 1512153252,  # ツンツン -> zunda_tsun
        5: 1512153251,  # セクシー -> zunda_sexy
        22: 1512153253,  # ささやき -> zunda_whisper
        38: 1512153254,  # ヒソヒソ -> zunda_hisohiso
        75: 1512153250,  # ヘロヘロ -> zunda_normal (no direct match)
        76: 1512153250,  # なみだめ -> zunda_normal (no direct match)
    },
    "aivis_to_voicevox": {
        # Reverse mapping
        1512153250: 3,  # zunda_normal -> ノーマル
        1512153249: 1,  # zunda_amai -> あまあま
        1512153252: 7,  # zunda_tsun -> ツンツン
        1512153251: 5,  # zunda_sexy -> セクシー
        1512153253: 22,  # zunda_whisper -> ささやき
        1512153254: 38,  # zunda_hisohiso -> ヒソヒソ
        1512153248: 3,  # zunda_reading -> ノーマル (no direct match)
        # Other AIVIS speakers map to VOICEVOX ずんだもんノーマル as fallback
        888753760: 3,  # anneli_normal -> ずんだもんノーマル
        888753761: 3,  # anneli_normal2 -> ずんだもんノーマル
        888753762: 3,  # anneli_tension -> ずんだもんノーマル
        888753763: 3,  # anneli_calm -> ずんだもんノーマル
        888753764: 3,  # anneli_happy -> ずんだもんノーマル
        888753765: 3,  # anneli_angry -> ずんだもんノーマル
        1431611904: 3,  # まい -> ずんだもんノーマル
        604166016: 3,  # 中2 -> ずんだもんノーマル
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
            1: {"name": "ずんだもん（あまあま）", "character": "ずんだもん"},
            3: {"name": "ずんだもん（ノーマル）", "character": "ずんだもん"},
            5: {"name": "ずんだもん（セクシー）", "character": "ずんだもん"},
            7: {"name": "ずんだもん（ツンツン）", "character": "ずんだもん"},
            22: {"name": "ずんだもん（ささやき）", "character": "ずんだもん"},
            38: {"name": "ずんだもん（ヒソヒソ）", "character": "ずんだもん"},
            75: {"name": "ずんだもん（ヘロヘロ）", "character": "ずんだもん"},
            76: {"name": "ずんだもん（なみだめ）", "character": "ずんだもん"},
        },
        "aivis": {
            1512153248: {"name": "非公式ずんだもん（朗読）", "character": "ずんだもん"},
            1512153249: {"name": "非公式ずんだもん（あまあま）", "character": "ずんだもん"},
            1512153250: {"name": "非公式ずんだもん（ノーマル）", "character": "ずんだもん"},
            1512153251: {"name": "非公式ずんだもん（セクシー）", "character": "ずんだもん"},
            1512153252: {"name": "非公式ずんだもん（ツンツン）", "character": "ずんだもん"},
            1512153253: {"name": "非公式ずんだもん（ささやき）", "character": "ずんだもん"},
            1512153254: {"name": "非公式ずんだもん（ヒソヒソ）", "character": "ずんだもん"},
            888753760: {"name": "Anneli（ノーマル）", "character": "Anneli"},
            888753761: {"name": "Anneli（通常）", "character": "Anneli"},
            888753762: {"name": "Anneli（テンション高め）", "character": "Anneli"},
            888753763: {"name": "Anneli（落ち着き）", "character": "Anneli"},
            888753764: {"name": "Anneli（上機嫌）", "character": "Anneli"},
            888753765: {"name": "Anneli（怒り・悲しみ）", "character": "Anneli"},
            1431611904: {"name": "まい", "character": "まい"},
            604166016: {"name": "中2", "character": "中2"},
        },
    }

    engine_speakers = speaker_db.get(engine, {})
    return engine_speakers.get(
        speaker_id,
        {"name": f"Unknown ({speaker_id})", "character": "Unknown"},
    )
