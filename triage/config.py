"""Typed loaders for config/*.yaml. Missing or extra keys fail loudly at load time."""

from datetime import date
from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _require_free(model_id: str) -> str:
    if not model_id.endswith(":free"):
        raise ValueError(f"only OpenRouter ':free' models are allowed, got {model_id!r}")
    return model_id


class RoleConfig(_Strict):
    provider: Literal["openrouter"]
    model: str
    fallbacks: list[str]
    temperature: float
    verified_on: date

    @field_validator("model")
    @classmethod
    def _model_free(cls, v: str) -> str:
        return _require_free(v)

    @field_validator("fallbacks")
    @classmethod
    def _fallbacks_free(cls, v: list[str]) -> list[str]:
        return [_require_free(m) for m in v]

    @model_validator(mode="after")
    def _distinct(self) -> Self:
        chain = [self.model, *self.fallbacks]
        if len(set(chain)) != len(chain):
            raise ValueError(f"model and fallbacks must be distinct: {chain}")
        return self


class Roles(_Strict):
    extractor: RoleConfig
    baseline_b1: RoleConfig


class Candidate(_Strict):
    id: str
    context_length: int | None
    structured_outputs: bool | None
    response_format: bool | None
    verified_on: date

    @field_validator("id")
    @classmethod
    def _id_free(cls, v: str) -> str:
        return _require_free(v)


class ModelsConfig(_Strict):
    roles: Roles
    candidates: list[Candidate]


class ModelPrice(_Strict):
    paid_variant: str | None
    input: float | None
    output: float | None


class PricingConfig(_Strict):
    checked_on: date
    source_url: str
    models: dict[str, ModelPrice]


class Thresholds(_Strict):
    name_match: int
    slot_cutoff_hours: float
    requests_per_minute: int
    requests_per_day: int
    llm_max_repair_retries: int
    demo_server_key_rpd: int | None


def _load(name: str, config_dir: Path | None) -> dict:
    path = (config_dir or CONFIG_DIR) / name
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a mapping at top level")
    return data


def load_models(config_dir: Path | None = None) -> ModelsConfig:
    return ModelsConfig.model_validate(_load("models.yaml", config_dir))


def load_pricing(config_dir: Path | None = None) -> PricingConfig:
    pricing = PricingConfig.model_validate(_load("pricing.yaml", config_dir))
    models = load_models(config_dir)
    for role in (models.roles.extractor, models.roles.baseline_b1):
        missing = {role.model, *role.fallbacks} - pricing.models.keys()
        if missing:
            raise ValueError(f"pricing.yaml has no entry for {sorted(missing)}")
    return pricing


def load_thresholds(config_dir: Path | None = None) -> Thresholds:
    return Thresholds.model_validate(_load("thresholds.yaml", config_dir))
