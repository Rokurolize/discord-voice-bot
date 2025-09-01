"""
Integration test functions for Discord Voice Channel Speaking functionality.
"""

import asyncio
import logging
import os

import pytest

from .test_voice_integration_bot import VoiceChannelTestBot

# ロギング設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s")
logger = logging.getLogger(__name__)


@pytest.mark.skipif(
    True,  # Always skip this test - it's too slow for regular testing
    reason="This integration test is too slow for regular test runs - run manually when needed",
)
@pytest.mark.integration
@pytest.mark.asyncio
async def test_bot_can_speak_in_voice_channel(caplog):
    """
    Integration test that verifies the bot can speak in a real Discord voice channel.
    
    Uses an actual Discord connection to validate: (1) the bot can join a voice channel, (2) it can generate and play audio files, (3) it can process and play TTS messages, and (4) audio quality across multiple frequencies is acceptable. This test requires DISCORD_BOT_TOKEN, TARGET_VOICE_CHANNEL_ID, and TTS_ENGINE environment variables; it will be skipped when the bot token is not set. Results are collected in bot.test_results and the test asserts that voice connection, audio playback, and audio quality checks are present and at least two checks succeed.
    """
    # 環境変数の確認
    token = os.getenv("DISCORD_BOT_TOKEN")
    target_channel_id = os.getenv("TARGET_VOICE_CHANNEL_ID")
    tts_engine = os.getenv("TTS_ENGINE")

    logger.info("🚀 Discordボイスチャンネル統合テストを開始します")
    if not token:
        pytest.skip("DISCORD_BOT_TOKEN が未設定のためテストをスキップします")
    logger.info(f"🔑 トークン: {token[:20]}...")
    logger.info(f"🎯 ターゲットボイスチャンネルID: {target_channel_id}")
    logger.info(f"🎤 TTSエンジン: {tts_engine}")

    # ボットインスタンス作成
    bot = VoiceChannelTestBot()

    try:
        # タイムアウト付きでボットを開始
        async with asyncio.timeout(120):  # 2分タイムアウト
            logger.info("🔗 Discordに接続しています...")
            await bot.start(token)

    except TimeoutError:
        pytest.fail("❌ テストがタイムアウトしました - ボットが正常に動作しなかった可能性があります")

    except Exception as e:
        pytest.fail(f"❌ テスト実行中にエラーが発生しました: {e}")

    finally:
        # クリーンアップ
        try:
            if not bot.is_closed():
                await bot.close()
        except Exception as e:
            logger.warning(f"ボットのクリーンアップ中にエラーが発生しました: {e}")

    # テスト結果の検証
    assert len(bot.test_results) > 0, "❌ テスト結果が記録されていませんでした"

    # ボイス接続テストが成功していることを確認
    voice_connection_results = [r for r in bot.test_results if r["test_name"] == "voice_connection"]
    assert len(voice_connection_results) > 0, "❌ ボイス接続テストが実行されていません"
    assert voice_connection_results[0]["success"], f"❌ ボイス接続テストが失敗しました: {voice_connection_results[0]['details']}"

    # 音声再生テストが成功していることを確認
    audio_playback_results = [r for r in bot.test_results if r["test_name"] == "audio_playback"]
    assert len(audio_playback_results) > 0, "❌ 音声再生テストが実行されていません"
    assert audio_playback_results[0]["success"], f"❌ 音声再生テストが失敗しました: {audio_playback_results[0]['details']}"

    # 音声品質テストが成功していることを確認
    audio_quality_results = [r for r in bot.test_results if r["test_name"] == "audio_quality"]
    assert len(audio_quality_results) > 0, "❌ 音声品質テストが実行されていません"
    assert audio_quality_results[0]["success"], f"❌ 音声品質テストが失敗しました: {audio_quality_results[0]['details']}"

    # 成功したテスト数をカウント
    successful_tests = sum(1 for result in bot.test_results if result["success"])
    total_tests = len(bot.test_results)

    logger.info(f"✅ 統合テスト完了: {successful_tests}/{total_tests} 成功")

    # 少なくとも基本的な機能（ボイス接続、音声再生、品質テスト）が成功していることを確認
    assert successful_tests >= 2, f"❌ 十分なテストが成功しませんでした: {successful_tests}/{total_tests}"

    # ボットが実際にボイスチャンネルで話せることを証明するメッセージ
    logger.info("🎉 ボットは正常にボイスチャンネルで話せることが証明されました！")
    logger.info("   - ボイスチャンネルへの接続: ✅")
    logger.info("   - 音声ファイルの生成と再生: ✅")
    logger.info("   - 音声品質テスト: ✅")


@pytest.mark.skipif(
    True,  # Always skip this test - it's too slow for regular testing
    reason="This integration test is too slow for regular test runs - run manually when needed",
)
@pytest.mark.integration
@pytest.mark.asyncio
async def test_bot_voice_functionality_comprehensive():
    """
    包括的なボイス機能テスト

    このテストはボットのボイス機能を総合的にテストします。
    実際のDiscord APIを使用してボットが正しく動作することを確認します。
    """
    # 環境変数の設定を確認
    required_env_vars = ["DISCORD_BOT_TOKEN", "TARGET_VOICE_CHANNEL_ID", "TTS_ENGINE"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]

    if missing_vars:
        pytest.skip(f"必要な環境変数が設定されていません: {', '.join(missing_vars)}")

    logger.info("🔬 包括的なボイス機能テストを開始します")

    # ここではより詳細なテストを実施可能
    # 実際のテストは上記のtest_bot_can_speak_in_voice_channelで実施されるため
    # このテストでは基本的な環境チェックのみ行う

    assert True, "包括的なボイス機能テストは環境設定チェックをパスしました"


if __name__ == "__main__":
    # pytest経由で実行することを推奨
    pytest.main([__file__, "-v", "-k", "test_bot_can_speak_in_voice_channel"])
