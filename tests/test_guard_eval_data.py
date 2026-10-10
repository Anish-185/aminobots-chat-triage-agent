import importlib.util
import subprocess
from pathlib import Path

import pytest

_path = Path(__file__).resolve().parent.parent / "scripts" / "guard_eval_data.py"
_spec = importlib.util.spec_from_file_location("guard_eval_data", _path)
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)


@pytest.mark.parametrize(
    ("paths", "expected"),
    [
        ([], []),
        (["triage/cli.py", "data/dev/dev-0001.json"], []),
        (["data/test/README.md", "data/challenge/README.md"], []),
        (["data/test/test-0001.json"], ["data/test/test-0001.json"]),
        (["data/challenge/sub/c.json", "README.md"], ["data/challenge/sub/c.json"]),
        (["data/testing/x.json", "data/tests.json"], []),  # prefix lookalikes are not frozen
        (["data/test/README.md.bak"], ["data/test/README.md.bak"]),
    ],
)
def test_violations(paths, expected):
    assert guard.violations(paths) == expected


def test_main_blocks_and_allows(monkeypatch):
    monkeypatch.setattr(guard, "staged_paths", lambda: ["data/test/x.json"])
    monkeypatch.delenv("ALLOW_EVAL_DATA_COMMIT", raising=False)
    assert guard.main() == 1
    monkeypatch.setenv("ALLOW_EVAL_DATA_COMMIT", "1")
    assert guard.main() == 0


def test_staged_paths_reads_index(tmp_path, monkeypatch):
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)  # noqa: S603,S607

    git("init", "-q")
    (tmp_path / "data/test").mkdir(parents=True)
    (tmp_path / "data/test/a.json").write_text("{}")
    git("add", ".")
    monkeypatch.chdir(tmp_path)
    assert guard.staged_paths() == ["data/test/a.json"]
