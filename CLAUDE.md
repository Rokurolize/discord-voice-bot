# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**Essential Commands (use these exact commands):**
- `uv run poe format` - Format code (BLACK + RUFF) - ONLY allowed formatting command
- `uv run poe type-check` - Run mypy type checking - ONLY allowed type checking command
- `uv run poe test` - Run tests
- `uv run poe lint` - Check code style without fixing

**Always run format, type-check, and test before completing any task.**

## Project Overview

Discord Voice TTS Bot that reads voice channel text messages using Zundamon voice via VOICEVOX or AivisSpeech engines. The bot maintains a persistent connection to a specific voice channel and synthesizes text-to-speech for all messages posted in that channel's text chat.

### Key Features
- Real-time text-to-speech synthesis
- Discord API compliance (Voice Gateway v8, E2EE, rate limiting)
- Parallel audio processing for gap-free playback
- Comprehensive health monitoring and error recovery
- Multi-engine TTS support (VOICEVOX, AivisSpeech)
- User-specific voice preferences

## Critical Configuration

**Token Location**: `/home/ubuntu/.config/discord-voice-bot/secrets.env`
- Uses `DISCORD_BOT_TOKEN` (not `DISCORD_TOKEN`)
- Target voice channel ID: 1350964414286921749

## Architecture & Key Design Decisions

### Module Responsibilities

1. **main.py**: Entry point with signal handling, health checks, and graceful shutdown
   - Performs TTS API health check before starting bot
   - Sets up structured logging with loguru

2. **src/bot.py**: Discord client and command handler
   - Commands: `!tts status`, `!tts skip`, `!tts clear`, `!tts speakers`, `!tts test`
   - Manages bot lifecycle and monitoring tasks
   - Coordinates between voice handler and message processor

3. **src/voice_handler.py**: Voice connection and audio queue management
   - Dual-queue system: synthesis queue for pre-processing, audio queue for playback
   - Parallel TTS synthesis while audio is playing (eliminates gaps)
   - Smart message chunking for long messages (500 char chunks at sentence boundaries)
   - Message group tracking for complete skip functionality

4. **src/tts_engine.py**: TTS synthesis with VOICEVOX/AivisSpeech
   - **CRITICAL**: Do NOT modify `pitchScale` - AivisSpeech uses 0.0 for natural voice
   - Creates Discord-compatible audio (48kHz, stereo)
   - Uses temporary files with FFmpegPCMAudio

5. **src/message_processor.py**: Message filtering and text processing
   - Rate limiting per user (100 messages/60 seconds default)
   - Filters bot messages, commands, and system messages
   - Converts Discord markup to Japanese TTS-friendly text
   - Message chunking for long text (splits at 。！？… boundaries)

6. **src/config.py**: Environment variable management
   - Loads from `/home/ubuntu/.config/discord-voice-bot/secrets.env` first
   - Falls back to local `.env` if present
   - Validates configuration on startup

### Audio Pipeline

```
Text Message → Message Processor → Chunking (if needed) →
Synthesis Queue → Parallel TTS Synthesis → Audio Queue →
FFmpegPCMAudio → Discord Voice Client → Voice Channel
```

### Key Implementation Improvements

**Parallel TTS Synthesis**:
- Synthesis happens in background while current audio plays
- Pre-synthesizes up to 3 chunks ahead
- Eliminates gaps between messages
- Separate synthesis and playback tasks run concurrently

**Smart Message Chunking**:
- Long messages split into 500-character chunks
- Splits at sentence boundaries (。！？…\n)
- Each message gets unique group ID for coordinated skip
- No message length limit (was 200, now 10000+)

**Enhanced Skip Command**:
- Skips all chunks of current message group
- Clears from both synthesis and audio queues
- Properly cleans up pre-synthesized audio

## TTS Engine Specifics

### VOICEVOX
- Default URL: `http://localhost:50021`
- Zundamon speaker IDs: normal=3, sexy=5, tsun=7, amai=1
- Supports: speedScale, volumeScale, outputSamplingRate

### AivisSpeech
- Default URL: `http://127.0.0.1:10101`
- Zundamon speaker IDs: normal=1512153250, sexy=1512153251, tsun=1512153252
- **CRITICAL**: Returns `pitchScale=0.0` which must NOT be modified

## Environment Variables

Required in `/home/ubuntu/.config/discord-voice-bot/secrets.env`:
- `DISCORD_BOT_TOKEN`: Bot authentication token

Configurable in `.env`:
- `TTS_ENGINE`: voicevox or aivis (default: aivis)
- `TTS_SPEAKER`: Voice style selection
- `MAX_MESSAGE_LENGTH`: Maximum message length (default: 10000)
- `DEBUG`: Enable debug logging and audio saving

## Development Environment

- Project uses Python 3.11 with `uv` for dependency management
- Strict typing with mypy, formatted with black (140 char) + ruff
- Configuration: `pyproject.toml` with hatchling build system
- Virtual environment: `./venv/` with all dependencies

## Running the Bot

```bash
# Direct execution
source venv/bin/activate
python main.py

# Check health before starting
python -c "from src.tts_engine import tts_engine; import asyncio; asyncio.run(tts_engine.health_check())"
```

## Debugging Audio Issues

```bash
# Audio debugger saves files to /tmp/discord_tts_debug/
# Enable with DEBUG=true environment variable
ls -la /tmp/discord_tts_debug/session_*/

# Test TTS synthesis directly
python minimal_api_test.py

# Test voice connection
python test_voice_connection.py
```

## Testing Strategy

- Unit tests in `tests/` directory with pytest
- Integration tests as standalone scripts
- Test parallel synthesis: `test_parallel_synthesis.py`
- All tests use asyncio for Discord API compatibility

## Working with the Codebase

- Always use type hints (Python 3.11 union syntax: `str | None`)
- Follow existing code patterns and imports
- Never assume library availability - check imports first
- Use loguru for all logging
- Handle asyncio cancellation properly
- Clean up resources (temp files, sessions) on shutdown

## Specialized Agent Integration

When working on specific aspects of the project, reference the appropriate specialized agent:

- **Discord Bot Issues** → Discord Bot Specialist
- **TTS Engine Problems** → TTS Engine Specialist
- **Audio Processing** → Audio Processing Specialist
- **Testing & TDD** → Testing Specialist
- **Configuration** → Configuration Specialist
- **Monitoring & Debugging** → Monitoring Specialist

Each agent provides detailed guidance, best practices, and critical requirements for their domain.
