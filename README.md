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

## Requirements

### System Dependencies
- Python 3.8+
- FFmpeg (for audio processing)
- VOICEVOX or AivisSpeech TTS engine running locally

### TTS Engine Setup
1. Download and run [VOICEVOX](https://voicevox.hiroshiba.com/) on `http://localhost:50021`
2. Or use [AivisSpeech](https://aivoice.aivis-project.com/) on `http://127.0.0.1:10101`

## Installation

### Using Poetry (Recommended)
```bash
# Clone repository
git clone <repo-url>
cd discord-voice-bot

# Install dependencies
poetry install

# Run the bot
poetry run python main.py
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
pip install -r requirements.txt

# Run the bot
python main.py
```

## Configuration

1. **Create Bot Token**: Create a Discord application and bot at [Discord Developer Portal](https://discord.com/developers/applications)

2. **Configure Environment**: Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```

3. **Set Required Variables**:
   - `DISCORD_TOKEN`: Your Discord bot token
   - `VOICE_CHANNEL_ID`: Target voice channel ID (default: 1350964414286921749)

## Usage

### Starting the Bot
```bash
# With Poetry
poetry run python main.py

# With pip
python main.py
```

### Bot Commands
- `!tts status` - Show bot status and statistics
- `!tts skip` - Skip current TTS playback
- `!tts clear` - Clear TTS message queue
- `!tts speakers` - List available TTS speakers
- `!tts test [message]` - Test TTS with custom message

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
poetry run black .

# Lint code  
poetry run ruff check .

# Type checking
poetry run mypy .

# Run tests
poetry run pytest
```

### Pre-commit Hooks
```bash
poetry run pre-commit install
poetry run pre-commit run --all-files
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