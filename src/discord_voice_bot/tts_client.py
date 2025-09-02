"""TTS API client for managing communication with TTS services."""

import asyncio
from typing import Any
from weakref import ref

import aiohttp
from loguru import logger

from .config import DEFAULT_AIVIS_URL, DEFAULT_VOICEVOX_URL, Config


class TTSClient:
    """Manages TTS API communication and requests."""

    def __init__(self, config: Config) -> None:
        """
        Create a TTSClient tied to the provided configuration.

        Stores a weak reference to the given Config (so the Config may be garbage-collected),
        initializes the internal aiohttp ClientSession placeholder to None, and creates an
        asyncio.Lock to guard lazy session creation and teardown.
        """
        super().__init__()
        self._config_ref = ref(config)
        self._session: aiohttp.ClientSession | None = None
        self._session_lock = asyncio.Lock()

    @property
    def config(self) -> Config:
        """
        Return the live Config instance referenced by this TTSClient.

        Retrieves the Config object previously stored as a weak reference. Raises a RuntimeError if the referenced Config has been garbage-collected, indicating the client is no longer bound to a live configuration.

        Returns:
            Config: The active configuration object.

        Raises:
            RuntimeError: If the weak reference no longer points to a live Config.

        """
        cfg = self._config_ref()
        if cfg is None:
            raise RuntimeError("Config has been garbage-collected; TTSClient is unbound")
        return cfg

    @property
    def api_url(self) -> str:
        """
        Return the base API URL for the configured TTS engine.

        Falls back to an engine-specific default when the engine is unknown or missing a URL
        (AIVIS → DEFAULT_AIVIS_URL; otherwise DEFAULT_VOICEVOX_URL).
        """
        engine_name = str(self.config.tts_engine).lower()
        if self.config.tts_engine not in self.config.engines:
            known = ", ".join(sorted(self.config.engines.keys()))
            logger.warning(f"Configured TTS engine '{self.config.tts_engine}' not found. Known engines=[{known}]. Falling back to default URL.")
            return DEFAULT_AIVIS_URL if engine_name == "aivis" else DEFAULT_VOICEVOX_URL

        engine_config = self.config.engines.get(self.config.tts_engine, {})
        default_url = DEFAULT_AIVIS_URL if engine_name == "aivis" else DEFAULT_VOICEVOX_URL
        return engine_config.get("url", default_url)

    @property
    def speaker_id(self) -> int:
        """
        Return the resolved speaker ID to use for synthesis.

        If the configured `tts_speaker` is a numeric value (or numeric string), that value is returned.
        Otherwise the method resolves a speaker ID from the configured engine's speaker map:
        - prefers the engine's `default_speaker` if present and castable to int;
        - otherwise uses the first value from the engine's `speakers` mapping;
        - if none of the above are available or castable to int, falls back to 3.

        All conversions are performed safely: non-integer or missing values are handled and a valid int is always returned.
        """
        val = str(self.config.tts_speaker).strip()
        if val.isdigit():
            return int(val)
        engines = self.config.engines
        engine = self.config.tts_engine
        engine_cfg: dict[str, Any] = dict(engines.get(engine, {}))  # MappingProxyType is dict-like
        speakers: dict[str, Any] = dict(engine_cfg.get("speakers", {}))

        # Prefer engine-local default; if missing, pick first speakers value; finally fallback to 3.
        speakers_values = list(speakers.values())
        fallback = 3

        def _to_int(v: Any, d: int) -> int:
            """
            Convert a value to an int, returning a provided default if conversion fails.

            Args:
                v: Value to convert to int.
                d: Default integer to return if `v` cannot be converted.

            Returns:
                int: The converted integer, or `d` when a TypeError or ValueError occurs.

            """
            try:
                return int(v)
            except (TypeError, ValueError):
                return d

        default = _to_int(engine_cfg.get("default_speaker"), _to_int(speakers_values[0] if speakers_values else None, fallback))

        try:
            cand = speakers.get(val, default)
            return int(cand)
        except (TypeError, ValueError):
            return default

    @property
    def engine_name(self) -> str:
        """
        Return the configured TTS engine name in uppercase.

        Returns:
            str: The TTS engine name converted to uppercase.

        """
        return self.config.tts_engine.upper()

    @property
    def session(self) -> aiohttp.ClientSession | None:
        """Get HTTP session for testing purposes."""
        return self._session

    async def start_session(self) -> None:
        """
        Lazily create and store the aiohttp ClientSession used for TTS API calls.

        If a session already exists this is a no-op. The operation is serialized with
        the client's internal asyncio Lock so concurrent callers do not create multiple
        sessions. The created ClientSession uses a short timeout (total=10s, connect=2s).
        """
        async with self._session_lock:
            if not self._session:
                logger.debug("🔗 Creating new aiohttp ClientSession for TTS client")
                timeout = aiohttp.ClientTimeout(total=10, connect=2)
                # Optional: tune connector for better pooling/latency under load.
                # connector = aiohttp.TCPConnector(limit=100, ttl_dns_cache=10)
                self._session = aiohttp.ClientSession(timeout=timeout)  # , connector=connector)
                logger.debug("✅ aiohttp ClientSession created successfully")

    async def close_session(self) -> None:
        """
        Close and clear the internal aiohttp ClientSession.

        This asynchronous, idempotent method acquires the internal session lock, closes the existing ClientSession if present (awaiting its close), and sets the internal session reference to None. Safe to call concurrently; if no session exists the method returns immediately.
        """
        async with self._session_lock:
            if self._session:
                logger.debug("🔗 Closing aiohttp ClientSession for TTS client")
                await self._session.close()
                self._session = None
                logger.debug("✅ aiohttp ClientSession closed successfully")

    # Backward-compatible aliases for tests/fixtures
    async def close(self) -> None:  # pragma: no cover - compatibility
        """
        Compatibility alias that closes the client's HTTP session.

        Asynchronously delegates to close_session() to close and clear the internal aiohttp ClientSession. Safe to call when no session exists.
        """
        await self.close_session()

    async def aclose(self) -> None:  # pragma: no cover - compatibility
        """
        Compatibility async alias for close_session.

        Provided for backward compatibility with older APIs; awaits close_session() to close and clear the internal HTTP session.
        """
        await self.close_session()

    async def check_api_availability(self) -> tuple[bool, str]:
        """
        Check whether the configured TTS API is reachable and return a short diagnostic.

        Ensures an aiohttp session is available and performs GET {api_url}/version. On HTTP 200 returns (True, "").
        On failure returns (False, detail) where `detail` is a short diagnostic such as:
        - "HTTP <status>" for non-200 responses (a short response-body snippet is logged for diagnostics),
        - "connection refused - server not running",
        - "connection timeout - server may be starting up",
        - "unexpected error: <ExceptionName>" for other errors.

        Preserves cooperative cancellation by re-raising asyncio.CancelledError.
        """
        if not self._session:
            await self.start_session()

        try:
            assert self._session is not None  # Type guard for mypy
            async with self._session.get(f"{self.api_url}/version") as response:
                if response.status == 200:
                    logger.debug(f"{self.engine_name} TTS API is available")
                    return True, ""
                else:
                    # Read up to 256 bytes of body for diagnostics
                    try:
                        body_snippet = (await response.text())[:256]
                    except Exception:
                        body_snippet = "<unavailable>"
                    error_msg = f"HTTP {response.status}"
                    logger.warning(f"{self.engine_name} TTS API returned {error_msg}; body={body_snippet!r}")
                    return False, error_msg

        except aiohttp.ClientConnectorError:
            error_msg = "connection refused - server not running"
            logger.error(f"{self.engine_name} TTS API: {error_msg}")
            return False, error_msg

        # Why we catch the built-in TimeoutError (Python ≥ 3.11, our project uses 3.12):
        # - In Python 3.11+, asyncio.TimeoutError is an alias of the built-in TimeoutError.
        #   (See Python docs: asyncio.TimeoutError — deprecated alias of TimeoutError.)
        # - aiohttp raises timeout-specific exceptions (ServerTimeoutError, ConnectionTimeoutError,
        #   SocketTimeoutError) that all inherit from asyncio.TimeoutError — and therefore from TimeoutError.
        # - Catching TimeoutError thus handles all aiohttp timeouts without redundancy; writing
        #   (asyncio.TimeoutError, TimeoutError) is equivalent but noisier.
        # - Linters (e.g., Ruff UP041) recommend using the built-in TimeoutError directly on 3.11+.
        # - If this code is ever backported to Python ≤ 3.10, revisit this decision.
        except TimeoutError:
            error_msg = "connection timeout - server may be starting up"
            logger.error(f"{self.engine_name} TTS API: {error_msg}")
            return False, error_msg

        except asyncio.CancelledError:
            # Preserve cooperative cancellation
            raise

        except Exception as e:
            error_msg = f"unexpected error: {type(e).__name__}"
            logger.error(f"{self.engine_name} TTS API: {error_msg} - {e!s}")
            return False, error_msg

    async def generate_audio_query(self, text: str, speaker_id: int, api_url: str) -> dict[str, Any] | None:
        """
        Create an audio_query payload for synthesis by POSTing the given text and speaker to the engine's /audio_query endpoint.

        Args:
            text: Input text to convert into an audio_query.
            speaker_id: Speaker identifier to request from the TTS engine.
            api_url: Base URL of the TTS engine API (used as {api_url}/audio_query).

        Returns:
            dict[str, Any] | None: Parsed JSON audio_query on success, or None on failure.

        Raises:
            asyncio.CancelledError: Propagated if the coroutine is cancelled.

        """
        try:
            if self._session is None:
                await self.start_session()
            params = {"text": text, "speaker": speaker_id}
            url = f"{api_url}/audio_query"

            assert self._session is not None  # Type guard for mypy
            async with self._session.post(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"Audio query failed with status {response.status}")
                    return None

                return await response.json()

        except asyncio.CancelledError:
            # Propagate cooperative cancellation
            raise
        except Exception as e:
            logger.error(f"Failed to generate audio query: {e!s}")
            return None

    async def synthesize_from_query(self, audio_query: dict[str, Any], speaker_id: int, api_url: str) -> bytes | None:
        """
        Synthesize audio bytes from an audio_query by calling the TTS engine's /synthesis endpoint.

        Sends a POST to "{api_url}/synthesis" with the audio_query as JSON and the speaker as a query parameter.
        On a successful (HTTP 200) response returns the raw audio bytes; on any non-200 response or error returns None.
        Cooperative cancellation via asyncio.CancelledError is propagated.
        """
        try:
            if self._session is None:
                await self.start_session()
            params = {"speaker": speaker_id}
            url = f"{api_url}/synthesis"

            assert self._session is not None  # Type guard for mypy
            async with self._session.post(url, params=params, json=audio_query) as response:
                if response.status != 200:
                    logger.error(f"Audio synthesis failed with status {response.status}")
                    return None

                return await response.read()

        except asyncio.CancelledError:
            # Propagate cooperative cancellation
            raise
        except Exception as e:
            logger.error(f"Failed to synthesize from query: {e!s}")
            return None

    async def synthesize_audio(self, text: str, speaker_id: int | None = None, engine_name: str | None = None) -> bytes | None:
        """
        Synthesize spoken audio bytes from input text using the configured TTS engine.

        Performs a high-level synthesis workflow: ensures an HTTP session is available, chooses the target engine (explicit override or configured engine, falling back to "voicevox" or the first configured engine if the requested one is missing), resolves a speaker ID (explicit override or the engine's `default_speaker`, then the first available speaker, then 3), selects the engine's API URL (falls back to DEFAULT_AIVIS_URL for "aivis" or DEFAULT_VOICEVOX_URL otherwise), requests an `audio_query` from the engine, and sends that query to produce raw audio bytes.

        Returns:
            bytes: Raw synthesized audio on success.
            None: If input text is empty, if engine selection fails, if the audio query or synthesis fails, or if an unexpected error occurs (exceptions are caught and result in None).

        """
        # Check for empty text early
        if not text or not text.strip():
            logger.debug("Empty text provided, returning None")
            return None

        if not self._session:
            await self.start_session()

        # Determine engine and speaker
        target_engine = (engine_name or self.config.tts_engine).lower()
        engines = self.config.engines
        engine_config = engines.get(target_engine)
        if not engine_config:
            fallback = "voicevox" if "voicevox" in engines else (next(iter(engines.keys()), None))
            logger.error(f"Unknown TTS engine requested; target={target_engine} fallback={fallback}")
            if not fallback:
                logger.error("No TTS engines configured; aborting synthesis")
                return None
            target_engine = fallback
            engine_config = engines[target_engine]

        # Use provided speaker ID or engine-local default with safe fallback derived from target_engine
        if speaker_id is not None:
            current_speaker_id = speaker_id
        else:
            speakers_map = dict(engine_config.get("speakers", {}))

            def _to_int(v: Any, d: int) -> int:
                """
                Convert a value to int, returning a default if conversion fails.

                Attempts to cast `v` to int using the built-in `int()`. If `v` is not convertible
                (a TypeError or ValueError is raised), returns the provided default `d`.

                Args:
                    v: The value to convert to int.
                    d: The integer to return if conversion of `v` fails.

                Returns:
                    int: The converted integer or the default `d` when conversion is not possible.

                """
                try:
                    return int(v)
                except (TypeError, ValueError):
                    return d

            first_speaker_any: Any = next(iter(speakers_map.values()), None)
            default_local = _to_int(engine_config.get("default_speaker"), _to_int(first_speaker_any, 3))
            current_speaker_id = default_local
        # Prefer engine's configured URL; if missing (unexpected), fall back to the
        # known default of the selected engine to avoid cross-engine bleed-through.
        if target_engine == "aivis":
            default_url = DEFAULT_AIVIS_URL
        else:
            default_url = DEFAULT_VOICEVOX_URL
        target_api_url = engine_config.get("url", default_url)

        logger.debug(f"Using {target_engine} engine (URL: {target_api_url}) with speaker {current_speaker_id}")

        try:
            # Generate audio query using target engine
            audio_query = await self.generate_audio_query(text, current_speaker_id, target_api_url)
            if not audio_query:
                return None

            # Synthesize audio
            audio_data = await self.synthesize_from_query(audio_query, current_speaker_id, target_api_url)
            if not audio_data:
                return None

            logger.info(f"Successfully synthesized audio for text: '{text[:50]}...'")
            return audio_data

        except Exception as e:
            logger.error(f"Failed to synthesize audio: {type(e).__name__} - {e!s}")
            return None
