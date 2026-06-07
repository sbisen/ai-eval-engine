"""Deterministic, reproducible sampling of domain sources.

Sampling is separated from the LLM call so it can be exercised offline (no API
key, no cost) and unit-tested. This is the reproducibility backbone of Step 1:
given the same ``sample_seed`` the same rows are always drawn.
"""

from __future__ import annotations

import csv
import random
from collections import defaultdict
from pathlib import Path

from ai_eval_engine.config import CsvSource, ProjectConfig


def resolve_source_path(source: CsvSource, base_dir: Path) -> Path:
    """Resolve a (possibly relative) source path against the config's directory."""
    path = Path(source.path)
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return path


def load_csv_sample(
    source: CsvSource, base_dir: Path, config: ProjectConfig
) -> list[dict[str, str]]:
    """Draw a deterministic sample of rows from a CSV source.

    When ``config.stratify_by`` is set, the sampler draws up to
    ``config.sample_per_stratum`` rows from every distinct value of that column,
    guaranteeing coverage of rare categories. Otherwise it draws a uniform
    ``config.sample_size`` sample. Both paths are seeded by ``config.sample_seed``.
    """
    path = resolve_source_path(source, base_dir)
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    rng = random.Random(config.sample_seed)

    if config.stratify_by:
        if rows and config.stratify_by not in rows[0]:
            raise ValueError(
                f"stratify_by={config.stratify_by!r} not in CSV columns "
                f"{list(rows[0].keys())}"
            )
        strata: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            strata[row[config.stratify_by]].append(row)
        sample: list[dict[str, str]] = []
        for stratum_rows in strata.values():
            k = min(config.sample_per_stratum, len(stratum_rows))
            sample.extend(rng.sample(stratum_rows, k))
        rng.shuffle(sample)
        return sample

    n = min(config.sample_size, len(rows))
    return rng.sample(rows, n)


def format_sample(sample: list[dict[str, str]]) -> str:
    """Render a sampled set of rows as a compact, deterministic text block."""
    if not sample:
        return "(empty sample)"
    columns = list(sample[0].keys())
    lines = [
        f"Columns: {', '.join(columns)}",
        f"Row count in sample: {len(sample)}",
        "",
    ]
    for i, row in enumerate(sample, 1):
        line = " | ".join(f"{k}={row.get(k, '')!r}" for k in columns)
        lines.append(f"{i:>3}. {line}")
    return "\n".join(lines)
