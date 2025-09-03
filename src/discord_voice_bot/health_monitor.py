"""Enhanced health monitoring system for Discord Voice TTS Bot."""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, cast

import discord
from loguru import logger

from .protocols import ConfigManager, DiscordBotClient
from .tts_client import TTSClient


@dataclass
class FailureRecord:
    """Record of a system failure."""

    timestamp: float
    failure_type: str
    details: str
    resolved: bool = False
    resolution_time: float | None = None


@dataclass
class HealthStatus:
    """Comprehensive health status information."""

    healthy: bool = True
    issues: list[str] = field(default_factory=lambda: list[str]())
    recommendations: list[str] = field(default_factory=lambda: list[str]())
    last_check: float = field(default_factory=time.time)
    failure_count: int = 0
    recent_failures: list[FailureRecord] = field(default_factory=lambda: list[FailureRecord]())


class HealthMonitor:
    """Comprehensive health monitoring system with automatic termination."""

    def __init__(self, bot_client: discord.Client | DiscordBotClient, config_manager: ConfigManager, tts_client: TTSClient):
        """
        Initialize the HealthMonitor.

        Sets up references to the Discord bot, configuration manager, and TTS client, and initializes internal monitoring state used by the health system: a HealthStatus instance, placeholders for background monitoring and permission-check tasks, termination-condition counters (voice disconnection windows and an API-unavailable threshold), and graceful-shutdown bookkeeping (flag, reason, and shutdown task).
        """
        super().__init__()
        self.bot = bot_client
        self._config_manager = config_manager
        self._tts_client = tts_client
        self.status = HealthStatus()
        self._monitoring_task: asyncio.Task[None] | None = None
        self._permission_check_task: asyncio.Task[None] | None = None
        self._termination_conditions: dict[str, dict[str, Any]] = {
            "voice_disconnections_10min": {"max": 5, "window": 600, "count": 0, "last_reset": time.time()},
            "voice_disconnections_30min": {"max": 10, "window": 1800, "count": 0, "last_reset": time.time()},
            "voice_disconnections_1hr": {"max": 20, "window": 3600, "count": 0, "last_reset": time.time()},
            "api_unavailable_duration": {"max": 900, "window": None, "count": 0, "last_reset": time.time()},  # 15 minutes
        }
        self._graceful_shutdown = False
        self._shutdown_reason: str | None = None
        self._shutdown_task: asyncio.Task[None] | None = None
        # Startup timestamp to allow a brief grace window for caches/login
        self._start_ts: float = time.time()
        # Debounce map for repeated warnings
        self._warn_last: dict[str, float] = {}
        # One-time log flags
        self._permission_scan_started: bool = False
        self._critical_perm_checks_started: bool = False

    def _bot_is_ready(self) -> bool:
        """Return True if the bot reports ready; supports both attr and method."""
        ready_attr = getattr(self.bot, "is_ready", None)
        try:
            return bool(ready_attr()) if callable(ready_attr) else bool(ready_attr)
        except Exception:
            return False

    def _in_grace_window(self, seconds: float = 15.0) -> bool:
        """Return True if within initial startup grace period."""
        try:
            return (time.time() - self._start_ts) < seconds
        except Exception:
            return False

    def _should_emit_warning(self, key: str, window_s: float = 10.0) -> bool:
        """Return True if a warning identified by `key` should be emitted.

        Maintains a short-lived timestamp map of previously emitted warnings and suppresses
        identical messages within the provided window.
        """
        now = time.time()
        last = self._warn_last.get(key, 0.0)
        if now - last >= window_s:
            self._warn_last[key] = now
            return True
        return False

    async def start(self) -> None:
        """Start health monitoring tasks."""
        logger.info("🩺 Starting enhanced health monitoring system...")

        # Start main health monitoring task
        self._monitoring_task = asyncio.create_task(self._health_monitoring_loop())
        self._permission_check_task = asyncio.create_task(self._permission_check_loop())

        logger.info("✅ Health monitoring system started")

    async def stop(self) -> None:
        """Stop health monitoring tasks."""
        if self._monitoring_task:
            _ = self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        if self._permission_check_task:
            _ = self._permission_check_task.cancel()
            try:
                await self._permission_check_task
            except asyncio.CancelledError:
                pass

        logger.info("🛑 Health monitoring system stopped")

    def record_disconnection(self, reason: str = "Unknown") -> None:
        """Record a voice disconnection event."""
        now = time.time()
        failure = FailureRecord(timestamp=now, failure_type="voice_disconnection", details=reason)
        self.status.recent_failures.append(failure)
        self.status.failure_count += 1

        # Update termination condition counters
        for condition, data in self._termination_conditions.items():
            if "disconnections" in condition:
                if now - data["last_reset"] > data["window"]:
                    data["count"] = 0
                    data["last_reset"] = now
                data["count"] += 1

                if data["count"] >= data["max"]:
                    self._trigger_termination(f"Too many voice disconnections: {data['count']} in {data['window']}s window")

        logger.warning(f"🔌 Voice disconnection recorded: {reason} (Total: {self.status.failure_count})")

    def record_api_failure(self) -> None:
        """Record a TTS API failure."""
        now = time.time()
        failure = FailureRecord(timestamp=now, failure_type="api_failure", details="TTS API unavailable")
        self.status.recent_failures.append(failure)
        self.status.failure_count += 1

        # Check API unavailable duration
        condition = self._termination_conditions["api_unavailable_duration"]
        # Count consecutive failures and mark the start of the outage window
        if condition["count"] == 0:
            condition["last_reset"] = now
        condition["count"] += 1

        logger.error(f"🚨 TTS API failure recorded (Count: {condition['count']})")

    def record_api_success(self) -> None:
        """Record TTS API success (resets failure count)."""
        self._termination_conditions["api_unavailable_duration"]["count"] = 0
        self._termination_conditions["api_unavailable_duration"]["last_reset"] = time.time()

    async def _create_monitoring_loop(self, operation: Any, interval: int, name: str, retry_interval: int = 30) -> None:
        """Generic monitoring loop with error handling."""
        while not self._graceful_shutdown:
            try:
                await operation()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in {name}: {e}")
                await asyncio.sleep(retry_interval)

    async def _health_monitoring_loop(self) -> None:
        """Main health monitoring loop."""
        await self._create_monitoring_loop(
            self._perform_health_checks,
            60,  # Check every minute
            "health monitoring loop",
        )

    async def _permission_check_loop(self) -> None:
        """Permission checking loop."""
        await self._create_monitoring_loop(
            self._check_bot_permissions,
            300,  # Check every 5 minutes
            "permission check loop",
            60,  # Retry after 1 minute
        )

    async def _perform_health_checks(self) -> None:
        """
        Run the bot's full set of health checks and update internal health state.

        Performs TTS API availability checks, voice-connection checks, and critical-permission checks.
        Aggregates detected issues and recommendations, updates self.status (healthy, issues,
        recommendations, last_check, recent_failures), and records API failures or successes.

        Side effects:
        - May call record_api_failure() / record_api_success().
        - Clears status.recent_failures.
        - Invokes _check_termination_conditions(), which can initiate a graceful shutdown if thresholds are met.

        Exceptions raised by individual checks are caught and appended to the aggregated issues list; the method itself does not raise on those internal failures.
        """
        logger.debug("🔍 Performing comprehensive health checks...")

        issues: list[str] = list[str]()
        recommendations: list[str] = list[str]()

        # Check TTS API health
        try:
            api_healthy, error_detail = await self._tts_client.check_api_availability()
            if not api_healthy:
                issues.append(f"TTS API health check failed: {error_detail}")
                recommendations.append("Check TTS server status and network connectivity")
                self.record_api_failure()
            else:
                self.record_api_success()
        except Exception as e:
            issues.append(f"TTS API check error: {e}")
            recommendations.append("Verify TTS engine configuration")

        # Check voice connection health
        try:
            voice_healthy, voice_issues = await self._check_voice_connection_health()
            # Ensure issues list is fully typed as list[str]
            voice_issues = [str(x) for x in (voice_issues or [])]
            if not voice_healthy:
                issues.extend(voice_issues)
                recommendations.append("Check voice channel permissions and network connectivity")
        except Exception as e:
            issues.append("Voice connection check error: " + str(e))

        # Check bot permissions
        try:
            perm_healthy, perm_issues = await self._check_critical_permissions()
            if not perm_healthy:
                issues.extend(perm_issues)
                recommendations.append("Review and fix bot permissions in Discord server")
        except Exception as e:
            issues.append("Permission check error: " + str(e))

        # Update health status
        self.status.healthy = len(issues) == 0
        self.status.issues = issues
        self.status.recommendations = recommendations
        self.status.last_check = time.time()
        # Keep a bounded history (last 50) for diagnostics
        self.status.recent_failures = self.status.recent_failures[-50:]

        if not self.status.healthy:
            logger.warning(f"⚠️ Health check detected {len(issues)} issues:")
            for issue in issues:
                logger.warning(f"   • {issue}")
            for recommendation in recommendations:
                logger.info(f"   💡 {recommendation}")
        else:
            logger.debug("✅ All health checks passed")

        # Check termination conditions
        await self._check_termination_conditions()

    async def _check_voice_connection_health(self) -> tuple[bool, list[str]]:
        """Check voice connection health."""
        issues: list[str] = []

        try:
            # Check bot readiness status
            bot_ready = self._bot_is_ready()
            logger.debug(f"🔍 Voice health check: Bot ready = {bot_ready}")

            # Get voice handler status
            voice_handler = getattr(self.bot, "voice_handler", None)
            logger.debug(f"🔍 Voice health check: Voice handler present = {voice_handler is not None}")

            if voice_handler:
                # Suppress voice connection warnings until bot is ready (or during grace)
                if not bot_ready or self._in_grace_window():
                    logger.debug("🔍 Voice health check: Startup phase; suppressing voice connection warnings")
                    return True, []
                # Obtain status defensively (support sync or async get_status implementations)
                get_status = getattr(voice_handler, "get_status", None)
                status: dict[str, Any] = {}
                if callable(get_status):
                    try:
                        if asyncio.iscoroutinefunction(get_status):
                            maybe = await get_status()
                        else:
                            maybe = get_status()
                        if isinstance(maybe, dict):
                            status = cast(dict[str, Any], maybe)
                    except Exception:
                        status = {}
                if not status.get("connected", False):
                    issues.append("Voice connection lost")
                    msg = f"🔍 Voice health check: Connection status = {status.get('connected', 'unknown')}"
                    if self._should_emit_warning(msg):
                        logger.warning(msg)
                    self.record_disconnection("Health check detected disconnection")
                elif not status.get("audio_playback_ready", True):
                    issues.append("Audio playback not ready")
                    msg = f"🔍 Voice health check: Audio playback ready = {status.get('audio_playback_ready', 'unknown')}"
                    if self._should_emit_warning(msg):
                        logger.warning(msg)
            else:
                # Only report as issue if bot is ready but voice handler is missing
                if bot_ready:
                    issues.append("Voice handler not initialized")
                    msg = "🔍 Voice health check: Bot is ready but voice handler is missing - this may indicate a problem"
                    if self._should_emit_warning(msg):
                        logger.warning(msg)
                else:
                    logger.debug("🔍 Voice health check: Voice handler not yet available (bot not ready) - this is normal during startup")
        except AttributeError:
            issues.append("Voice handler access error")
            msg = "🔍 Voice health check: AttributeError accessing voice handler"
            if self._should_emit_warning(msg):
                logger.warning(msg)

        except Exception as e:
            issues.append("Voice health check error: " + str(e))
            logger.error(f"🔍 Voice health check: Unexpected error: {e}")

        return len(issues) == 0, issues

    def _check_permissions_in_guild(self, guild: discord.Guild, critical_perms: dict[str, bool], trigger_termination: bool = False) -> list[str]:
        """Check permissions in a specific guild."""
        missing_perms = [perm for perm, has_perm in critical_perms.items() if not has_perm]

        if missing_perms:
            msg = f"⚠️ Missing permissions in {guild.name}: {', '.join(missing_perms)}"
            if self._should_emit_warning(msg):
                logger.warning(msg)

            # Check if this affects our target channel
            target_channel = self.bot.get_channel(self._config_manager.get_target_voice_channel_id())
            if isinstance(target_channel, (discord.VoiceChannel, discord.StageChannel)) and target_channel.guild == guild:
                if trigger_termination:
                    logger.error(f"🚨 Critical permissions missing in target guild {guild.name}")
                    self._trigger_termination(f"Missing critical permissions: {', '.join(missing_perms)}")
        else:
            logger.debug(f"✅ All permissions present in {guild.name}")

        return missing_perms

    async def _check_bot_permissions(self) -> None:
        """Check bot permissions across all accessible guilds."""
        logger.debug("🔐 Performing comprehensive bot permissions check...")

        # Suppress early warnings until ready or after grace
        if not self._bot_is_ready() or self._in_grace_window():
            logger.debug("🔐 Startup phase; skipping guild permission warnings")
            return

        # First time we are past startup/grace, announce that permission scans begin
        if not self._permission_scan_started:
            self._permission_scan_started = True
            logger.info("🔐 Bot is ready; starting periodic guild permission scans")

        if not self.bot.guilds:
            logger.warning("⚠️ Bot is not in any guilds")
            return

        for guild in self.bot.guilds:
            try:
                if guild.me:
                    perms = guild.me.guild_permissions
                    critical_perms = {
                        "view_channels": perms.view_channel,
                        "connect": perms.connect,
                        "speak": perms.speak,
                        "use_voice_activation": perms.use_voice_activation,
                        "read_messages": perms.read_message_history,
                    }
                    _ = self._check_permissions_in_guild(guild, critical_perms, trigger_termination=True)

            except Exception as e:
                logger.error(f"Error checking permissions in {guild.name}: {e}")

    async def _check_critical_permissions(self) -> tuple[bool, list[str]]:
        """Check critical permissions for bot operation."""
        issues: list[str] = []

        try:
            # Suppress target-channel checks until ready (or after grace)
            if not self._bot_is_ready() or self._in_grace_window():
                logger.debug("🔐 Startup phase; skipping critical permission checks for target channel")
                return True, []

            if not self._critical_perm_checks_started:
                self._critical_perm_checks_started = True
                logger.info("🔐 Beginning critical permission checks for target voice channel")

            target_channel_id = self._config_manager.get_target_voice_channel_id()
            target_channel = self.bot.get_channel(target_channel_id)
            if not target_channel:
                issues.append(f"Target voice channel {target_channel_id} not found")
                return False, issues

            if not isinstance(target_channel, (discord.VoiceChannel, discord.StageChannel)):
                issues.append(f"Target channel is not a voice channel (type: {type(target_channel).__name__})")
                return False, issues

            # Check if bot can access the channel
            bot_perms = target_channel.permissions_for(target_channel.guild.me)

            critical_perms = {
                "view_channel": bot_perms.view_channel,
                "connect": bot_perms.connect,
                "speak": bot_perms.speak,
            }

            missing_perms = [perm for perm, has_perm in critical_perms.items() if not has_perm]
            issues.extend([f"Missing '{perm}' permission for target voice channel" for perm in missing_perms])

        except Exception as e:
            issues.append("Critical permission check error: " + str(e))

        return len(issues) == 0, issues

    async def _check_termination_conditions(self) -> None:
        """Check if any termination conditions are met."""
        if self._graceful_shutdown:
            return

        now = time.time()

        # Check disconnection thresholds
        for condition_name, condition in self._termination_conditions.items():
            if "disconnections" in condition_name:
                if condition["count"] >= condition["max"]:
                    self._trigger_termination(f"Termination condition met: {condition['count']} {condition_name} (threshold: {condition['max']})")

        # Check API unavailable duration
        api_condition = self._termination_conditions["api_unavailable_duration"]
        if api_condition["count"] > 0:
            duration = now - api_condition["last_reset"]
            if duration >= api_condition["max"]:
                self._trigger_termination(f"TTS API has been unavailable for {duration:.0f} seconds")

    def _trigger_termination(self, reason: str) -> None:
        """Trigger server termination with detailed logging."""
        if self._graceful_shutdown:
            return

        self._graceful_shutdown = True
        self._shutdown_reason = reason

        logger.error("🚨 AUTOMATIC TERMINATION TRIGGERED 🚨")
        logger.error(f"Reason: {reason}")
        logger.error("🔧 Server will shutdown to prevent further issues")
        logger.error("💡 Check the following:")
        logger.error("   1. Network connectivity")
        logger.error("   2. Discord bot permissions")
        logger.error("   3. TTS API server status")
        logger.error("   4. Voice channel accessibility")

        # Log recent failures for debugging
        if self.status.recent_failures:
            logger.error(f"📊 Recent failures ({len(self.status.recent_failures)} total):")
            for failure in self.status.recent_failures[-5:]:  # Show last 5
                age = time.time() - failure.timestamp
                logger.error(f"   • {failure.failure_type} ({age:.0f}s ago): {failure.details}")

        # Force shutdown
        self._shutdown_task = asyncio.create_task(self._perform_shutdown())

    async def _perform_shutdown(self) -> None:
        """
        Initiate a graceful shutdown: attempt to clean up the voice handler, close the Discord client, and terminate the process.

        This coroutine attempts to run `voice_handler.cleanup()` if a `voice_handler` attribute exists on the bot (supports sync or async cleanup). It then closes the Discord client connection if it is open. Any exceptions during cleanup or closing are caught and logged. Finally, the process is terminated with exit code 1.
        """
        logger.error("🔄 Initiating graceful shutdown...")

        try:
            # Stop voice handler if exists
            voice_handler = getattr(self.bot, "voice_handler", None)
            if voice_handler:
                cleanup = getattr(voice_handler, "cleanup", None)
                if callable(cleanup):
                    try:
                        if asyncio.iscoroutinefunction(cleanup):
                            await cleanup()
                        else:
                            _ = cleanup()
                    except Exception as e:
                        logger.warning(f"Voice handler cleanup failed: {e}")

            # Close Discord connection
            if not self.bot.is_closed():
                await self.bot.close()

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

        finally:
            logger.error("💀 Server shutdown complete")
            # Exit with error code (skip in test mode)
            import sys

            try:
                is_test = getattr(self._config_manager, "is_test_mode", None)
                if callable(is_test) and is_test():
                    logger.error("🧪 Test mode detected; skipping sys.exit(1)")
                else:
                    sys.exit(1)
            except Exception:
                # Fall through to exit if we cannot determine test mode
                sys.exit(1)

    def get_health_status(self) -> dict[str, Any]:
        """Get current health status information."""
        return {
            "healthy": self.status.healthy,
            "issues": self.status.issues.copy(),
            "recommendations": self.status.recommendations.copy(),
            "last_check": self.status.last_check,
            "failure_count": self.status.failure_count,
            "recent_failures": len(self.status.recent_failures),
            "termination_conditions": {
                name: {"count": data["count"], "max": data["max"], "window": data["window"], "last_reset": data["last_reset"]} for name, data in self._termination_conditions.items()
            },
            "shutdown_reason": self._shutdown_reason,
            "graceful_shutdown": self._graceful_shutdown,
        }

    # Test access method
    async def perform_health_checks_for_testing(self) -> None:
        """Perform health checks for testing purposes.

        This is a public method to allow tests to trigger health checks
        without accessing private methods.
        """
        await self._perform_health_checks()


# Global health monitor instance
health_monitor: HealthMonitor | None = None
