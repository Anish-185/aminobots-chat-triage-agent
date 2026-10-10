"""Run the Claude Code guard hooks the way Claude Code does: JSON on stdin, exit 2 = block."""

import json
import os
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
        ("uv run python -m eval.run_eval --split test --system pipeline", False),
        ("uv run python scripts/check_leakage.py", False),
        ("git push origin main", False),
        ("git commit -m 'add tag support'", False),
        ("git log --tags", False),
        ("ls data/dev", False),
    ],
)
def test_guard_bash(command, blocked):
    assert (run_hook("guard_bash.py", "Bash", {"command": command}) == 2) is blocked


def test_malformed_input_fails_closed():
    proc = subprocess.run(  # noqa: S603
        [sys.executable, str(HOOKS / "guard_bash.py")],
        input="not json",
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 2
