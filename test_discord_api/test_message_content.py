#!/usr/bin/env python3
"""
Discord API メッセージ内容取得テスト
Discord.py でメッセージの内容が正しく取得できるかをテストする最小限のコード
"""

import asyncio
import logging
import os
import sys
from typing import Any

import discord
from dotenv import load_dotenv

# ロギング設定
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s", handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

# .envファイルから環境変数を読み込む
_ = load_dotenv()


class TestBot(discord.Client):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # インテンツ設定 - メッセージ内容を取得するために必要
        intents = discord.Intents.default()
        intents.message_content = True  # 重要：メッセージ内容を取得する
        intents.voice_states = True
        intents.guilds = True

        super().__init__(*args, intents=intents, **kwargs)
        self.test_messages_received: list[dict[str, Any]] = []

    async def on_ready(self) -> None:
        if self.user:
            logger.info(f"✅ テストボットがログインしました: {self.user.name} (ID: {self.user.id})")
        else:
            logger.info("✅ テストボットがログインしました: ユーザー情報なし")
        logger.info(f"🔍 インテンツ設定: message_content = {self.intents.message_content}")

        # ギルド情報を表示
        for guild in self.guilds:
            logger.info(f"📍 参加しているギルド: {guild.name} (ID: {guild.id})")

            # チャンネル情報を表示
            for channel in guild.channels:
                if isinstance(channel, discord.TextChannel):
                    logger.info(f"   📝 テキストチャンネル: {channel.name} (ID: {channel.id})")

    async def on_message(self, message: discord.Message) -> None:
        """メッセージ受信時の処理"""
        logger.info("=" * 60)
        logger.info("📨 新しいメッセージを受信しました")
        logger.info("=" * 60)

        # メッセージの詳細情報を表示
        logger.info(f"👤 送信者: {message.author.name} (ID: {message.author.id})")
        channel_name = getattr(message.channel, "name", "Unknown")
        logger.info(f"📍 チャンネル: {channel_name} (ID: {message.channel.id})")
        logger.info(f"🏠 ギルド: {message.guild.name if message.guild else 'DM'}")
        logger.info(f"📝 メッセージID: {message.id}")
        logger.info(f"📅 タイムスタンプ: {message.created_at}")
        logger.info(f"🤖 ボットメッセージ: {message.author.bot}")

        # メッセージ内容の詳細な調査
        logger.info("-" * 40)
        logger.info("🔍 メッセージ内容の詳細調査")
        logger.info("-" * 40)

        # 様々な方法でメッセージ内容を取得してみる
        logger.info(f"message.content: '{message.content}'")
        logger.info(f"message.content 長さ: {len(message.content)}")
        logger.info(f"message.content repr: {message.content!r}")
        logger.info(f"message.content type: {type(message.content)}")

        # メッセージオブジェクトの属性を確認
        logger.info(f"message.type: {message.type}")
        logger.info(f"message.tts: {message.tts}")

        # 添付ファイルの確認
        logger.info(f"添付ファイル数: {len(message.attachments)}")

        # 埋め込みの確認
        logger.info(f"埋め込み数: {len(message.embeds)}")

        # システムメッセージかどうかの確認
        logger.info(f"システムメッセージ: {message.is_system()}")

        # メッセージの属性一覧
        logger.info(f"message.__dict__ keys: {list(message.__dict__.keys())}")

        # 生のメッセージデータの確認（型チェックを回避するためコメントアウト）
        # try:
        #     logger.info("🔧 生のメッセージデータを確認")
        #     # Discord.pyの内部データにアクセス（プライベート属性）
        #     if hasattr(message, "_data"):
        #         data_dict = getattr(message, "_data", {})
        #         if isinstance(data_dict, dict):
        #             logger.info(f"message._data keys: {list(data_dict.keys())}")
        #             if "content" in data_dict:
        #                 logger.info(f"生データ content: {data_dict['content']!r}")
        # except Exception as e:
        #     logger.error(f"生データ確認エラー: {e}")

        # テスト結果を保存
        test_result = {
            "author": message.author.name,
            "content": message.content,
            "content_length": len(message.content),
            "message_id": message.id,
            "channel_id": message.channel.id,
            "timestamp": message.created_at.isoformat(),
            "is_bot": message.author.bot,
        }

        self.test_messages_received.append(test_result)

        # 結果をファイルに保存
        with open("/home/ubuntu/workbench/projects/discord-voice-bot/test_discord_api/test_results.json", "a", encoding="utf-8") as f:
            import json

            _ = f.write(json.dumps(test_result, ensure_ascii=False) + "\n")

        logger.info("=" * 60)
        logger.info("✅ メッセージ処理完了")
        logger.info("=" * 60)

        # 自分自身のメッセージは無視
        if message.author == self.user:
            return

        # テストメッセージに対する応答
        if message.content and len(message.content.strip()) > 0:
            response = f"✅ メッセージを受信しました！\n内容: '{message.content}'\n長さ: {len(message.content)}文字"
            _ = await message.channel.send(response)
        else:
            response = "❌ メッセージ内容が空でした。Discord APIの権限設定を確認してください。"
            _ = await message.channel.send(response)


async def main():
    """メイン関数"""
    logger.info("🚀 Discord API メッセージ内容取得テストを開始します")

    # トークンの確認
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        logger.error("❌ 環境変数 DISCORD_BOT_TOKEN が設定されていません")
        logger.error("   .envファイルに DISCORD_BOT_TOKEN=your_token_here を追加してください")
        sys.exit(1)

    logger.info(f"🔑 トークン: {token[:20]}...")

    # ボットインスタンス作成
    bot = TestBot()

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

        # テスト結果のサマリー
        logger.info("=" * 60)
        logger.info("📊 テスト結果サマリー")
        logger.info("=" * 60)

        total_messages = len(bot.test_messages_received)
        empty_messages = sum(1 for msg in bot.test_messages_received if msg["content_length"] == 0)

        logger.info(f"受信したメッセージ総数: {total_messages}")
        logger.info(f"空のメッセージ数: {empty_messages}")

        if total_messages > 0:
            success_rate = ((total_messages - empty_messages) / total_messages) * 100
            logger.info(f"メッセージ内容取得成功率: {success_rate:.1f}%")

            if empty_messages > 0:
                logger.warning("⚠️ 空のメッセージが検出されました。Discord APIの権限設定を確認してください。")
            else:
                logger.info("✅ すべてのメッセージ内容が正常に取得できました！")

        logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
