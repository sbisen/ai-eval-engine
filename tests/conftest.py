"""Shared fixtures: a tiny, self-contained CSV + config written to a temp dir."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_eval_engine.config import ProjectConfig

# 6 rows across 3 categories (a, a, b, b, c, c) so 2-per-stratum sampling is exact.
_CSV = """text,category
how do I reset my password,a
i forgot my password,a
where is my card,b
my card has not arrived,b
what is my balance,c
show recent transactions,c
"""


@pytest.fixture
def csv_path(tmp_path: Path) -> Path:
    p = tmp_path / "mini.csv"
    p.write_text(_CSV)
    return p


@pytest.fixture
def config_path(tmp_path: Path, csv_path: Path) -> Path:
    cfg = tmp_path / "mini.yaml"
    cfg.write_text(
        "project: mini-test\n"
        "domain_sources:\n"
        f"  - type: csv\n    path: {csv_path.name}\n    description: mini fixture\n"
        "stratify_by: category\n"
        "sample_per_stratum: 2\n"
        "sample_seed: 42\n"
    )
    return cfg


@pytest.fixture
def stratified_config() -> ProjectConfig:
    return ProjectConfig(
        project="mini-test",
        domain_sources=[{"type": "csv", "path": "mini.csv", "description": "mini fixture"}],
        stratify_by="category",
        sample_per_stratum=2,
        sample_seed=42,
    )


# --- grounded_qa fixture: a CSV + task-enabled config for Steps 2-5 ---------
_QA_CSV = """id,question,answer,evidence,company
q1,What was revenue?,$100,Total revenue was $100 for the year,Acme
q2,What was net income?,$20,Net income came to $20,Acme
q3,How many sites?,Three,The firm operates three regional sites,Globex
q4,What is the policy?,Refer to filing,The policy is described in the filing,Globex
"""


@pytest.fixture
def qa_project(tmp_path: Path) -> Path:
    """A grounded_qa project dir; returns the config path."""
    (tmp_path / "qa.csv").write_text(_QA_CSV)
    cfg = tmp_path / "qa.yaml"
    cfg.write_text(
        "project: qa-test\n"
        "domain_sources:\n"
        "  - type: csv\n    path: qa.csv\n    description: qa fixture\n"
        "stratify_by: company\n"
        "sample_per_stratum: 2\n"
        "sample_seed: 42\n"
        "task:\n"
        "  kind: grounded_qa\n"
        "  id_field: id\n"
        "  input_field: question\n"
        "  gold_field: answer\n"
        "  grounding_field: evidence\n"
        "  category_field: company\n"
    )
    return cfg
