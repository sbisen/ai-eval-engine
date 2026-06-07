"""Text-artifact ingestion (the cold-start, no-dataset path) — offline."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_eval_engine.artifacts import (
    DEFAULT_MAX_CHARS_PER_FILE,
    format_artifacts,
    load_text_artifacts,
)
from ai_eval_engine.config import TextSource


def _source(*names: str) -> TextSource:
    return TextSource(paths=list(names), description="spec")


def test_load_reads_each_file_in_order(tmp_path: Path):
    (tmp_path / "a.md").write_text("alpha")
    (tmp_path / "b.md").write_text("beta")
    artifacts = load_text_artifacts(_source("a.md", "b.md"), tmp_path)
    assert [a["name"] for a in artifacts] == ["a.md", "b.md"]
    assert artifacts[0]["content"] == "alpha"
    assert artifacts[0]["truncated"] is False


def test_load_truncates_large_files(tmp_path: Path):
    (tmp_path / "big.md").write_text("x" * (DEFAULT_MAX_CHARS_PER_FILE + 50))
    [artifact] = load_text_artifacts(_source("big.md"), tmp_path, max_chars_per_file=100)
    assert artifact["truncated"] is True
    assert len(artifact["content"]) == 100


def test_load_missing_path_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_text_artifacts(_source("nope.md"), tmp_path)


def test_format_labels_and_flags_truncation():
    rendered = format_artifacts(
        [
            {"name": "sys.md", "content": "be safe", "truncated": False},
            {"name": "big.md", "content": "...", "truncated": True},
        ]
    )
    assert "Artifact count: 2" in rendered
    assert "Artifact 1: sys.md" in rendered
    assert "Artifact 2: big.md (truncated)" in rendered
    assert "be safe" in rendered


def test_format_empty():
    assert format_artifacts([]) == "(no artifacts)"
