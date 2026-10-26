"""Run the Claude Code guard hooks the way Claude Code does: JSON on stdin, exit 2 = block."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude" / "hooks"


def run_hook(script: str, tool: str, tool_input: dict) -> int:
    event = {
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "cwd": str(ROOT),
        "tool_input": tool_input,
    }
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(ROOT)}
    return subprocess.run(  # noqa: S603
        [sys.executable, str(HOOKS / script)],
        input=json.dumps(event),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    ).returncode


@pytest.mark.parametrize(
    ("tool", "tool_input", "blocked"),
    [
        ("Write", {"file_path": str(ROOT / "data/test/t.json")}, True),
        ("Edit", {"file_path": "data/challenge/c.json"}, True),
        ("Read", {"file_path": str(ROOT / "data/test/../test/t.json")}, True),
        ("Grep", {"pattern": "x", "path": str(ROOT / "data/challenge")}, True),
        ("Write", {"file_path": str(ROOT / "data/test/README.md")}, False),
        ("Write", {"file_path": str(ROOT / "data/dev/d.json")}, False),
        ("Write", {"file_path": str(ROOT / "data/testing/x.json")}, False),
        ("Glob", {"pattern": "data/*/*.json"}, True),
        ("Glob", {"pattern": "data/**"}, True),
        ("Glob", {"pattern": "data/{test,dev}/*"}, True),
        ("Glob", {"pattern": "*/*.json", "path": str(ROOT / "data")}, True),
        ("Glob", {"pattern": "test/*", "path": str(ROOT / "data")}, True),
        ("Grep", {"pattern": "x", "path": "data"}, True),
        ("Grep", {"pattern": "x", "glob": "data/*/*.json"}, True),
        ("Grep", {"pattern": "x", "path": "/"}, True),
        ("Glob", {"pattern": "data/dev/*.txt"}, False),
        ("Glob", {"pattern": "data/world/*.yaml"}, False),
        ("Glob", {"pattern": "**/*.py"}, False),
        ("Grep", {"pattern": "x", "path": "data/dev"}, False),
        ("Grep", {"pattern": "x", "glob": "*.py"}, False),
        ("Grep", {"pattern": "x"}, False),
    ],
)
def test_guard_paths(tool, tool_input, blocked):
    assert (run_hook("guard_paths.py", tool, tool_input) == 2) is blocked


@pytest.mark.parametrize(
    ("command", "blocked"),
    [
        ("cat data/test/t.json", True),
        ("head -n5 data/challenge/c.json", True),
        ("grep -r foo data/test", True),
        ("python -c \"open('data/test/t.json').read()\"", True),
        ("uv run python -m eval.run_eval --split test; cat data/test/t.json", True),
        ("git push --force origin main", True),
        ("git push -f", True),
        ("git -C . tag v1", True),
        ("ls data/*", True),
        ("cat data/**/*.json", True),
        ("cat data/{test,dev}/a.json", True),
        ("head data/t*/x", True),
        ("ls data/[tc]*", True),
        ("cd data && cat test/x.json", True),
        ("cd data; ls challenge", True),
        ("grep -rn foo .", True),
        ("grep -r foo data", True),
        ("grep -R foo", True),
        ("grep --include '*.py' -rn foo *", True),
        ("find . -name '*.json'", True),
        ("find data -type f", True),
        ("find /", True),
        ("tree data", True),
        ("du -sh data/", True),
        ("ls -R data", True),
        ("cp -r data /tmp/x", True),
        ("tar czf x.tgz .", True),
        ("rg --no-ignore foo", True),
        ("rg -uu foo", True),
        ("uv run python scripts/check_leakage.py data/test", True),
        ("uv run python -m eval.run_eval --split test --system pipeline", False),
        ("ls data", False),
        ("ls data/dev/*", False),
        ("cat data/world/*.yaml", False),
        ("cat data/dev/c01.txt", False),
        ("grep -rn foo data/dev", False),
        ("grep -rn --include '*.py' foo triage tests", False),
        ("grep -n foo triage/config.py", False),
        ("find data/dev -name '*.json'", False),
        ("find triage tests -name '*.py'", False),
        ("cd data && ls dev", False),
        ("rg foo", False),
        ("uv run pytest -q", False),
        ("git push origin main", False),
        ("git commit -m 'add tag support'", False),
        ("git log --tags", False),
        ("ls data/dev", False),
    ],
)
def test_guard_bash(command, blocked):
    assert (run_hook("guard_bash.py", "Bash", {"command": command}) == 2) is blocked


@pytest.mark.skipif(shutil.which("rg") is None, reason="ripgrep not installed")
def test_ignore_file_hides_frozen_sets_from_ripgrep(tmp_path: Path):
    """Grep/Glob use ripgrep; the root .ignore must hide the frozen sets (fake copies here)."""
    shutil.copy(ROOT / ".ignore", tmp_path / ".ignore")
    for d in ("test", "challenge", "dev"):
        (tmp_path / "data" / d).mkdir(parents=True)
        (tmp_path / "data" / d / "x.txt").write_text("needle\n")
    out = subprocess.run(  # noqa: S603
        ["rg", "-l", "needle"],  # noqa: S607
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    ).stdout.split()
    assert out == ["data/dev/x.txt"]


def test_malformed_input_fails_closed():
    proc = subprocess.run(  # noqa: S603
        [sys.executable, str(HOOKS / "guard_bash.py")],
        input="not json",
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 2
