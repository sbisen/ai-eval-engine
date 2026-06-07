"""Dataset-agnostic Step-1 quickstart.

Usage:
    python examples/quickstart.py configs/financebench.yaml
    python examples/quickstart.py configs/scienceagentbench.yaml

The sampling half runs offline (no API key). The extraction half requires
ANTHROPIC_API_KEY; it is skipped with a message if the key is absent. Equivalent
to `ai-eval-engine sample --config <cfg>` and `ai-eval-engine extract --config <cfg>`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from ai_eval_engine import build_user_message, load_config, load_csv_sample


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2

    config_path = Path(argv[0]).resolve()
    config = load_config(config_path)
    source = config.domain_sources[0]

    # --- Offline: reproduce the deterministic Step-1 sample -------------------
    sample = load_csv_sample(source, config_path.parent, config)
    print(f"Sampled {len(sample)} rows for project {config.project!r}.")
    print(build_user_message(config.project, source.description, sample)[:600], "...\n")

    # --- Online: extract the structured DomainContext ------------------------
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set — skipping extraction.")
        return 0

    from ai_eval_engine import extract_domain_context

    context = extract_domain_context(config_path)
    print(context.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
