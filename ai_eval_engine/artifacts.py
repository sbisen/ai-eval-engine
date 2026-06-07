"""Load and format free-text domain artifacts for Step 1 (the cold-start path).

When a project has no dataset — only a repo and the agent's spec — domain context
must be inferred from *intent*: the system prompt, README, tool/function
definitions, user stories. This module reads those files offline (no API key, no
cost) so the prompt can be inspected and unit-tested, mirroring
:mod:`ai_eval_engine.sampling` for CSV sources.
"""

from __future__ import annotations

from pathlib import Path

from ai_eval_engine.config import TextSource

#: Per-file character cap so a large README can't blow the context budget.
DEFAULT_MAX_CHARS_PER_FILE = 8000


def resolve_artifact_paths(source: TextSource, base_dir: Path) -> list[Path]:
    """Resolve each (possibly relative) artifact path against the config's directory."""
    resolved: list[Path] = []
    for raw in source.paths:
        path = Path(raw)
        if not path.is_absolute():
            path = (base_dir / path).resolve()
        resolved.append(path)
    return resolved


def load_text_artifacts(
    source: TextSource,
    base_dir: Path,
    max_chars_per_file: int = DEFAULT_MAX_CHARS_PER_FILE,
) -> list[dict]:
    """Read each artifact file, truncating any that exceed the per-file char cap.

    Returns one record per file with ``name`` (the file name), ``content`` (text,
    possibly truncated), and ``truncated`` (bool). Raises ``FileNotFoundError`` for
    a missing path so a typo in the config fails loudly rather than silently.
    """
    artifacts: list[dict] = []
    for path in resolve_artifact_paths(source, base_dir):
        if not path.exists():
            raise FileNotFoundError(f"text source path not found: {path}")
        text = path.read_text(errors="replace")
        truncated = len(text) > max_chars_per_file
        if truncated:
            text = text[:max_chars_per_file]
        artifacts.append({"name": path.name, "content": text, "truncated": truncated})
    return artifacts


def format_artifacts(artifacts: list[dict]) -> str:
    """Render artifacts as labeled, deterministic text blocks for the model prompt."""
    if not artifacts:
        return "(no artifacts)"
    blocks = [f"Artifact count: {len(artifacts)}", ""]
    for i, a in enumerate(artifacts, 1):
        suffix = " (truncated)" if a.get("truncated") else ""
        blocks.append(f"--- Artifact {i}: {a['name']}{suffix} ---")
        blocks.append(a["content"])
        blocks.append("")
    return "\n".join(blocks)
