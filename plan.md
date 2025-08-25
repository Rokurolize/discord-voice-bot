# テスト失敗問題の解決計画

## 問題の詳細

現在の `uv run poe check` 実行で、以下の3つのテストが失敗している：

### 1. `test_bot_can_speak_in_voice_channel`
- **エラー**: "Voice channel not found"
- **原因**: `.env` ファイルの `TARGET_VOICE_CHANNEL_ID` が無効なIDだった
- **修正済み**: IDを `1391964875600822366` から `1350964414286921749` に変更

### 2. `test_fixed_behavior_allows_self_messages`
- **エラー**: "Fixed implementation should allow self-messages"
- **原因**: 自己メッセージ処理のロジックが正しくない
- **詳細**: メッセージのオーソーがボット自身の場合でも、フィルタリングが失敗している

### 3. `test_workers_process_queue_items_fixed`
- **エラー**: "Audio was not queued after synthesis"
- **原因**: SynthesizerWorker が音声を生成しているのに、audio queue に追加されていない
- **詳細**: ログに "Synthesized chunk 1/1 (size: 1004 bytes)" とあるが、audio queue が空のまま

## やるべきこと

### 優先度1: 自己メッセージ処理の修正
1. `src/discord_voice_bot/message_processor.py` を調査
2. `should_process_message` メソッドのロジックを確認
3. 自己メッセージ（`message.author.id == bot.user.id`）の処理を修正

### 優先度2: 合成ワーカーの修正
1. `src/discord_voice_bot/voice/workers/synthesizer.py` を調査
2. `run` メソッドで音声を生成した後の処理を確認
3. audio queue にアイテムを追加するロジックを修正

### 優先度3: テストの再実行と確認
1. 修正後に `uv run poe check` を実行
2. すべてのテストが通ることを確認
3. 必要に応じて追加のログを追加

## 現在の状態
- ボイスチャンネルIDの修正は完了
- 残り2つのテスト失敗を修正する必要がある
- デバッグモードで系統的に問題を解決中

マスター、これで問題の整理は合っているかな？ 修正を始める前に確認してほしいな♡