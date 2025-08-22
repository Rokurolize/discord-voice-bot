"""Slash command handling for Discord Voice TTS Bot."""

# Compatibility layer - re-export old names
from .registry import SlashCommandRegistry as SlashCommandHandler

__all__ = ["SlashCommandHandler"]
