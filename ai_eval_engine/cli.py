"""Command-line interface for AI Eval Engine.

    ai-eval-engine sample  --config configs/financebench.yaml      # Step 1, offline
    ai-eval-engine extract --config configs/financebench.yaml      # Step 1, calls Claude
    ai-eval-engine golden    --config configs/financebench.yaml    # Step 2, offline
    ai-eval-engine recommend --context context.json                # Step 3a, offline
    ai-eval-engine build     --config configs/financebench.yaml    # Steps 2-5, offline
    ai-eval-engine version

The ``sample``, ``golden`` and ``build`` commands run fully offline (no API key,
no cost) so the whole pipeline — golden set, eval, runbook, dashboard — can be
reproduced and reviewed without spending tokens.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ai_eval_engine import __version__
from ai_eval_engine.config import TextSource, load_config
from ai_eval_engine.domain_context import build_artifacts_message, build_user_message
from ai_eval_engine.sampling import format_sample, load_csv_sample


def _cmd_sample(args: argparse.Namespace) -> int:
    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    source = config.domain_sources[0]

    if isinstance(source, TextSource):
        return _sample_text(args, config, source, config_path.parent)
    return _sample_csv(args, config, source, config_path.parent)


def _sample_csv(args, config, source, base_dir: Path) -> int:
    sample = load_csv_sample(source, base_dir, config)

    if args.show_prompt:
        sys.stdout.write(build_user_message(config.project, source.description, sample))
        sys.stdout.write("\n")
        return 0
    if args.json:
        json.dump(sample, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    strata = {row[config.stratify_by] for row in sample} if config.stratify_by else set()
    print(f"project:        {config.project}")
    print(f"source:         {source.path}")
    print(f"sample rows:    {len(sample)}")
    if config.stratify_by:
        print(f"stratified by:  {config.stratify_by} ({len(strata)} strata)")
    print(f"seed:           {config.sample_seed}")
    print()
    print(format_sample(sample))
    return 0


def _sample_text(args, config, source, base_dir: Path) -> int:
    from ai_eval_engine.artifacts import format_artifacts, load_text_artifacts

    artifacts = load_text_artifacts(source, base_dir)

    if args.show_prompt:
        sys.stdout.write(
            build_artifacts_message(config.project, source.description, artifacts)
        )
        sys.stdout.write("\n")
        return 0
    if args.json:
        json.dump(artifacts, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    print(f"project:        {config.project}")
    print(f"source:         text ({len(artifacts)} artifact(s))")
    print()
    print(format_artifacts(artifacts))
    return 0


def _cmd_extract(args: argparse.Namespace) -> int:
    # Imported lazily so `sample`/`version` work without the anthropic SDK configured.
    from ai_eval_engine.domain_context import extract_domain_context

    context = extract_domain_context(args.config)
    payload = context.model_dump_json(indent=2)
    if args.out:
        Path(args.out).write_text(payload)
        print(f"wrote DomainContext -> {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(payload + "\n")
    return 0


def _cmd_golden(args: argparse.Namespace) -> int:
    from ai_eval_engine.golden_set import build_golden_set

    golden = build_golden_set(args.config, context_path=args.context)
    if args.out:
        golden.save(args.out)
        print(f"wrote golden set ({golden.case_count} cases, {golden.version}) "
              f"-> {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(golden.model_dump_json(indent=2) + "\n")
    return 0


def _cmd_generate(args: argparse.Namespace) -> int:
    from ai_eval_engine.config import load_config
    from ai_eval_engine.golden_set import (
        _evidence_excerpts,
        _require_task,
        build_generation_message,
        runbook_learnings,
    )
    from ai_eval_engine.sampling import load_csv_sample

    config_path = Path(args.config).resolve()

    if args.show_prompt:
        config = load_config(config_path)
        task = _require_task(config)
        sample = load_csv_sample(config.domain_sources[0], config_path.parent, config)
        excerpts = _evidence_excerpts(sample, task, config.category_field)
        ctx = json.loads(Path(args.context).read_text())
        learnings = runbook_learnings(
            json.loads(Path(args.runbook).read_text()) if args.runbook else None
        )
        sys.stdout.write(
            build_generation_message(config.project, ctx, excerpts, args.target, learnings)
            + "\n"
        )
        return 0

    from ai_eval_engine.golden_set import generate_golden_set

    golden = generate_golden_set(args.config, args.context, target_cases=args.target,
                                 runbook_path=args.runbook)
    if args.out:
        golden.save(args.out)
        print(f"generated golden set ({golden.case_count} cases, {golden.version}) "
              f"-> {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(golden.model_dump_json(indent=2) + "\n")
    return 0


def _cmd_build(args: argparse.Namespace) -> int:
    from ai_eval_engine.pipeline import build

    paths = build(args.config, args.out, context_path=args.context,
                  predictions=args.predictions, demo=not args.gold_baseline)
    print(f"built domain-aware eval bundle in {args.out}/", file=sys.stderr)
    for name, p in paths.items():
        print(f"  {name:12} {p}", file=sys.stderr)
    print(f"\nopen the dashboard:  {paths['dashboard']}", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-eval-engine",
        description="Domain-aware evaluation framework for production AI agents.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_sample = sub.add_parser(
        "sample", help="Draw the deterministic Step-1 sample (offline, no API key)."
    )
    p_sample.add_argument("--config", required=True, help="Path to a project YAML config.")
    p_sample.add_argument("--json", action="store_true", help="Emit the sampled rows as JSON.")
    p_sample.add_argument(
        "--show-prompt",
        action="store_true",
        help="Print the exact prompt that would be sent to the model.",
    )
    p_sample.set_defaults(func=_cmd_sample)

    p_extract = sub.add_parser(
        "extract", help="Extract a DomainContext via Claude (requires ANTHROPIC_API_KEY)."
    )
    p_extract.add_argument("--config", required=True, help="Path to a project YAML config.")
    p_extract.add_argument("--out", help="Write the DomainContext JSON to this path.")
    p_extract.set_defaults(func=_cmd_extract)

    p_golden = sub.add_parser(
        "golden", help="Generate a versioned golden set (Step 2, offline)."
    )
    p_golden.add_argument("--config", required=True, help="Path to a project YAML config.")
    p_golden.add_argument("--context", help="Optional DomainContext JSON (adds safety cases).")
    p_golden.add_argument("--out", help="Write the golden set JSON to this path.")
    p_golden.set_defaults(func=_cmd_golden)

    p_generate = sub.add_parser(
        "generate",
        help="Generate a varied, edge-case golden set via Claude (Step 2, requires ANTHROPIC_API_KEY).",
    )
    p_generate.add_argument("--config", required=True, help="Path to a project YAML config.")
    p_generate.add_argument(
        "--context", required=True, help="Step-1 DomainContext JSON (grounds the generation)."
    )
    p_generate.add_argument(
        "--target", type=int, default=24, help="Approx. number of cases to author (default 24)."
    )
    p_generate.add_argument(
        "--runbook",
        help="Optional Step-4 living runbook JSON; its failure modes are re-targeted.",
    )
    p_generate.add_argument("--out", help="Write the golden set JSON to this path.")
    p_generate.add_argument(
        "--show-prompt",
        action="store_true",
        help="Print the exact generation prompt instead of calling the model (offline).",
    )
    p_generate.set_defaults(func=_cmd_generate)

    p_build = sub.add_parser(
        "build",
        help="Run Steps 2-5 end-to-end: golden set, eval, runbook, dashboard (offline).",
    )
    p_build.add_argument("--config", required=True, help="Path to a project YAML config.")
    p_build.add_argument("--out", required=True, help="Output directory for all artifacts.")
    p_build.add_argument("--context", help="Optional DomainContext JSON (adds safety cases).")
    p_build.add_argument("--predictions", help="JSON map {case_id: prediction} to score.")
    p_build.add_argument(
        "--gold-baseline", action="store_true",
        help="Use near-perfect baseline predictions instead of the demo mix.",
    )
    p_build.set_defaults(func=_cmd_build)

    p_version = sub.add_parser("version", help="Print the installed version.")
    p_version.set_defaults(func=lambda _a: (print(__version__) or 0))

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
