"""Deterministic / stratified sampling — the reproducibility backbone of Step 1."""

from __future__ import annotations

import pytest

from ai_eval_engine.config import CsvSource, ProjectConfig
from ai_eval_engine.sampling import format_sample, load_csv_sample


def test_stratified_covers_every_stratum(csv_path, stratified_config):
    source = CsvSource(path=csv_path.name)
    sample = load_csv_sample(source, csv_path.parent, stratified_config)
    # 3 categories x 2 per stratum = 6 rows, every category represented.
    assert len(sample) == 6
    assert {row["category"] for row in sample} == {"a", "b", "c"}


def test_sampling_is_deterministic(csv_path, stratified_config):
    source = CsvSource(path=csv_path.name)
    first = load_csv_sample(source, csv_path.parent, stratified_config)
    second = load_csv_sample(source, csv_path.parent, stratified_config)
    assert first == second


def test_different_seed_changes_order(csv_path):
    source = CsvSource(path=csv_path.name)
    base = dict(
        project="p",
        domain_sources=[{"type": "csv", "path": csv_path.name}],
        stratify_by="category",
        sample_per_stratum=2,
    )
    a = load_csv_sample(source, csv_path.parent, ProjectConfig(**base, sample_seed=1))
    b = load_csv_sample(source, csv_path.parent, ProjectConfig(**base, sample_seed=2))
    # Same rows are present, but the shuffle order differs across seeds.
    assert {r["text"] for r in a} == {r["text"] for r in b}
    assert a != b


def test_uniform_sample_respects_size(csv_path):
    source = CsvSource(path=csv_path.name)
    config = ProjectConfig(
        project="p",
        domain_sources=[{"type": "csv", "path": csv_path.name}],
        sample_size=3,
    )
    sample = load_csv_sample(source, csv_path.parent, config)
    assert len(sample) == 3


def test_bad_stratify_column_raises(csv_path):
    source = CsvSource(path=csv_path.name)
    config = ProjectConfig(
        project="p",
        domain_sources=[{"type": "csv", "path": csv_path.name}],
        stratify_by="not_a_column",
    )
    with pytest.raises(ValueError, match="not in CSV columns"):
        load_csv_sample(source, csv_path.parent, config)


def test_format_sample_contains_columns_and_count():
    rows = [{"text": "hi", "category": "a"}, {"text": "yo", "category": "b"}]
    out = format_sample(rows)
    assert "Columns: text, category" in out
    assert "Row count in sample: 2" in out


def test_format_empty_sample():
    assert format_sample([]) == "(empty sample)"
