"""site/data must be real pipeline output that still matches the contracts (SPEC §11)."""

import json
from pathlib import Path

import yaml

from triage.schemas import RunResult

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "site" / "data"


def test_every_run_file_matches_run_result():
    files = sorted((DATA / "runs").glob("*.json"))
    assert len(files) >= 4
    for f in files:
        r = RunResult.model_validate_json(f.read_text())
        assert r.status == "OK" and r.requests, f.name
        assert all(rec.simulated for rec in r.log)


def test_manifest_points_at_existing_runs():
    for entry in json.loads((DATA / "manifest.json").read_text()):
        assert (DATA / entry["file"]).is_file()


def test_policy_json_is_the_policy_file():
    policy = yaml.safe_load((ROOT / "policy" / "policy_v1.yaml").read_text())
    assert json.loads((DATA / "policy.json").read_text()) == policy


def test_results_json_has_what_the_site_shows():
    res = json.loads((DATA / "results.json").read_text())
    assert {"metrics", "hard_gates", "targets", "slices"} <= res.keys()
    assert {"confusion_matrix", "approval_load", "latency_p50_s"} <= res["metrics"].keys()


def test_every_json_file_loads():
    for f in DATA.rglob("*.json"):
        json.loads(f.read_text())
