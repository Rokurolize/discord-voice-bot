#!/usr/bin/env python3
"""Comprehensive Discord voice protocol debugging."""

import asyncio
import json
from datetime import datetime

import discord

from src.audio_debugger import audio_debugger
from src.config import config


class VoiceProtocolDebugger:
    """Step-by-step voice protocol debugger."""

    def __init__(self):
        self.debug_log = []
        self.client = None
        self.voice_client = None

    def log_step(self, step: str, status: str, details: dict = None):
        """Log a debugging step."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "status": status,
            "details": details or {},
        }
        self.debug_log.append(entry)

        # Color-coded output
        color = "✅" if status == "SUCCESS" else "❌" if status == "FAILED" else "🔄"
        print(f"{color} [{step}] {status}")
        if details:
            for key, value in details.items():
                print(f"   {key}: {value}")

    async def debug_voice_protocol(self):
        """Debug entire voice protocol step by step."""
        print("🔍 === COMPREHENSIVE DISCORD VOICE PROTOCOL DEBUG ===\\n")

        try:
            # Step 1: Basic Discord Connection
            await self.test_discord_connection()

            # Step 2: Voice Channel Discovery
            await self.test_voice_channel_discovery()

            # Step 3: Voice Connection (with timeout)
            await self.test_voice_connection()

            # Step 4: Voice WebSocket Analysis
            if self.voice_client:
                await self.test_voice_websocket()

                # Step 5: Speaking Protocol
                await self.test_speaking_protocol()

                # Step 6: Audio Transmission Test
                await self.test_audio_transmission()

                # Cleanup
                await self.voice_client.disconnect()

        except Exception as e:
            self.log_step("OVERALL_TEST", "FAILED", {"error": f"{type(e).__name__}: {e!s}"})

        finally:
            if self.client and not self.client.is_closed():
                await self.client.close()

            # Generate debug report
            self.generate_debug_report()

    async def test_discord_connection(self):
        """Test basic Discord connection."""
        try:
            intents = discord.Intents.default()
            intents.message_content = True
            self.client = discord.Client(intents=intents)

            connection_complete = asyncio.Event()
            connection_error = None

            @self.client.event
            async def on_ready():
                nonlocal connection_error
                try:
                    self.log_step(
                        "DISCORD_CONNECTION",
                        "SUCCESS",
                        {
                            "bot_name": str(self.client.user),
                            "bot_id": self.client.user.id,
                            "guild_count": len(self.client.guilds),
                        },
                    )
                    connection_complete.set()
                except Exception as e:
                    connection_error = e
                    connection_complete.set()

            # Start connection with timeout
            connection_task = asyncio.create_task(self.client.start(config.discord_token))

            try:
                await asyncio.wait_for(connection_complete.wait(), timeout=15)
                if connection_error:
                    raise connection_error
            except TimeoutError:
                self.log_step("DISCORD_CONNECTION", "TIMEOUT", {"timeout_seconds": 15})
                connection_task.cancel()
                return False

        except Exception as e:
            self.log_step(
                "DISCORD_CONNECTION",
                "FAILED",
                {"error": f"{type(e).__name__}: {e!s}"},
            )
            return False

        return True

    async def test_voice_channel_discovery(self):
        """Test voice channel discovery."""
        try:
            channel = self.client.get_channel(config.target_voice_channel_id)
            if not channel:
                self.log_step(
                    "VOICE_CHANNEL_DISCOVERY",
                    "FAILED",
                    {
                        "channel_id": config.target_voice_channel_id,
                        "error": "Channel not found",
                    },
                )
                return False

            self.log_step(
                "VOICE_CHANNEL_DISCOVERY",
                "SUCCESS",
                {
                    "channel_name": channel.name,
                    "channel_type": type(channel).__name__,
                    "guild_name": channel.guild.name,
                    "member_count": (len(channel.members) if hasattr(channel, "members") else "N/A"),
                },
            )

            self.target_channel = channel
            return True

        except Exception as e:
            self.log_step(
                "VOICE_CHANNEL_DISCOVERY",
                "FAILED",
                {"error": f"{type(e).__name__}: {e!s}"},
            )
            return False

    async def test_voice_connection(self):
        """Test voice connection with detailed monitoring."""
        if not hasattr(self, "target_channel"):
            self.log_step("VOICE_CONNECTION", "SKIPPED", {"reason": "No target channel available"})
            return False

        try:
            self.log_step("VOICE_CONNECTION", "STARTING", {"channel": self.target_channel.name})

            # Connect with timeout
            connection_task = asyncio.create_task(self.target_channel.connect())

            try:
                self.voice_client = await asyncio.wait_for(connection_task, timeout=30)

                self.log_step(
                    "VOICE_CONNECTION",
                    "SUCCESS",
                    {
                        "voice_client_type": type(self.voice_client).__name__,
                        "connected": self.voice_client.is_connected(),
                    },
                )
                return True

            except TimeoutError:
                self.log_step(
                    "VOICE_CONNECTION",
                    "TIMEOUT",
                    {
                        "timeout_seconds": 30,
                        "suggestion": "Voice gateway or network issue",
                    },
                )
                connection_task.cancel()
                return False

        except Exception as e:
            self.log_step(
                "VOICE_CONNECTION",
                "FAILED",
                {
                    "error": f"{type(e).__name__}: {e!s}",
                    "suggestion": "Check bot permissions and network connectivity",
                },
            )
            return False

    async def test_voice_websocket(self):
        """Test voice WebSocket connection."""
        try:
            ws_available = hasattr(self.voice_client, "ws") and self.voice_client.ws is not None

            if not ws_available:
                self.log_step(
                    "VOICE_WEBSOCKET",
                    "FAILED",
                    {
                        "error": "WebSocket not available",
                        "has_ws_attr": hasattr(self.voice_client, "ws"),
                        "ws_is_none": (self.voice_client.ws is None if hasattr(self.voice_client, "ws") else "N/A"),
                    },
                )
                return False

            ws_connected = not self.voice_client.ws.closed

            self.log_step(
                "VOICE_WEBSOCKET",
                "SUCCESS",
                {
                    "websocket_connected": ws_connected,
                    "websocket_type": type(self.voice_client.ws).__name__,
                },
            )

            return ws_connected

        except Exception as e:
            self.log_step("VOICE_WEBSOCKET", "FAILED", {"error": f"{type(e).__name__}: {e!s}"})
            return False

    async def test_speaking_protocol(self):
        """Test Discord speaking protocol (Opcode 5)."""
        if not self.voice_client or not hasattr(self.voice_client, "ws") or not self.voice_client.ws:
            self.log_step("SPEAKING_PROTOCOL", "SKIPPED", {"reason": "No WebSocket available"})
            return False

        try:
            # Test speaking TRUE
            self.log_step("SPEAKING_PROTOCOL", "TESTING_TRUE", {})
            await self.voice_client.ws.speak(True)
            await asyncio.sleep(1)

            # Test speaking FALSE
            self.log_step("SPEAKING_PROTOCOL", "TESTING_FALSE", {})
            await self.voice_client.ws.speak(False)

            self.log_step(
                "SPEAKING_PROTOCOL",
                "SUCCESS",
                {"speak_true_sent": True, "speak_false_sent": True},
            )
            return True

        except Exception as e:
            self.log_step(
                "SPEAKING_PROTOCOL",
                "FAILED",
                {
                    "error": f"{type(e).__name__}: {e!s}",
                    "critical": "This prevents audio transmission to Discord",
                },
            )
            return False

    async def test_audio_transmission(self):
        """Test actual audio transmission."""
        if not self.voice_client:
            self.log_step("AUDIO_TRANSMISSION", "SKIPPED", {"reason": "No voice client"})
            return False

        try:
            # Create test audio
            test_path = audio_debugger.create_test_audio(800, 2.0, 48000)

            # Create Discord audio source
            ffmpeg_options = {"options": "-ar 48000 -ac 2 -f s16le"}
            audio_source = discord.FFmpegPCMAudio(str(test_path), **ffmpeg_options)

            self.log_step(
                "AUDIO_TRANSMISSION",
                "AUDIO_SOURCE_CREATED",
                {
                    "audio_source_type": type(audio_source).__name__,
                    "test_file": str(test_path),
                },
            )

            # Set speaking state and play
            if hasattr(self.voice_client, "ws") and self.voice_client.ws:
                await self.voice_client.ws.speak(True)

            self.voice_client.play(audio_source)

            # Monitor playback
            playback_start = asyncio.get_event_loop().time()
            max_wait = 5  # 5 second maximum wait

            while self.voice_client.is_playing() and (asyncio.get_event_loop().time() - playback_start) < max_wait:
                await asyncio.sleep(0.1)

            playback_duration = asyncio.get_event_loop().time() - playback_start

            # Clear speaking state
            if hasattr(self.voice_client, "ws") and self.voice_client.ws:
                await self.voice_client.ws.speak(False)

            self.log_step(
                "AUDIO_TRANSMISSION",
                "COMPLETED",
                {
                    "playback_duration": f"{playback_duration:.2f}s",
                    "completed_normally": not self.voice_client.is_playing(),
                    "status": "Audio should now be audible in Discord voice channel",
                },
            )

            return True

        except Exception as e:
            self.log_step(
                "AUDIO_TRANSMISSION",
                "FAILED",
                {"error": f"{type(e).__name__}: {e!s}"},
            )
            return False

    def generate_debug_report(self):
        """Generate comprehensive debug report."""
        print("\\n" + "=" * 60)
        print("🔍 VOICE PROTOCOL DEBUG REPORT")
        print("=" * 60)

        success_count = len([entry for entry in self.debug_log if entry["status"] == "SUCCESS"])
        failed_count = len([entry for entry in self.debug_log if entry["status"] == "FAILED"])
        total_count = len([entry for entry in self.debug_log if entry["status"] in ["SUCCESS", "FAILED"]])

        print(f"📊 Results: {success_count}/{total_count} steps successful")
        print(f"❌ Failed steps: {failed_count}")

        # Show all steps
        for entry in self.debug_log:
            status_icon = "✅" if entry["status"] == "SUCCESS" else "❌" if entry["status"] == "FAILED" else "🔄"
            print(f'{status_icon} {entry["step"]}: {entry["status"]}')

            if entry["status"] == "FAILED" and "error" in entry.get("details", {}):
                print(f'    Error: {entry["details"]["error"]}')

        # Save detailed log
        debug_session_dir = audio_debugger.session_dir
        log_file = debug_session_dir / "voice_protocol_debug.json"

        with open(log_file, "w") as f:
            json.dump(
                {
                    "session_id": audio_debugger.session_id,
                    "debug_steps": self.debug_log,
                    "summary": {
                        "total_steps": total_count,
                        "successful_steps": success_count,
                        "failed_steps": failed_count,
                    },
                },
                f,
                indent=2,
            )

        print(f"📄 Detailed log saved to: {log_file}")


async def main():
    """Run comprehensive voice debugging."""
    debugger = VoiceProtocolDebugger()
    await debugger.debug_voice_protocol()


if __name__ == "__main__":
    asyncio.run(main())
