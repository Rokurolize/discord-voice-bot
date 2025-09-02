import re
from pathlib import Path

import pytest

# Framework note:
# Using pytest. Async support is available project-wide per repo docs, but these tests are synchronous.


def _find_guidelines_md(repo_root: Path) -> Path:
    # Search candidates by heading and common doc locations
    patterns = [
        r"^#\s*Repository Guidelines\s*$",
    ]
    globs = [
        "*.md",
        "docs/**/*.md",
        "DOCS/**/*.md",
        "README*.md",
    ]
    for g in globs:
        for p in repo_root.glob(g):
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for pat in patterns:
                if re.search(pat, text, flags=re.MULTILINE):
                    return p
    raise FileNotFoundError("Could not locate the 'Repository Guidelines' markdown. Ensure the document contains a top-level '# Repository Guidelines' heading.")


@pytest.fixture(scope="session")
def guidelines_path() -> Path:
    return _find_guidelines_md(Path.cwd())


@pytest.fixture(scope="session")
def guidelines_text(guidelines_path: Path) -> str:
    return guidelines_path.read_text(encoding="utf-8")


def test_has_required_top_level_sections_in_order(guidelines_text: str):
    # Expected section order from the diff/source provided
    expected_sections = [
        r"^#\s*Repository Guidelines\s*$",
        r"^##\s*Project Structure & Module Organization\s*$",
        r"^##\s*Build, Test, and Development Commands\s*$",
        r"^##\s*Coding Style & Naming Conventions\s*$",
        r"^##\s*Testing Guidelines\s*$",
        r"^##\s*Commit & Pull Request Guidelines\s*$",
        r"^##\s*Security & Configuration Tips\s*$",
        r"^###\s*Test-only overrides\s*$",
        r"^##\s*Resolving Review Threads\s*$",
        r"^##\s*Single-Action Summary\s*$",
        r"^##\s*Maintenance Note\s*$",
    ]
    # Find index positions of each header to assert relative order
    positions = []
    for pat in expected_sections:
        m = re.search(pat, guidelines_text, flags=re.MULTILINE)
        assert m, f"Missing section heading matching pattern: {pat}"
        positions.append(m.start())

    # Ensure strictly increasing order
    assert positions == sorted(positions), "Section headings are out of the expected order."


def test_testing_guidelines_call_out_pytest_and_asyncio(guidelines_text: str):
    m = re.search(r"^##\s*Testing Guidelines\s*$", guidelines_text, flags=re.MULTILINE)
    assert m, "Missing 'Testing Guidelines' section."

    # Look within the section up to the next '##'
    start = m.end()
    next_h2 = re.search(r"^##\s+", guidelines_text[start:], flags=re.MULTILINE)
    section_text = guidelines_text[start:] if not next_h2 else guidelines_text[start : start + next_h2.start()]

    assert "pytest" in section_text.lower(), "Testing guidelines should mention pytest."
    assert "pytest-asyncio" in section_text.lower(), "Testing guidelines should mention pytest-asyncio."
    assert re.search(r"Naming:\s*`test_.*\.py`.*`Test\*`.*`test_.*`", section_text), "Expected naming conventions not found."
    assert re.search(r"Targeted runs:\s*`[^`]*pytest[^`]*-k[^`]*`", section_text), "Expected targeted run example not found."


def test_build_commands_include_uv_and_poe(guidelines_text: str):
    section_re = r"^##\s*Build, Test, and Development Commands\s*$"
    m = re.search(section_re, guidelines_text, flags=re.MULTILINE)
    assert m, "Missing build/test/dev commands section."

    text = guidelines_text[m.end() :]
    next_h2 = re.search(r"^##\s+", text, flags=re.MULTILINE)
    section_text = text if not next_h2 else text[: next_h2.start()]

    required_snippets = [
        r"`uv run discord-voice-bot`",
        r"`python -m discord_voice_bot`",
        r"`uv run poe test`",
        r"`uv run pytest -q`",
        r"`uv run poe lint`",
        r"`uv run poe format`",
        r"`uv run poe fix`",
        r"`uv run poe type-check`",
        r"`uv run poe check`",
    ]
    for snip in required_snippets:
        assert re.search(snip, section_text), f"Missing expected command snippet: {snip}"


def test_coding_style_highlights_python_version_and_line_length(guidelines_text: str):
    section_re = r"^##\s*Coding Style & Naming Conventions\s*$"
    m = re.search(section_re, guidelines_text, flags=re.MULTILINE)
    assert m, "Missing coding style section."
    text = guidelines_text[m.end() :]
    next_h2 = re.search(r"^##\s+", text, flags=re.MULTILINE)
    section_text = text if not next_h2 else text[: next_h2.start()]

    assert re.search(r"Python\s+3\.12", section_text), "Expected Python 3.12 reference."
    assert re.search(r"line length\s*200", section_text), "Expected line length 200 reference."
    assert re.search(r"Ruff", section_text), "Expected Ruff mention for formatting/linting."
    assert re.search(r"Type hints required", section_text), "Expected 'Type hints required' statement."


