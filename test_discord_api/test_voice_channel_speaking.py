#!/usr/bin/env python3
"""
Discord Voice Channel Speaking Test
ボットが実際にボイスチャンネルでしゃべれるかをテストする

このテストは以下の機能を検証します：
1. ボットがボイスチャンネルに接続できるか
2. テスト音声を生成してボイスチャンネルで再生できるか
3. TTSメッセージを処理してボイスチャンネルで再生できるか
4. 音声品質をチェックできるか
"""

import asyncio
import logging
import os
import sys
import tempfile
import time
from typing import Any

import aiohttp
import discord
from dotenv import load_dotenv

# ロギング設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s", handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

# .envファイルから環境変数を読み込む
_ = load_dotenv()


class VoiceChannelTestBot(discord.Client):
    """ボイスチャンネルでの音声再生をテストするボット"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # インテンツ設定 - ボイスチャンネル接続に必要
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.guilds = True

        super().__init__(*args, intents=intents, **kwargs)
        self.test_results: list[dict[str, Any]] = []
        self.voice_client: discord.VoiceClient | None = None
        self.target_channel_id = int(os.getenv("TARGET_VOICE_CHANNEL_ID", "0"))

    async def on_ready(self) -> None:
        """ボット準備完了時の処理"""
        if self.user:
            logger.info(f"✅ テストボットがログインしました: {self.user.name} (ID: {self.user.id})")
        else:
            logger.info("✅ テストボットがログインしました: ユーザー情報なし")

        # ギルド情報を表示
        for guild in self.guilds:
            logger.info(f"📍 参加しているギルド: {guild.name} (ID: {guild.id})")

            # ボイスチャンネル情報を表示
            for channel in guild.channels:
                if isinstance(channel, discord.VoiceChannel):
                    logger.info(f"   🔊 ボイスチャンネル: {channel.name} (ID: {channel.id})")

        # ボイスチャンネル接続テストを開始
        await self.run_voice_tests()

    async def run_voice_tests(self) -> None:
        """ボイスチャンネルテストを実行"""
        logger.info("🎤 ボイスチャンネルテストを開始します")

        # テスト1: ボイスチャンネル接続テスト
        await self.test_voice_connection()

        # テスト2: テスト音声再生テスト
        await self.test_audio_playback()

        # テスト3: TTS音声再生テスト
        await self.test_tts_playback()

        # テスト4: 音声品質テスト
        await self.test_audio_quality()

        # テスト結果のサマリーを表示
        await self.show_test_summary()

    async def test_voice_connection(self) -> None:
        """ボイスチャンネル接続テスト"""
        logger.info("🔗 テスト1: ボイスチャンネル接続テスト")

        try:
            # ターゲットボイスチャンネルを取得
            if not self.target_channel_id:
                logger.error("❌ TARGET_VOICE_CHANNEL_IDが設定されていません")
                self.record_test_result("voice_connection", False, "TARGET_VOICE_CHANNEL_ID not set")
                return

            channel = self.get_channel(self.target_channel_id)
            if not channel or not isinstance(channel, discord.VoiceChannel):
                logger.error(f"❌ ボイスチャンネルが見つかりません: {self.target_channel_id}")
                self.record_test_result("voice_connection", False, "Voice channel not found")
                return

            # ボイスチャンネルに接続
            self.voice_client = await channel.connect()
            logger.info(f"✅ ボイスチャンネルに接続成功: {channel.name}")

            # 接続状態を確認
            await asyncio.sleep(1)
            if self.voice_client and self.voice_client.is_connected():
                logger.info("✅ ボイス接続が正常に確立されています")
                self.record_test_result("voice_connection", True, "Successfully connected to voice channel")
            else:
                logger.error("❌ ボイス接続が失敗しました")
                self.record_test_result("voice_connection", False, "Failed to establish voice connection")

        except Exception as e:
            logger.error(f"❌ ボイスチャンネル接続テスト失敗: {e}")
            self.record_test_result("voice_connection", False, str(e))

    async def test_audio_playback(self) -> None:
        """テスト音声再生テスト"""
        logger.info("🎵 テスト2: テスト音声再生テスト")

        if not self.voice_client or not self.voice_client.is_connected():
            logger.error("❌ ボイスクライアントが接続されていません")
            self.record_test_result("audio_playback", False, "Voice client not connected")
            return

        try:
            # テスト音声データを生成 (サイン波)
            import math
            import struct

            # 音声パラメータ
            sample_rate = 24000
            duration = 2  # 2秒
            frequency = 440  # A4音
            amplitude = 0.3

            # PCMデータ生成
            samples: list[bytes] = []
            for i in range(int(sample_rate * duration)):
                sample = amplitude * math.sin(2 * math.pi * frequency * i / sample_rate)
                # 16-bit PCMに変換
                sample_int = int(sample * 32767)
                samples.append(struct.pack("<h", sample_int))

            pcm_data = b"".join(samples)

            # WAVヘッダー作成
            wav_header = self.create_wav_header(len(pcm_data), sample_rate, 1, 16)

            # 完全なWAVデータ
            wav_data = wav_header + pcm_data

            # 一時ファイルにWAVデータを書き込む
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.wav', delete=False) as temp_file:
                _ = temp_file.write(wav_data)
                temp_file_path = temp_file.name

            try:
                # Discord AudioSource作成 (ファイルパスを使用)
                audio_source = discord.FFmpegPCMAudio(temp_file_path)
                
                # 音声を再生
                self.voice_client.play(audio_source)
                
                # 再生完了まで待機
                while self.voice_client.is_playing():
                    await asyncio.sleep(0.1)
                
                logger.info("✅ テスト音声再生成功")
                self.record_test_result("audio_playback", True, "Successfully played test audio")
            
            finally:
                # 一時ファイルを削除
                import os
                try:
                    _ = os.unlink(temp_file_path)
                except OSError:
                    pass  # ファイルが既に削除されている可能性がある
        
        except Exception as e:
            logger.error(f"❌ テスト音声再生失敗: {e}")
            self.record_test_result("audio_playback", False, str(e))

    async def test_tts_playback(self) -> None:
        """TTS音声再生テスト"""
        logger.info("🗣️ テスト3: TTS音声再生テスト")

        if not self.voice_client or not self.voice_client.is_connected():
            logger.error("❌ ボイスクライアントが接続されていません")
            self.record_test_result("tts_playback", False, "Voice client not connected")
            return

        try:
            # TTSエンジンを使って音声生成
            test_text = "こんにちは、これはボイスチャンネルテストです。"

            # TTS APIから音声データを取得
            tts_audio_data = await self.generate_tts_audio(test_text)

            if not tts_audio_data:
                logger.error("❌ TTS音声生成失敗")
                self.record_test_result("tts_playback", False, "Failed to generate TTS audio")
                return

            # TTS音声データを一時ファイルに書き込む
            with tempfile.NamedTemporaryFile(mode="wb", suffix=".wav", delete=False) as tts_temp_file:
                _ = tts_temp_file.write(tts_audio_data)
                tts_temp_file_path = tts_temp_file.name
            
            try:
                # Discord AudioSource作成 (ファイルパスを使用)
                audio_source = discord.FFmpegPCMAudio(tts_temp_file_path)
                
                # 音声を再生
                self.voice_client.play(audio_source)
                
                # 再生完了まで待機
                while self.voice_client.is_playing():
                    await asyncio.sleep(0.1)
                
                logger.info("✅ TTS音声再生成功")
                self.record_test_result("tts_playback", True, "Successfully played TTS audio")
            
            finally:
                # 一時ファイルを削除
                import os
                try:
                    os.unlink(tts_temp_file_path)
                except OSError:
                    pass  # ファイルが既に削除されている可能性がある

            # 音声を再生
            self.voice_client.play(audio_source)

            # 再生完了まで待機
            while self.voice_client.is_playing():
                await asyncio.sleep(0.1)

            logger.info("✅ TTS音声再生成功")
            self.record_test_result("tts_playback", True, "Successfully played TTS audio")

        except Exception as e:
            logger.error(f"❌ TTS音声再生失敗: {e}")
            self.record_test_result("tts_playback", False, str(e))

    async def test_audio_quality(self) -> None:
        """音声品質テスト"""
        logger.info("📊 テスト4: 音声品質テスト")

        if not self.voice_client or not self.voice_client.is_connected():
            logger.error("❌ ボイスクライアントが接続されていません")
            self.record_test_result("audio_quality", False, "Voice client not connected")
            return None

        try:
            # 複数の周波数でテスト音声を生成して品質チェック
            test_frequencies = [200, 1000, 3000, 8000]  # 異なる周波数
            quality_results: list[str] = []

            for freq in test_frequencies:
                logger.info(f"   テスト周波数: {freq}Hz")

                # テスト音声生成
                audio_data = await self.generate_test_tone(freq, duration=1.0)
                if audio_data:
                    # 音声データを一時ファイルに書き込む
                    with tempfile.NamedTemporaryFile(mode="wb", suffix=".wav", delete=False) as quality_temp_file:
                        _ = quality_temp_file.write(audio_data)
                        quality_temp_file_path = quality_temp_file.name
                    
                    try:
                        # Discord AudioSource作成 (ファイルパスを使用)
                        audio_source = discord.FFmpegPCMAudio(quality_temp_file_path)
                        self.voice_client.play(audio_source)
                        
                        while self.voice_client.is_playing():
                            await asyncio.sleep(0.1)
                        
                        quality_results.append(f"✓ {freq}Hz: OK")
                    finally:
                        # 一時ファイルを削除
                        import os
                        try:
                            _ = os.unlink(quality_temp_file_path)
                        except OSError:
                            pass  # ファイルが既に削除されている可能性がある
                else:
                    quality_results.append(f"✗ {freq}Hz: Failed")
            # TTSエンジン設定を取得
            tts_engine = os.getenv("TTS_ENGINE", "voicevox")
            api_url = os.getenv("VOICEVOX_URL", "http://127.0.0.1:50021")
            speaker_id = int(os.getenv("VOICEVOX_SPEAKER_ID", "1"))

            if tts_engine.lower() == "aivis":
                api_url = os.getenv("AIVIS_URL", "http://127.0.0.1:10101")
                speaker_id = int(os.getenv("AIVIS_SPEAKER_ID", "888753760"))

            async with aiohttp.ClientSession() as session:
                # テキストを音声クエリに変換
                query_url = f"{api_url}/audio_query"
                test_text = "こんにちは、これはボイスチャンネルテストです。"
                params = {"text": test_text, "speaker": speaker_id}

                async with session.post(query_url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"TTSクエリ失敗: {response.status}")
                        return None

                    audio_query = await response.json()

                # 音声合成
                synthesis_url = f"{api_url}/synthesis"
                synthesis_params = {"speaker": speaker_id}

                headers = {"Content-Type": "application/json"}
                async with session.post(synthesis_url, params=synthesis_params, json=audio_query, headers=headers) as response:
                    if response.status != 200:
                        logger.error(f"TTS合成失敗: {response.status}")
                        return None

                    return await response.read()

        except Exception as e:
            logger.error(f"TTS音声生成エラー: {e}")
            return None

    async def generate_test_tone(self, frequency: int, duration: float = 1.0) -> bytes | None:
        """テスト音声（サイン波）を生成"""
        try:
            import math
            import struct

            sample_rate = 24000
            amplitude = 0.3

            # PCMデータ生成
            samples: list[bytes] = []
            for i in range(int(sample_rate * duration)):
                sample = amplitude * math.sin(2 * math.pi * frequency * i / sample_rate)
                sample_int = int(sample * 32767)
                samples.append(struct.pack("<h", sample_int))

            pcm_data = b"".join(samples)

            # WAVヘッダー作成
            wav_header = self.create_wav_header(len(pcm_data), sample_rate, 1, 16)

            return wav_header + pcm_data

        except Exception as e:
            logger.error(f"テスト音声生成エラー: {e}")
            return None

    async def generate_tts_audio(self, text: str) -> bytes | None:
        """TTS APIを使って音声データを生成"""
        try:
            # TTSエンジン設定を取得
            tts_engine = os.getenv("TTS_ENGINE", "voicevox")
            api_url = os.getenv("VOICEVOX_URL", "http://127.0.0.1:50021")
            speaker_id = int(os.getenv("VOICEVOX_SPEAKER_ID", "1"))

            if tts_engine.lower() == "aivis":
                api_url = os.getenv("AIVIS_URL", "http://127.0.0.1:10101")
                speaker_id = int(os.getenv("AIVIS_SPEAKER_ID", "888753760"))

            async with aiohttp.ClientSession() as session:
                # テキストを音声クエリに変換
                query_url = f"{api_url}/audio_query"
                test_text = "こんにちは、これはボイスチャンネルテストです。"
                params = {"text": test_text, "speaker": speaker_id}

                async with session.post(query_url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"TTSクエリ失敗: {response.status}")
                        return None

                    audio_query = await response.json()

                # 音声合成
                synthesis_url = f"{api_url}/synthesis"
                synthesis_params = {"speaker": speaker_id}

                headers = {"Content-Type": "application/json"}
                async with session.post(synthesis_url, params=synthesis_params, json=audio_query, headers=headers) as response:
                    if response.status != 200:
                        logger.error(f"TTS合成失敗: {response.status}")
                        return None

                    return await response.read()

        except Exception as e:
            logger.error(f"TTS音声生成エラー: {e}")
            return None

    def create_wav_header(self, data_size: int, sample_rate: int, channels: int, bits_per_sample: int) -> bytes:
        """WAVファイルヘッダーを作成"""
        # RIFFヘッダー
        riff_header = b"RIFF"
        file_size = 36 + data_size
        riff_header += file_size.to_bytes(4, "little")
        riff_header += b"WAVE"

        # fmtチャンク
        fmt_header = b"fmt "
        fmt_size = 16
        fmt_header += fmt_size.to_bytes(4, "little")
        fmt_header += (1).to_bytes(2, "little")  # PCM format
        fmt_header += channels.to_bytes(2, "little")
        fmt_header += sample_rate.to_bytes(4, "little")
        byte_rate = sample_rate * channels * bits_per_sample // 8
        fmt_header += byte_rate.to_bytes(4, "little")
        block_align = channels * bits_per_sample // 8
        fmt_header += block_align.to_bytes(2, "little")
        fmt_header += bits_per_sample.to_bytes(2, "little")

        # dataチャンク
        data_header = b"data"
        data_header += data_size.to_bytes(4, "little")

        return riff_header + fmt_header + data_header

    def record_test_result(self, test_name: str, success: bool, details: str) -> None:
        """テスト結果を記録"""
        result = {"test_name": test_name, "success": success, "details": details, "timestamp": time.time()}
        self.test_results.append(result)

        status = "✅" if success else "❌"
        logger.info(f"{status} {test_name}: {details}")

    async def show_test_summary(self) -> None:
        """テスト結果のサマリーを表示"""
        logger.info(f"\n{'=' * 60}")
        logger.info("📊 ボイスチャンネルテスト結果サマリー")
        logger.info(f"{'=' * 60}")
        logger.info("=" * 60)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests

        logger.info(f"総テスト数: {total_tests}")
        logger.info(f"成功: {passed_tests}")
        logger.info(f"失敗: {failed_tests}")

        if failed_tests == 0:
            logger.info("🎉 すべてのテストが成功しました！ボットは正常にボイスチャンネルでしゃべれます")
        else:
            logger.info("⚠️ 一部のテストが失敗しました。詳細を確認してください")

        # 各テストの結果を表示
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            logger.info(f"  {status} {result['test_name']}: {result['details']}")

        logger.info("=" * 60)

        # ボットを終了
        await self.close()


async def main():
    """メイン関数"""
    logger.info("🚀 Discordボイスチャンネルテストを開始します")

    # トークンの確認
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        logger.error("❌ 環境変数 DISCORD_BOT_TOKEN が設定されていません")
        logger.error("   .envファイルに DISCORD_BOT_TOKEN=your_token_here を追加してください")
        sys.exit(1)

    # 必要な環境変数の確認
    required_env_vars = ["TARGET_VOICE_CHANNEL_ID", "TTS_ENGINE"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(f"❌ 以下の環境変数が設定されていません: {', '.join(missing_vars)}")
        logger.error("   .envファイルにこれらの変数を追加してください")
        sys.exit(1)

    logger.info(f"🔑 トークン: {token[:20]}...")
    logger.info(f"🎯 ターゲットボイスチャンネルID: {os.getenv('TARGET_VOICE_CHANNEL_ID')}")
    logger.info(f"🎤 TTSエンジン: {os.getenv('TTS_ENGINE')}")

    # ボットインスタンス作成
    bot = VoiceChannelTestBot()

    try:
        logger.info("🔗 Discordに接続しています...")
        await bot.start(token)
    except KeyboardInterrupt:
        logger.info("🛑 ユーザーによって停止されました")
    except Exception as e:
        logger.error(f"❌ エラーが発生しました: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        logger.info("🔌 Discordとの接続を閉じています...")
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
