"""Slash command handling for Discord Voice TTS Bot."""

# Compatibility layer - re-export old names
# Legacy alias retained for backward-compat imports in external code.
try:
    from .registry import SlashCommandRegistry as SlashCommandHandler
except Exception:  # pragma: no cover
    SlashCommandHandler = object  # fallback

__all__ = ["SlashCommandHandler"]
