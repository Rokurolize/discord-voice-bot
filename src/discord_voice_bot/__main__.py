"""Main entry point for the discord-voice-bot package."""

import asyncio
import os
import signal
import sys
from pathlib import Path
from types import FrameType

# Set up logging before importing our modules
from loguru import logger

from .bot import run_bot
from .config import Config
from .health_monitor import HealthMonitor


class BotManager:
    """Manages bot lifecycle and graceful shutdown."""

    def __init__(self, config: Config | None = None) -> None:
        """Initialize bot manager.

        If no config is supplied, load from environment.
        """
        super().__init__()
        self.bot_task: asyncio.Task[None] | None = None
        self.shutdown_event = asyncio.Event()
        self.is_shutting_down = False
        self.health_monitor: HealthMonitor | None = None
        self.config = config or Config.from_env()

    def setup_logging(self) -> None:
        """Set up structured logging."""
        # Remove default logger
        logger.remove()

        # Check if terminal supports colors
        import os

        colorize = os.environ.get("NO_COLOR") is None and sys.stderr.isatty()

        logger.debug(f"Terminal color support: {colorize}")
        logger.debug(f"NO_COLOR env var: {os.environ.get('NO_COLOR', 'not set')}")

        # Get log level from environment variable directly to avoid early Config creation
        log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

        # Console logging with colors and formatting
        _ = logger.add(
            sys.stderr,
            level=log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>"
            if colorize
            else "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
            colorize=colorize,
            backtrace=True,
            diagnose=True,
        )

        # File logging if configured - get log file from environment variable directly
        log_file = os.environ.get("LOG_FILE", "discord_bot_error.log")
        if log_file and log_file != "discord_bot_error.log":  # Only if explicitly set
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            _ = logger.add(
                log_path,
                level=log_level,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
                rotation="10 MB",
                retention="1 week",
                compression="gz",
                backtrace=True,
                diagnose=True,
            )

            logger.info(f"File logging enabled: {log_path}")

    def setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""

        def signal_handler(signum: int, frame: FrameType | None) -> None:
            """Handle shutdown signals."""
            if self.is_shutting_down:
                logger.warning("Force shutdown requested")
                sys.exit(1)

            signal_names: dict[int, str] = {
                signal.SIGINT: "SIGINT (Ctrl+C)",
                signal.SIGTERM: "SIGTERM",
            }

            signal_name = signal_names.get(signum, f"Signal {signum}")
            logger.info(f"Received {signal_name}, starting graceful shutdown...")

            self.is_shutting_down = True
            self.shutdown_event.set()

        # Set up signal handlers
        _ = signal.signal(signal.SIGINT, signal_handler)
        _ = signal.signal(signal.SIGTERM, signal_handler)

        logger.info("Signal handlers set up for graceful shutdown")

    async def run(self) -> None:
        """Run the bot with proper lifecycle management."""
        logger.info("Starting Discord Voice TTS Bot...")

        try:
            # Log configuration summary
            logger.info(f"Target voice channel ID: {self.config.target_voice_channel_id}")
            logger.info(f"TTS Engine: {self.config.tts_engine.upper()}")
            logger.info(f"TTS API URL: {self.config.engines[self.config.tts_engine]['url']}")
            logger.info(f"Speaker: {self.config.tts_speaker} (ID: {self.config.engines[self.config.tts_engine]['speakers'][self.config.tts_speaker]})")
            logger.info(f"Command prefix: {self.config.command_prefix}")

            # Start bot
            self.bot_task = asyncio.create_task(run_bot(config=self.config))

            # Wait for bot to be ready, then initialize health monitor
            await asyncio.sleep(5)  # Give bot time to initialize and connect

            # Get the bot instance and initialize health monitor
            # The health monitor is already initialized in the bot's _on_ready method
            logger.info("🩺 Health monitoring system is active")

            # Wait for shutdown signal or bot completion
            done, pending = await asyncio.wait(
                [self.bot_task, asyncio.create_task(self.shutdown_event.wait())],
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Cancel remaining tasks
            for task in pending:
                _ = task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # If bot task completed, check for exceptions
            if self.bot_task in done:
                try:
                    _ = await self.bot_task
                except Exception as e:
                    logger.error(f"Bot task failed: {type(e).__name__} - {e!s}")
                    raise

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")

        except Exception as e:
            logger.error(f"Fatal error: {type(e).__name__} - {e!s}")
            raise

        finally:
            logger.info("Bot shutdown complete")

    async def health_check(self) -> bool:
        """Perform startup health checks."""
        logger.info("Performing startup health checks...")

        try:
            # Import TTS engine for health check
            from .tts_engine import get_tts_engine

            # Initialize TTS engine with config
            tts_engine = await get_tts_engine(self.config)

            # Check TTS API availability
            logger.info("Checking TTS API availability...")
            await tts_engine.start()

            is_available, error_detail = await tts_engine.check_api_availability()
            if not is_available:
                logger.error(f"TTS API health check failed: {error_detail}")
                # Get engine info from environment variables directly to avoid early Config creation
                engine_name = os.environ.get("TTS_ENGINE", "voicevox").upper()
                api_url = os.environ.get("VOICEVOX_URL", "http://localhost:50021")
                logger.error(f"Please ensure {engine_name} server is running at {api_url}")
                return False

            logger.info("TTS API health check passed")

            # Test TTS synthesis
            logger.info("Testing TTS synthesis...")
            test_audio = await tts_engine.synthesize_audio("Startup test")
            if not test_audio:
                logger.error("TTS synthesis test failed")
                return False

            logger.info("TTS synthesis test passed")

            await tts_engine.close()

        except ImportError as e:
            logger.error(f"Module import failed: {e!s}")
            return False

        except Exception as e:
            logger.error(f"Health check failed: {type(e).__name__} - {e!s}")
            return False

        logger.info("All health checks passed ✅")
        return True


async def main() -> None:
    """Main entry point."""
    config = Config.from_env()
    bot_manager = BotManager(config)

    # Set up logging
    bot_manager.setup_logging()

    # Set up signal handlers
    bot_manager.setup_signal_handlers()

    logger.info("Discord Voice TTS Bot starting up...")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {Path.cwd()}")

    try:
        # Perform health checks
        if not await bot_manager.health_check():
            logger.error("Startup health checks failed")
            sys.exit(1)

        # Run the bot
        await bot_manager.run()

    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")

    except RuntimeError as e:
        if "Voice connection failed during startup" in str(e):
            logger.error(f"Bot startup aborted due to voice connection failure: {e}")
            sys.exit(1)
        else:
            logger.error(f"Unexpected runtime error: {type(e).__name__} - {e!s}")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {type(e).__name__} - {e!s}")
        # Print full traceback to stderr for debugging
        import traceback

        logger.error("Full traceback:")
        for line in traceback.format_exc().splitlines():
            logger.error(line)
        sys.exit(1)

    logger.info("Goodbye! 👋")


def sync_main() -> None:
    """Synchronous wrapper for main."""
    try:
        if sys.platform == "win32":
            # Use ProactorEventLoop on Windows for better subprocess support
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        # Handle --help argument before running the bot
        if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
            print("Discord Voice TTS Bot")
            print("")
            print("A Discord bot that reads voice channel text messages using Zundamon voice.")
            print("")
            print("Usage:")
            print("  discord-voice-bot")
            print("  python -m discord_voice_bot")
            print("")
            print("Environment Variables:")
            print("  DISCORD_BOT_TOKEN     Discord bot token (required)")
            print("  TARGET_VOICE_CHANNEL_ID  Voice channel ID (default: 1350964414286921749)")
            print("  TTS_ENGINE            TTS engine (default: voicevox)")
            print("  TTS_SPEAKER           Voice speaker (default: normal)")
            print("  LOG_LEVEL             Logging level (default: INFO)")
            print("")
            print("For more information, see the README.md file.")
            sys.exit(0)

        asyncio.run(main())

    except KeyboardInterrupt:
        pass  # Handled in async main

    except Exception as e:
        print(f"Fatal error: {type(e).__name__} - {e!s}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    sync_main()
