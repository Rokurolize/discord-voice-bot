# TODO (本タスク用)

進め方: チェックボックスで進捗管理します。完了時は [x] に変更。

## ブランチ運用
- [x] 新規ブランチ作成（`chore/task-todo-setup`）
- [ ] 最終反映用ブランチ命名を確定（例: `feat/discordpy-alignment`）

## コマンド/スラッシュ整理
- [ ] 旧 `slash_command_handler.py` の段階的撤去方針を決定
- [ ] `slash/` 配下を `app_commands`/`bot.tree` ベースに統一する設計
- [ ] 代表ハンドラをハイブリッド化（必要に応じて `@bot.hybrid_command`）
- [ ] 移行の最小パス（互換 alias／deprecated log）の提示

## レート制御の標準化
- [ ] コマンドのクールダウンを `app_commands.checks.cooldown` / `commands.cooldown` に移行
- [ ] Discord API 呼び出しのレートはライブラリに委譲（独自は TTS API限定）

## イベントハンドリング簡素化（任意）
- [ ] `event_handler` 経由の単純委譲を Cog 直実装に集約する案の評価
- [ ] 重要イベントのみ委譲層を残す（可観測性・分離の観点）

## Voice 層見直し（中期）
- [ ] `VoiceConnectionManager` で `VoiceChannel.connect()`/`Guild.voice_client` を標準経路に寄せる
- [ ] `NullVoiceClient` の利用箇所棚卸し（`None`/guard で代替可能か）
- [ ] 必要なら `VoiceProtocol`/`connect(cls=...)` の正攻法拡張

## ログ/ステータス整備
- [ ] `discord.utils.setup_logging`/`client.run(log_handler=...)` の採用要否を決定
- [ ] stats のレガシー互換層の deprecate 計画（`StatsTracker` に収束）

## テスト/CI
- [ ] 変更点に対する単体/統合テストの追加
- [ ] `poe check` がローカルでグリーンになることを確認
- [ ] PR 説明に移行背景と差分の根拠（公式 docs）を添付

