#!/bin/bash

# Discord API メッセージ内容取得テスト実行スクリプト

echo "🚀 Discord API メッセージ内容取得テストを開始します"
echo ""

# .envファイルの存在確認
if [ ! -f ".env" ]; then
    echo "❌ .envファイルが見つかりません"
    echo "   .env.example をコピーして .env を作成してください"
    echo "   cp .env.example .env"
    echo "   その後、DISCORD_BOT_TOKEN を設定してください"
    exit 1
fi

# 環境変数の確認
if ! grep -q "DISCORD_BOT_TOKEN=your_bot_token_here" .env; then
    echo "✅ .envファイルにトークンが設定されているようです"
else
    echo "❌ .envファイルのDISCORD_BOT_TOKENが設定されていません"
    echo "   .envファイルを編集してトークンを設定してください"
    exit 1
fi

echo "📦 依存関係をインストールします..."
pip install -r requirements.txt

echo ""
echo "🔧 テストボットを起動します..."
echo "   テストボットが起動したら、Discordでメッセージを送信してください"
echo "   Ctrl+C で停止できます"
echo ""

python test_message_content.py
