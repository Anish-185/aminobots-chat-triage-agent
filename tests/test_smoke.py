from typer.testing import CliRunner

import triage
from triage.cli import app
from triage.config import load_models, load_pricing, load_thresholds


def test_import():
    assert triage.__doc__


def test_configs_load():
    assert load_models().roles.extractor.provider == "openrouter"
    assert load_pricing().models
    assert load_thresholds().requests_per_day == 50
    assert load_thresholds().demo_server_key_rpd == 10


def test_version_command():
    result = CliRunner().invoke(app, ["version"])
    assert result.exit_code == 0, result.output
    assert "aminobots-triage" in result.output
    assert "policy:" in result.output
    assert "prompts:" in result.output
