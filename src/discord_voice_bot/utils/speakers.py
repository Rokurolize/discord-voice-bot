def match_speaker(speakers_map: dict[str, int], user_input: str) -> tuple[str | None, int | None]:
    """Find a speaker by name (case-insensitive) or numeric ID.

    Args:
        speakers_map: Mapping of speaker name -> numeric ID from config/engine.
        user_input: Raw user-provided string (name or ID).

    Returns:
        (matched_name, matched_id) if found, otherwise (None, None).

    """
    sp = (user_input or "").strip()
    if not sp:
        return None, None

    sp_lower = sp.casefold()
    # Try exact name (case-insensitive) or exact numeric ID string
    for name, sid in speakers_map.items():
        if name.casefold() == sp_lower or str(sid) == sp:
            return name, sid

    # Fallback: prefix match (case-insensitive)
    for name, sid in speakers_map.items():
        if name.casefold().startswith(sp_lower):
            return name, sid

    return None, None
