"""CLI smoke tests for the offline commands (no API key required)."""

from __future__ import annotations

import json

from ai_eval_engine.cli import main


def test_version_command(capsys):
    rc = main(["version"])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out  # a version string is printed


def test_sample_command_human_readable(capsys, config_path):
    rc = main(["sample", "--config", str(config_path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "project:        mini-test" in out
    assert "stratified by:  category" in out
    assert "Row count in sample: 6" in out


def test_sample_command_json(capsys, config_path):
    rc = main(["sample", "--config", str(config_path), "--json"])
    out = capsys.readouterr().out
    assert rc == 0
    rows = json.loads(out)
    assert len(rows) == 6
    assert {r["category"] for r in rows} == {"a", "b", "c"}


def test_sample_command_show_prompt(capsys, config_path):
    rc = main(["sample", "--config", str(config_path), "--show-prompt"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Project: mini-test" in out
    assert "Extract the DomainContext" in out


def test_sample_text_source_human_readable(capsys, text_config_path):
    rc = main(["sample", "--config", str(text_config_path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "project:        spec-test" in out
    assert "2 artifact(s)" in out
    assert "Artifact 1: system_prompt.md" in out


def test_sample_text_source_json(capsys, text_config_path):
    rc = main(["sample", "--config", str(text_config_path), "--json"])
    out = capsys.readouterr().out
    assert rc == 0
    artifacts = json.loads(out)
    assert [a["name"] for a in artifacts] == ["system_prompt.md", "user_stories.md"]


def test_sample_text_source_show_prompt(capsys, text_config_path):
    rc = main(["sample", "--config", str(text_config_path), "--show-prompt"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Project: spec-test" in out
    assert "Extract the DomainContext for this agent" in out