def test_security_and_config_tips_include_test_mode_truthy_semantics(guidelines_text: str):
    section_re = r"^##\s*Security & Configuration Tips\s*$"
    m = re.search(section_re, guidelines_text, flags=re.MULTILINE)
    assert m, "Missing security & configuration tips section."
    text = guidelines_text[m.end() :]
    next_h2 = re.search(r"^##\s+|^###\s+", text, flags=re.MULTILINE)
    section_text = text if not next_h2 else text[: next_h2.start()]

    # Verify TEST_MODE description and truthy values list
    assert re.search(r"TEST_MODE", section_text), "Expected TEST_MODE mention."
    truthy = re.findall(r"`(true|1|yes|on)`", section_text, flags=re.IGNORECASE)
    assert set(map(str.lower, truthy)) == {"true", "1", "yes", "on"}, "Expected truthy values list not found or incomplete."

    # Verify precedence ordering
    assert re.search(
        r"precedence:\s*process environment variables override `.env`; `.env` overrides secrets; all override built-in defaults\.",
        section_text,
        flags=re.IGNORECASE,
    ), "Expected precedence statement not found."


def test_test_only_overrides_section_contains_expected_keys_and_examples(guidelines_text: str):
    m = re.search(r"^###\s*Test-only overrides\s*$", guidelines_text, flags=re.MULTILINE)
    assert m, "Missing 'Test-only overrides' subsection."
    text = guidelines_text[m.end() :]
    # Capture until next H2/H3
    next_hdr = re.search(r"^##\s+|^###\s+", text, flags=re.MULTILINE)
    section_text = text if not next_hdr else text[: next_hdr.start()]

    # Keys
    for key in [
        "TEST_TARGET_VOICE_CHANNEL_ID",
        "TEST_RATE_LIMIT_MESSAGES",
        "TEST_RATE_LIMIT_PERIOD",
    ]:
        assert key in section_text, f"Expected key '{key}' not documented in test-only overrides."

    # Number formatting rules
    assert re.search(
        r"accepts? underscores/spaces/commas.*\(e\.g\.,\s*`1_234_567_890`.*`1,234,567,890`\)",
        section_text,
        flags=re.IGNORECASE | re.DOTALL,
    ), "Expected number formatting guidance with underscores/spaces/commas."

    # dotenv example block present with the exact variables
    dotenv_block = re.search(
        r"```dotenv\s*.*?TEST_MODE=true.*?TEST_TARGET_VOICE_CHANNEL_ID=.*?\n.*?TEST_RATE_LIMIT_MESSAGES=.*?\n.*?TEST_RATE_LIMIT_PERIOD=.*?\n```",
        section_text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    assert dotenv_block, "Expected dotenv example block with TEST_MODE and test override values."

    # bash one-off example present
    bash_block = re.search(
        r"```bash\s*.*?export\s+TEST_MODE=true\s+TEST_TARGET_VOICE_CHANNEL_ID=.*?\s+TEST_RATE_LIMIT_MESSAGES=.*?\s+TEST_RATE_LIMIT_PERIOD=.*?\n.*?```",
        section_text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    assert bash_block, "Expected bash export example block with test overrides."


def test_resolving_review_threads_contains_git_and_ci_instructions(guidelines_text: str):
    m = re.search(r"^##\s*Resolving Review Threads\s*$", guidelines_text, flags=re.MULTILINE)
    assert m, "Missing 'Resolving Review Threads' section."
    text = guidelines_text[m.end() :]
    next_h2 = re.search(r"^##\s+", text, flags=re.MULTILINE)
    section_text = text if not next_h2 else text[: next_h2.start()]

    required_lines = [
        r"`git status`",
        r"`git diff -U0`",
        r"`uv run poe check`.*status code 0",
        r"Even for doc-only changes, still run the checks",
    ]
    for rl in required_lines:
        assert re.search(rl, section_text, flags=re.IGNORECASE), f"Missing review thread instruction: {rl}"


def test_single_action_summary_has_push_guidance(guidelines_text: str):
    m = re.search(r"^##\s*Single-Action Summary\s*$", guidelines_text, flags=re.MULTILINE)
    assert m, "Missing 'Single-Action Summary' section."
    text = guidelines_text[m.end() :]
    next_h2 = re.search(r"^##\s+", text, flags=re.MULTILINE)
    section_text = text if not next_h2 else text[: next_h2.start()]

    # Check for the sequence guidance and fork tip code block
    assert re.search(r"After each fix:\s*`uv run poe check`", section_text), "Expected 'After each fix' instruction."


# Blocked command:     assert re.search(r"git push -u origin HEAD:\$\(git branch --show-current\)", section_text), "Expected explicit push guidance for forks."


def test_maintenance_note_prefers_small_commits_and_rebase_guidance(guidelines_text: str):
    m = re.search(r"^##\s*Maintenance Note\s*$", guidelines_text, flags=re.MULTILINE)
    assert m, "Missing 'Maintenance Note' section."
    text = guidelines_text[m.end() :]
    # end of file, so we can use the tail
    section_text = text

    assert re.search(r"Prefer small,\s*focused commits", section_text, flags=re.IGNORECASE), "Expected small commits guidance."
    assert re.search(r"git rebase -i origin/main", section_text), "Expected interactive rebase suggestion."
    # Blocked command:     assert re.search(r"git push --force-with-lease", section_text), "Expected safe force push guidance."
    assert re.search(r"Squash and merge", section_text), "Expected squash and merge mention."
