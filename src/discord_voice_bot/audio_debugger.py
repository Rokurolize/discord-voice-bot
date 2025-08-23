"""Comprehensive audio debugging system for Discord Voice TTS Bot."""

import json
import struct
import subprocess
import wave
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger


class AudioDebugger:
    """Debug system for saving and validating audio at each pipeline stage."""

    def __init__(self, debug_dir: str = "/tmp/discord_tts_debug"):
        """Initialize audio debugger.

        Args:
            debug_dir: Directory to save debug audio files

        """
        super().__init__()
        self.debug_dir = Path(debug_dir)
        self.debug_dir.mkdir(exist_ok=True)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.debug_dir / f"session_{self.session_id}"
        self.session_dir.mkdir(exist_ok=True)

        logger.info(f"Audio debugger initialized: {self.session_dir}")

        # Create session log
        self.log_file = self.session_dir / "debug_log.json"
        self.debug_log: list[dict[str, Any]] = []

    def save_audio_stage(
        self,
        audio_data: bytes,
        stage: str,
        text: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        """Save audio data for a specific pipeline stage.

        Args:
            audio_data: Raw audio data
            stage: Pipeline stage name (e.g., 'tts_raw', 'discord_converted')
            text: Original text that generated this audio
            metadata: Additional metadata to save

        Returns:
            Path to saved audio file

        """
        timestamp = datetime.now().strftime("%H%M%S_%f")[:-3]  # Include milliseconds
        filename = f"{timestamp}_{stage}.wav"
        filepath = self.session_dir / filename

        # Save audio data
        with open(filepath, "wb") as f:
            _ = f.write(audio_data)

        # Create metadata
        debug_entry = {
            "timestamp": datetime.now().isoformat(),
            "stage": stage,
            "filename": filename,
            "size_bytes": len(audio_data),
            "text": text[:100] if text else "",  # Truncate for logging
            "metadata": metadata or {},
        }

        # Add audio file analysis
        try:
            audio_info = self._analyze_audio_file(filepath)
            debug_entry["audio_info"] = audio_info
        except Exception as e:
            debug_entry["audio_analysis_error"] = str(e)

        self.debug_log.append(debug_entry)
        self._save_debug_log()

        logger.info(f"🎵 Saved {stage} audio: {filepath} ({len(audio_data)} bytes)")

        return filepath

    def _analyze_audio_file(self, filepath: Path) -> dict[str, Any]:
        """Analyze audio file properties using ffprobe."""
        try:
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-show_format",
                "-show_streams",
                "-of",
                "json",
                str(filepath),
            ]

            result = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                probe_data = json.loads(result.stdout)

                # Extract key audio properties
                audio_info: dict[str, Any] = {
                    "duration": None,
                    "sample_rate": None,
                    "channels": None,
                    "bit_rate": None,
                    "codec_name": None,
                    "format_name": None,
                }

                if "format" in probe_data:
                    fmt = probe_data["format"]
                    audio_info.update(
                        {
                            "duration": float(fmt.get("duration", 0)),
                            "bit_rate": int(fmt.get("bit_rate", 0)),
                            "format_name": fmt.get("format_name", "unknown"),
                        }
                    )

                if probe_data.get("streams"):
                    stream = probe_data["streams"][0]  # First audio stream
                    audio_info.update(
                        {
                            "sample_rate": int(stream.get("sample_rate", 0)),
                            "channels": int(stream.get("channels", 0)),
                            "codec_name": stream.get("codec_name", "unknown"),
                        }
                    )

                return audio_info
            else:
                return {"error": "ffprobe failed", "stderr": result.stderr}

        except Exception as e:
            return {"error": str(e)}

    def _save_debug_log(self) -> None:
        """Save debug log to JSON file."""
        with open(self.log_file, "w") as f:
            json.dump({"session_id": self.session_id, "entries": self.debug_log}, f, indent=2)

    def create_test_audio(self, frequency: int = 440, duration: float = 2.0, sample_rate: int = 48000) -> Path:
        """Create a test sine wave audio file for Discord testing.

        Args:
            frequency: Sine wave frequency in Hz
            duration: Duration in seconds
            sample_rate: Sample rate in Hz

        Returns:
            Path to created test audio file

        """
        filename = f"test_sine_{frequency}hz_{duration}s.wav"
        filepath = self.session_dir / filename

        # Generate stereo sine wave
        num_samples = int(sample_rate * duration)

        with wave.open(str(filepath), "w") as wav_file:
            wav_file.setnchannels(2)  # Stereo for Discord
            wav_file.setsampwidth(2)  # 16-bit samples
            wav_file.setframerate(sample_rate)

            for i in range(num_samples):
                # Calculate sine wave sample
                sample = int(16384 * 0.8 * (__import__("math").sin(2 * __import__("math").pi * frequency * i / sample_rate)))

                # Write stereo sample (same value for both channels)
                packed_sample = struct.pack("<hh", sample, sample)  # Little endian, stereo
                wav_file.writeframes(packed_sample)

        logger.info(f"🎵 Created test audio: {filepath} ({frequency}Hz, {duration}s)")

        # Add to debug log
        self.debug_log.append(
            {
                "timestamp": datetime.now().isoformat(),
                "stage": "test_audio_created",
                "filename": filename,
                "parameters": {
                    "frequency": frequency,
                    "duration": duration,
                    "sample_rate": sample_rate,
                },
            }
        )
        self._save_debug_log()

        return filepath

    def test_audio_playback(self, filepath: Path) -> dict[str, Any]:
        """Test audio file playback using system tools.

        Args:
            filepath: Path to audio file to test

        Returns:
            Dictionary with test results

        """
        results: dict[str, Any] = {
            "file_exists": filepath.exists(),
            "file_size": filepath.stat().st_size if filepath.exists() else 0,
            "ffplay_test": False,
            "ffprobe_test": False,
        }

        if not results["file_exists"]:
            results["error"] = "File does not exist"
            return results

        # Test with ffprobe (info extraction)
        try:
            cmd = ["ffprobe", "-v", "error", "-show_format", str(filepath)]
            result = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=5)
            results["ffprobe_test"] = result.returncode == 0
            if result.returncode != 0:
                results["ffprobe_error"] = result.stderr
        except Exception as e:
            results["ffprobe_error"] = str(e)

        # Test with ffplay (playback capability) - just validate, don't actually play
        try:
            cmd = ["ffplay", "-v", "error", "-f", "null", "-", "-i", str(filepath)]
            result = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=5)
            results["ffplay_test"] = result.returncode == 0
            if result.returncode != 0:
                results["ffplay_error"] = result.stderr
        except Exception as e:
            results["ffplay_error"] = str(e)

        logger.info(f"🔍 Audio test results for {filepath.name}: {results}")
        return results

    def get_session_summary(self) -> dict[str, Any]:
        """Get summary of current debugging session."""
        return {
            "session_id": self.session_id,
            "session_dir": str(self.session_dir),
            "total_files": len(list(self.session_dir.glob("*.wav"))),
            "total_log_entries": len(self.debug_log),
            "stages_tested": list(set(entry["stage"] for entry in self.debug_log)),
        }

    def generate_report(self) -> str:
        """Generate comprehensive debugging report."""
        summary = self.get_session_summary()

        report = f"""
# Audio Debugging Session Report
Session ID: {summary["session_id"]}
Session Directory: {summary["session_dir"]}

## Summary
- Total audio files saved: {summary["total_files"]}
- Pipeline stages tested: {", ".join(summary["stages_tested"])}
- Debug log entries: {summary["total_log_entries"]}

## Audio Files Analysis
"""

        for entry in self.debug_log:
            if "audio_info" in entry:
                info = entry["audio_info"]
                report += f"""
### {entry["stage"]} - {entry["filename"]}
- Size: {entry["size_bytes"]} bytes
- Duration: {info.get("duration", "unknown")}s
- Sample Rate: {info.get("sample_rate", "unknown")}Hz
- Channels: {info.get("channels", "unknown")}
- Codec: {info.get("codec_name", "unknown")}
- Text: "{entry["text"]}"
"""

        return report


# Global debugger instance
audio_debugger = AudioDebugger()
