# Discord Voice TTS Bot - Deployment Guide

## Quick Start

1. **Install Dependencies**
   ```bash
   uv sync
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Start TTS Engines**
   ```bash
   # Start VOICEVOX (default port 50021)
   # Start AIVIS Speech (default port 10101)
   ```

4. **Run the Bot**
   ```bash
   uv run discord-voice-bot
   ```

## Configuration

### Required Environment Variables
- `DISCORD_BOT_TOKEN`: Your Discord bot token
- `TARGET_VOICE_CHANNEL_ID`: Voice channel ID for TTS
- `TTS_ENGINE`: "voicevox" or "aivis"
- `VOICEVOX_URL`: VOICEVOX API URL (default: http://localhost:50021)
- `AIVIS_URL`: AIVIS Speech API URL (default: http://127.0.0.1:10101)

### Optional Settings
- `ENABLE_SELF_MESSAGE_PROCESSING`: Allow bot to read its own messages
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR
- `MAX_MESSAGE_LENGTH`: Maximum message length to process

## Features

✅ **Working Features:**
- Text-to-speech conversion using VOICEVOX or AIVIS engines
- Automatic voice channel connection
- Message processing pipeline
- Slash command support (/voice, /skip, /status, etc.)
- Health monitoring and error recovery
- User voice preferences
- Rate limiting and queue management

## Testing

Run the included test scripts to verify functionality:

```bash
# Test TTS engines
python test_tts_engines.py

# Test slash commands
python test_slash_commands.py

# Test message pipeline
python test_message_pipeline.py

# Test bot startup
python test_bot_startup.py
```

## Troubleshooting

- Ensure TTS engines are running and accessible
- Check Discord bot permissions (voice, message content intent)
- Verify voice channel exists and bot has access
- Check logs for detailed error information
