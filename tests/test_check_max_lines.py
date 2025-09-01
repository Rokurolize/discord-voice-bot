"""
Tests for the max-lines pre-commit bash script.

Testing library and framework: pytest (Python)
- We use pytest's tmp_path fixture and subprocess for invoking the script.
- We intentionally write the script to a temporary path inside each test to avoid coupling to repo layout.

The tests focus on behaviors visible in the diff:
- LIMIT=500 enforcement
- Exceptions list: ("uv.lock", "gh-review-threads.sh")
- Accurate line counting including CRLF
- Handling of empty and nonexistent files
- Aggregation of failures across multiple inputs
"""

import stat
import subprocess
from collections.abc import Iterable
from pathlib import Path

SCRIPT_CONTENT = """#!/usr/bin/env bash
set -euo pipefail

LIMIT=500
FAILED=0

# 例外ファイルリスト（行数制限のチェックから除外するファイル）
EXCEPTIONS=("uv.lock" "gh-review-threads.sh")

# pre-commit から渡されたステージ対象ファイルをチェック
#（types: [text] によりテキストのみが渡される想定）
for file in "$@"; do
  # ファイルが存在しない（削除など）場合はスキップ
  [[ -f "$file" ]] || continue

  # 例外ファイルの場合はチェックをスキップ
  filename=$(basename "$file")
  # Check exceptions by exact match to avoid regex/glob pitfalls
  skip=false
  for ex in "${EXCEPTIONS[@]}"; do
    if [[ "$filename" == "$ex" ]]; then
      skip=true
      break
    fi
  done
  if [[ "$skip" == true ]]; then
    echo "⏭️ ${file}: 例外ファイルのためチェックをスキップします。"
    continue
  fi

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
"""

def _write_script(path: Path) -> Path:
    path.write_text(SCRIPT_CONTENT, encoding="utf-8")
    # Make executable
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path

def _make_text_file(path: Path, lines: int, crlf: bool = False) -> Path:
    # When lines == 0, create an empty file
    if lines == 0:
        path.write_bytes(b"")
        return path

    # Build content using actual newline characters and control them via open(..., newline="")
    sep = "\r\n" if crlf else "\n"
    content = sep.join(str(i) for i in range(1, lines + 1)) + sep
    with path.open(mode="w", encoding="utf-8", newline="") as f:
        f.write(content)
    return path

def _run(script: Path, args: Iterable[Path]) -> tuple[int, str, str]:
    proc = subprocess.run(
        [str(script), *[str(a) for a in args]],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr

def test_under_limit_exits_zero_and_emits_no_error(tmp_path: Path):
    script = _write_script(tmp_path / "check_max_lines.sh")
    f = _make_text_file(tmp_path / "small.txt", lines=10)
    code, out, err = _run(script, [f])
    assert code == 0
    assert "❌" not in out
    assert err == ""

def test_over_limit_exits_one_and_reports_file(tmp_path: Path):
    script = _write_script(tmp_path / "check_max_lines.sh")
    f = _make_text_file(tmp_path / "big.txt", lines=501)
    code, out, err = _run(script, [f])
    assert code == 1
    # Expect exact message per script formatting
    expected = f"❌ {f}: 501 行（上限 500 行）→ コミットをブロックします。"
    # Normalize line endings from echo
    lines = [line.strip() for line in out.strip().splitlines()]
    assert expected in lines
    assert err == ""

def test_empty_file_count_is_zero(tmp_path: Path):
    script = _write_script(tmp_path / "check_max_lines.sh")
    f = _make_text_file(tmp_path / "empty.txt", lines=0)
    code, out, err = _run(script, [f])
    assert code == 0
    assert out.strip() == ""
    assert err == ""

def test_nonexistent_file_is_safely_ignored(tmp_path: Path):
    script = _write_script(tmp_path / "check_max_lines.sh")
    missing = tmp_path / "does_not_exist.txt"
    code, out, err = _run(script, [missing])
    assert code == 0
    assert out.strip() == ""
    assert err == ""

def test_exception_file_is_skipped_even_if_large(tmp_path: Path):
    script = _write_script(tmp_path / "check_max_lines.sh")
    # Create files with names in EXCEPTIONS
    uv_lock = _make_text_file(tmp_path / "uv.lock", lines=2000)
    gh_script = _make_text_file(tmp_path / "gh-review-threads.sh", lines=2000)
    code, out, err = _run(script, [uv_lock, gh_script])
    assert code == 0
    outs = [line.strip() for line in out.strip().splitlines() if line.strip()]
    assert f"⏭️ {uv_lock}: 例外ファイルのためチェックをスキップします。" in outs
    assert f"⏭️ {gh_script}: 例外ファイルのためチェックをスキップします。" in outs
    assert err == ""

def test_multiple_files_mixed_results_returns_failure_if_any_violate(tmp_path: Path):
    script = _write_script(tmp_path / "check_max_lines.sh")
    ok1 = _make_text_file(tmp_path / "ok1.txt", lines=100)
    ok2 = _make_text_file(tmp_path / "ok2.txt", lines=500)
    bad = _make_text_file(tmp_path / "bad.txt", lines=750)
    code, out, err = _run(script, [ok1, bad, ok2])
    assert code == 1
    assert f"❌ {bad}: 750 行（上限 500 行）→ コミットをブロックします。" in out
    # Ensure no false positives on OK files
    assert "ok1.txt" not in out
    assert "ok2.txt" not in out
    assert err == ""

def test_counts_crlf_lines_correctly(tmp_path: Path):
    script = _write_script(tmp_path / "check_max_lines.sh")
    # Create CRLF terminated file with 20 lines (below limit)
    crlf_ok = _make_text_file(tmp_path / "crlf_ok.txt", lines=20, crlf=True)
    code, out, err = _run(script, [crlf_ok])
    assert code == 0
    assert out.strip() == ""
    # Now create a CRLF file just over the limit
    crlf_bad = _make_text_file(tmp_path / "crlf_bad.txt", lines=501, crlf=True)
    code2, out2, err2 = _run(script, [crlf_bad])
    assert code2 == 1
    assert f"❌ {crlf_bad}: 501 行（上限 500 行）→ コミットをブロックします。" in out2
    assert err == "" and err2 == ""

def test_handles_no_arguments_gracefully(tmp_path: Path):
    script = _write_script(tmp_path / "check_max_lines.sh")
    # Calling with no args should be a no-op and succeed
    code, out, err = _run(script, [])
    assert code == 0
    assert out.strip() == ""
    assert err == ""

# Note: wc -l counts newline characters, not logical lines without trailing newline.
# The current script uses wc -l and only normalizes empty string to 0.
# We document current behavior with a regression-style test below.
def test_no_trailing_newline_underreports_per_wc_behavior(tmp_path: Path):
    script = _write_script(tmp_path / "check_max_lines.sh")
    # Create 501 lines but omit trailing newline; wc -l will report 500 -> no failure expected
    p = tmp_path / "no_final_newline.txt"
    # Write 501 lines without trailing newline
    content = "\n".join(str(i) for i in range(1, 501 + 1))  # no terminal newline
    with p.open(mode="w", encoding="utf-8", newline="") as f:
        f.write(content)
    code, out, err = _run(script, [p])
    assert code == 0
    assert out.strip() == ""
    assert err == ""
