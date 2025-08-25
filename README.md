# Discord Voice Bot

A Discord voice channel text-to-speech bot with Zundamon voice.

## Setup

### 1. Discord Bot Creation

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give your bot a name
3. Go to the "Bot" section in the left sidebar
4. Click "Reset Token" to generate a new bot token
5. **IMPORTANT**: Enable the following under "Privileged Gateway Intents":
   - ✅ Message Content Intent (required to read message content)

### 2. Bot Permissions

In the "Bot" section, ensure the following permissions are enabled:
- ✅ Send Messages
- ✅ Use Slash Commands
- ✅ Connect
- ✅ Speak
- ✅ Use Voice Activity

### 3. Invite Bot to Server

1. In Discord Developer Portal, go to "OAuth2" → "URL Generator"
2. Select scopes: `bot`
3. Select permissions:
   - Send Messages
   - Use Slash Commands
   - Connect
   - Speak
   - Use Voice Activity
4. Use the generated URL to invite the bot to your server

### 4. Environment Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and set your configuration:
   ```env
   # Discord Bot Configuration
   DISCORD_BOT_TOKEN=your_bot_token_here
   TARGET_GUILD_ID=your_server_id
   TARGET_VOICE_CHANNEL_ID=your_voice_channel_id

   # TTS Configuration
   TTS_ENGINE=voicevox
   TTS_SPEAKER=normal

   # Optional: Test mode (skips Discord connection)
   TEST_MODE=false
   ```

### 5. TTS Engine Setup

The bot supports multiple TTS engines:

#### VoiceVOX (Default)
- Download from: https://voicevox.hiroshiba.jp/
- Run on default port (50021)

#### AivisSpeech
- Download from: https://aivspeech.com/
- Run on port 10101 (or configure AIVIS_URL)

## Usage

### Production Mode
```bash
uv run discord-voice-bot
```

### Test Mode (No Discord Connection)
```bash
TEST_MODE=true uv run discord-voice-bot
```

## Development

```bash
# Run tests
uv run pytest

# Run linting
uv run poe lint

# Format code
uv run poe format

# Type checking
uv run poe type-check

# Full check pipeline
uv run poe check
```

## Configuration System

The bot uses a dependency injection pattern for configuration:

- `ConfigManagerImpl()` - Main configuration manager
- `ConfigManagerImpl(test_mode=True)` - Forces test mode
- Environment variables override `.env` file settings
- Configuration is validated on startup

## Requirements

- Python 3.12
- Discord.py
- Various other dependencies (see pyproject.toml)
- VoiceVOX or AivisSpeech TTS engine
