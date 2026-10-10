"""Shared helpers for the guard hooks. Frozen sets: CLAUDE.md invariant 6."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2]).resolve()
FROZEN = ("data/test", "data/challenge")


def rel_frozen(path: str, cwd: str | None = None) -> str | None:
    """Return the repo-relative path if `path` lies in a frozen set, else None."""
    p = Path(path)
    if not p.is_absolute():
        p = Path(cwd or ROOT) / p
    try:
        rel = p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return None
    return rel if any(rel == d or rel.startswith(d + "/") for d in FROZEN) else None


def block(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(2)


def run(check) -> None:
    """Read hook JSON from stdin and run `check`; any crash blocks (fail closed)."""
    try:
        check(json.load(sys.stdin))
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        block(f"guard hook error, blocking to fail closed: {e!r}")
