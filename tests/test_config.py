"""Config loading and validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ai_eval_engine.config import ProjectConfig, load_config


def test_load_config_roundtrip(config_path):
    config = load_config(config_path)
    assert config.project == "mini-test"
    assert config.stratify_by == "category"
    assert config.sample_per_stratum == 2
    assert config.sample_seed == 42
    assert config.domain_sources[0].type == "csv"
    assert config.domain_sources[0].path == "mini.csv"


def test_defaults():
    config = ProjectConfig(
        project="p", domain_sources=[{"type": "csv", "path": "x.csv"}]
    )
    assert config.sample_size == 100
    assert config.sample_seed == 42
    assert config.stratify_by is None


def test_requires_a_domain_source():
    with pytest.raises(ValidationError):
        ProjectConfig(project="p", domain_sources=[])


def test_requires_non_empty_project():
    with pytest.raises(ValidationError):
        ProjectConfig(project="", domain_sources=[{"type": "csv", "path": "x.csv"}])
