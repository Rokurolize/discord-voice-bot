# Discord API メッセージ内容取得テスト

このテストコードは、Discord.pyでメッセージ内容が正しく取得できるかを確認するための最小限のボットです。

## 問題の背景

現在のDiscord Voice TTSボットで、ユーザーがメッセージを送信しているのにボットが空のメッセージとして受信している問題があります。このテストで、問題がDiscord APIの権限設定にあるのか、それともコードの実装にあるのかを特定します。

## セットアップ

### 1. 環境変数の設定

```bash
# .env.example をコピーして .env を作成
cp .env.example .env
```

`.env`ファイルを編集して、Discord Bot Tokenを設定してください：

```env
DISCORD_BOT_TOKEN=your_bot_token_here
```

### 2. Discord Bot Tokenの取得

1. [Discord Developer Portal](https://discord.com/developers/applications) にアクセス
2. 新しいアプリケーションを作成するか、既存のものを選択
3. `Bot`セクションに移動
4. `Token`の下にある `Reset Token` をクリックしてトークンを取得
5. トークンを `.env` ファイルに設定

### 3. 権限設定（重要）

Discord Developer Portalで以下の設定を確認してください：

1. **Botの権限設定**:
   - `Read Messages` ✅
   - `Read Message History` ✅
   - `Message Content Intent` ✅ (重要！)

2. **インテンツ設定**:
   - `Message Content Intent` を有効化

## 使用方法

### テストの実行

```bash
# 依存関係のインストール
pip install -r requirements.txt

# テストボットの実行
python test_message_content.py
```

### テストの手順

1. テストボットを起動
2. Discordでテストボットと同じチャンネルにメッセージを送信
3. ボットのログを確認
4. メッセージ内容が正しく取得できているか確認

### 期待される結果

**正常な場合**:
```
📨 新しいメッセージを受信しました
message.content: 'こんにちは、テストです'
message.content 長さ: 11
```

**問題がある場合**:
```
📨 新しいメッセージを受信しました
message.content: ''
message.content 長さ: 0
```

## 結果の解釈

### メッセージ内容が取得できる場合
- Discord APIの権限設定は正しい
- 問題は現在のボットのコード実装にある可能性が高い

### メッセージ内容が取得できない場合
- Discord APIの権限設定に問題がある
- Message Content Intentが有効になっていない

## テスト結果の保存

テスト結果は `test_results.json` ファイルに保存されます：

```json
{
  "author": "ユーザー名",
  "content": "メッセージ内容",
  "content_length": 8,
  "message_id": "1234567890123456789",
  "channel_id": "1234567890123456789",
  "timestamp": "2025-08-24T01:43:32.652000+00:00",
  "is_bot": false
}
```

## トラブルシューティング

### よくある問題

1. **トークンが設定されていない**
   ```
   ❌ 環境変数 DISCORD_BOT_TOKEN が設定されていません
   ```
   → `.env`ファイルにトークンを設定してください

2. **権限が不足している**
   ```
   message.content: ''
   ```
   → Discord Developer PortalでMessage Content Intentを有効化してください

3. **ボットがチャンネルに参加していない**
   → ボットを対象のチャンネルに招待してください

## 次のステップ

テスト結果に基づいて：

- メッセージ内容が取得できる場合 → 現在のボットのコード実装を修正
- メッセージ内容が取得できない場合 → Discord APIの権限設定を修正
