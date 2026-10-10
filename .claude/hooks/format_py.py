#!/usr/bin/env python3
"""PostToolUse: run `uv run ruff format` on an edited .py file. Never blocks."""

import json
import subprocess
import sys
from pathlib import Path

from _frozen import ROOT

try:
    path = (json.load(sys.stdin).get("tool_input") or {}).get("file_path") or ""
    if path.endswith(".py") and Path(path).is_file():
        subprocess.run(["uv", "run", "ruff", "format", path], cwd=ROOT, check=False)  # noqa: S603,S607
except Exception as e:  # noqa: BLE001
    print(f"format_py: skipped ({e!r})", file=sys.stderr)
