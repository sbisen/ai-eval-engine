"""Config loading and validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ai_eval_engine.config import CsvSource, ProjectConfig, TextSource, load_config


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


def test_text_source_discriminator_routes_by_type():
    config = ProjectConfig(
        project="spec",
        domain_sources=[{"type": "text", "paths": ["system_prompt.md"]}],
    )
    source = config.domain_sources[0]
    assert isinstance(source, TextSource)
    assert source.paths == ["system_prompt.md"]


def test_csv_source_still_routes_by_type():
    config = ProjectConfig(
        project="data", domain_sources=[{"type": "csv", "path": "x.csv"}]
    )
    assert isinstance(config.domain_sources[0], CsvSource)


def test_text_source_requires_at_least_one_path():
    with pytest.raises(ValidationError):
        ProjectConfig(
            project="spec", domain_sources=[{"type": "text", "paths": []}]
        )
