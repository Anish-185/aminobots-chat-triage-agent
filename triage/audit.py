"""Audit trail: load runs/*.jsonl into runs/audit.db (sqlite-utils) for Datasette.

    uv run python -m triage.audit
    uv run datasette runs/audit.db -m config/datasette.yaml

Read-only glue over the simulated logs (SPEC §10): the table is rebuilt from the JSONL each time,
and the JSONL files are never changed. sqlite-utils and Datasette are dev dependencies.
"""

import json
from pathlib import Path

import sqlite_utils

from triage.route import LOGS, RUNS

LOGS_ORDER = tuple(n.removesuffix(".jsonl") for n in LOGS.values())
COLUMNS = ("log", "run_id", "request_id", "grade", "rule_id", "identity_state", "team", "now")


def build(runs_dir: Path = RUNS, db_path: Path | None = None) -> dict[str, int]:
    """Rebuild the `records` table from every log; returns the row count per log."""
    runs_dir.mkdir(parents=True, exist_ok=True)
    db = sqlite_utils.Database(db_path or runs_dir / "audit.db")
    db["records"].drop(ignore=True)
    counts: dict[str, int] = {}
    for name in LOGS.values():
        path, log = runs_dir / name, name.removesuffix(".jsonl")
        lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
        rows = [
            {"id": f"{log}:{n}", "log": log, **json.loads(line)}
            for n, line in enumerate(lines, 1)
            if line.strip()
        ]
        if rows:
            db["records"].insert_all(rows, pk="id", alter=True, column_order=COLUMNS)
        counts[log] = len(rows)
    return counts


if __name__ == "__main__":
    counts = build()
    print(", ".join(f"{k}: {v}" for k, v in counts.items()), f"→ {RUNS / 'audit.db'}")
    print("Open it with: uv run datasette runs/audit.db -m config/datasette.yaml")
