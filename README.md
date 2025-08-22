# Discord Voice TTS Bot

A Discord bot that reads voice channel text messages using Zundamon voice (VOICEVOX) or other TTS engines.

## Features

- 🎤 **Text-to-Speech**: Reads messages from voice channel text chat
- 🔊 **Zundamon Voice**: Uses Zundamon voice from VOICEVOX by default
- 🎭 **Multiple Speakers**: Support for various voice styles and engines
- 📋 **Message Queue**: Queues messages for orderly playback
- 🔄 **Auto-Reconnect**: Automatically reconnects if disconnected
- 🛡️ **Rate Limiting**: Prevents spam with configurable rate limits
- 📊 **Status Commands**: Bot status and queue management commands
- ⚡ **Slash Commands**: Modern Discord slash command interface with autocomplete
- 🔧 **Voice Management**: Advanced voice connection health checks and reconnection

## Requirements

### System Dependencies
- Python 3.11+
- FFmpeg (for audio processing)
- VOICEVOX or AivisSpeech TTS engine running locally

### TTS Engine Setup
1. Download and run [VOICEVOX](https://voicevox.hiroshiba.com/) on `http://localhost:50021`
2. Or use [AivisSpeech](https://aivoice.aivis-project.com/) on `http://127.0.0.1:10101`

## Installation

### Using uv (Recommended)
```bash
# Clone repository
git clone <repo-url>
cd discord-voice-bot

# Install dependencies
uv sync

# Run the bot (CLI)
uv run discord-voice-bot

# Or run as module
uv run python -m discord_voice_bot
```

### Using pip
```bash
# Clone repository
git clone <repo-url>
cd discord-voice-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install dependencies
pip install -e .

# Run the bot (CLI)
discord-voice-bot

# Or run as module
python -m discord_voice_bot
```

### Development Installation
```bash
# Install with development dependencies
uv sync --extra dev
# Or with pip
pip install -e ".[dev]"
```

## Configuration

1. **Create Bot Token**: Create a Discord application and bot at [Discord Developer Portal](https://discord.com/developers/applications)

2. **Configure Environment**: Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```

3. **Set Required Variables**:
   - `DISCORD_BOT_TOKEN`: Your Discord bot token
   - `TARGET_VOICE_CHANNEL_ID`: Target voice channel ID (default: 1350964414286921749)
   - `VOICE_CHANNEL_ID`: Legacy fallback for backward compatibility

## Usage

### Starting the Bot

#### CLI Command (Recommended)
```bash
# Using uv
uv run discord-voice-bot

# Using pip
discord-voice-bot
```

#### Module Execution
```bash
# Using uv
uv run python -m discord_voice_bot

# Using pip
python -m discord_voice_bot
```

#### Direct Script Execution (Legacy)
```bash
# Using uv
uv run python main.py

# Using pip
python main.py
```

### Bot Commands

#### Traditional Prefix Commands
- `!tts status` - Show bot status and statistics
- `!tts skip` - Skip current TTS playback
- `!tts clear` - Clear TTS message queue
- `!tts speakers` - List available TTS speakers
- `!tts test [message]` - Test TTS with custom message

#### Modern Slash Commands (Recommended)
- `/status` - Show bot status and statistics
- `/skip` - Skip current TTS playback
- `/clear` - Clear TTS message queue
- `/speakers` - List available TTS speakers
- `/test [text]` - Test TTS with custom message
- `/voice [speaker]` - Set or show personal voice preference with autocomplete
- `/voices` - List all available voices with details
- `/voicecheck` - Perform voice connection health check
- `/reconnect` - Manually attempt to reconnect to voice channel

### Bot Permissions Required
- Connect to Voice Channels
- Speak in Voice Channels  
- Read Messages
- Send Messages
- Use Slash Commands

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Discord API   │◄──►│  Discord Bot     │◄──►│  Message        │
│                 │    │  (bot.py)        │    │  Processor      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │                          │
                              ▼                          ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Voice         │◄──►│  Voice Handler   │◄──►│  TTS Engine     │
│   Channel       │    │  (Queue Manager) │    │  (VOICEVOX)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Development

### Code Quality
```bash
# Format code
uv run black src/discord_voice_bot tests

# Lint code
uv run ruff check src/discord_voice_bot tests

# Type checking
uv run mypy src/discord_voice_bot

# Run tests
uv run pytest
```

### Development Tasks
```bash
# Run all linting and type checking
uv run poe lint
uv run poe type-check

# Format code
uv run poe format

# Run tests
uv run poe test
```

## Configuration Options

See `.env.example` for all available configuration options including:
- TTS engine selection (VOICEVOX/AivisSpeech)
- Voice speaker selection
- Rate limiting settings
- Audio quality settings
- Logging configuration

## Troubleshooting

### Common Issues

1. **"TTS API not available"**
   - Ensure VOICEVOX/AivisSpeech is running
   - Check the API URL configuration
   - Verify firewall settings

2. **"Failed to connect to voice channel"**
   - Check bot permissions in Discord
   - Verify voice channel ID is correct
   - Ensure bot has joined the server

3. **"No audio playback"**
   - Check FFmpeg installation
   - Verify audio drivers (especially on WSL2)
   - Check Discord voice connection

### Debug Mode
Set `DEBUG=true` in `.env` for verbose logging.

## License

This project is licensed under the MIT License.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

## Acknowledgments

- [VOICEVOX](https://voicevox.hiroshiba.com/) for the TTS engine
- [discord.py](https://discordpy.readthedocs.io/) for Discord API integration
- Zundamon character for the voice