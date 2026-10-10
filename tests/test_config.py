import shutil
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from triage.config import CONFIG_DIR, load_models, load_pricing, load_thresholds


@pytest.fixture
def cfg(tmp_path: Path) -> Path:
    for f in CONFIG_DIR.glob("*.yaml"):
        shutil.copy(f, tmp_path)
    return tmp_path


def _edit(path: Path, fn) -> None:
    data = yaml.safe_load(path.read_text())
    fn(data)
    path.write_text(yaml.safe_dump(data))


@pytest.mark.parametrize("field", ["model", "fallbacks"])
def test_rejects_non_free_model(cfg: Path, field: str):
    def paid(d):
        role = d["roles"]["extractor"]
        if field == "model":
            role["model"] = "nvidia/nemotron-3-super-120b-a12b"
        else:
            role["fallbacks"] = ["google/gemma-4-31b-it"]

    _edit(cfg / "models.yaml", paid)
    with pytest.raises(ValidationError, match=":free"):
        load_models(cfg)


def test_rejects_other_provider(cfg: Path):
    _edit(cfg / "models.yaml", lambda d: d["roles"]["extractor"].update(provider="anthropic"))
    with pytest.raises(ValidationError):
        load_models(cfg)


def test_rejects_extra_key(cfg: Path):
    _edit(cfg / "thresholds.yaml", lambda d: d.update(surprise=1))
    with pytest.raises(ValidationError, match="surprise"):
        load_thresholds(cfg)


def test_rejects_missing_key(cfg: Path):
    _edit(cfg / "thresholds.yaml", lambda d: d.pop("openrouter_rpd"))
    with pytest.raises(ValidationError, match="openrouter_rpd"):
        load_thresholds(cfg)


def test_reference_distance_must_fit_overlap(cfg: Path):
    _edit(cfg / "thresholds.yaml", lambda d: d.update(max_reference_distance=61))
    with pytest.raises(ValidationError, match="chunk_overlap"):
        load_thresholds(cfg)


def test_every_configured_model_is_priced(cfg: Path):
    _edit(cfg / "pricing.yaml", lambda d: d["models"].pop("google/gemma-4-31b-it:free"))
    with pytest.raises(ValueError, match="gemma"):
        load_pricing(cfg)
