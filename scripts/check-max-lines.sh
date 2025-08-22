#!/usr/bin/env bash
set -euo pipefail

LIMIT=500
FAILED=0

# pre-commit から渡されたステージ対象ファイルをチェック
#（types: [text] によりテキストのみが渡される想定）
for file in "$@"; do
  # ファイルが存在しない（削除など）場合はスキップ
  [[ -f "$file" ]] || continue

  # 行数カウント（CRLFも問題なく数えられる）
  # 空ファイルは 0 行
  lines=$(wc -l < "$file" | tr -d ' ')
  # wc の仕様で空だと空文字になることがあるので 0 に補正
  : "${lines:=0}"

  if [[ "$lines" -gt "$LIMIT" ]]; then
    echo "❌ ${file}: ${lines} 行（上限 ${LIMIT} 行）→ コミットをブロックします。"
    FAILED=1
  fi
done

exit "$FAILED"
