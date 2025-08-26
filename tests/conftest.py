from unittest.mock import MagicMock

import pytest

from discord_voice_bot.config import Config  # 本物のConfigクラスをインポート


@pytest.fixture(autouse=True)
def mock_config_get(monkeypatch: pytest.MonkeyPatch):
    """
    Automatically patches get_config() for each test to return a fresh MagicMock.
    Each test gets an isolated mock instance.
    """
    # 1. 偽物のConfigオブジェクト（モック）を1つだけ作る
    # spec=Config で、本物そっくりな賢い偽物にするのを忘れないでね！
    mock_instance = MagicMock(spec=Config)

    # 2. テストで共通して使う、基本的な値を設定しておく
    mock_instance.discord_token = "test_token_from_conftest"
    mock_instance.target_voice_channel_id = 1234567890
    mock_instance.tts_engine = "voicevox"
    mock_instance.log_level = "DEBUG"
    mock_instance.rate_limit_messages = 5
    mock_instance.rate_limit_period = 60
    # ... 他の必要な設定もここに追加！

    # 3. これが一番大事な魔法！
    # 'discord_voice_bot.config.get_config' という名前の関数を、
    # いつでもさっき作った偽物を返すだけの単純な関数にすり替える
    monkeypatch.setattr("discord_voice_bot.config.get_config", lambda: mock_instance)

    # 4. この偽物を他のテストでも使えるように、一応返しておく
    # これで、テスト関数でこのフィクスチャを要求すれば、設定をイジれるようになるよ
    return mock_instance
