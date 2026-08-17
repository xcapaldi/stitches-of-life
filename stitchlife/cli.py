"""
Command line front end, so the engine can be driven without a display.

    python -m stitchlife fixtures/leaf.json
    python -m stitchlife fixtures/raglan-front.json --rule 30 --shape --counts
    python -m stitchlife fixtures/scarf.json --rows 12      # stop partway
    python -m stitchlife fixtures/scarf.json --surface 4    # Life on the finished piece
    python -m stitchlife fixtures/leaf.json --schema        # IR schema for a model
"""

from __future__ import annotations

import argparse
import json
import sys

from .chart import render_text
from .knitter import Knitter
from .pattern import Pattern, PatternError, pattern_json_schema
from .rules import ElementaryRule, LifeRule
from .shaping import DensityShaper
from .surface import SurfaceAutomaton


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stitchlife", description=__doc__)
    parser.add_argument("pattern", nargs="?", help="path to a pattern JSON file")
    parser.add_argument("--rule", type=int, default=110, help="elementary rule number (0-255)")
    parser.add_argument("--seed", type=int, default=0, help="seed for the cast-on row")
    parser.add_argument(
        "--seed-kind",
        default="center",
        choices=("center", "edges", "full", "random"),
        help="how to seed the cast-on row",
    )
    parser.add_argument(
        "--shape",
        action="store_true",
        help="let the automaton propose shaping within the pattern's stitch counts",
    )
    parser.add_argument("--rows", type=int, help="stop after this many rows")
    parser.add_argument(
        "--surface",
        type=int,
        metavar="GENS",
        help="after knitting, run Game of Life over the finished piece",
    )
    parser.add_argument("--life-rule", default="B3/S23", help="birth/survival rule for --surface")
    parser.add_argument(
        "--no-normalize",
        action="store_true",
        help="use literal Life thresholds instead of scaling by neighbourhood degree",
    )
    parser.add_argument("--counts", action="store_true", help="annotate rows with stitch counts")
    parser.add_argument("--describe", action="store_true", help="print the pattern as prose")
    parser.add_argument("--json", action="store_true", help="dump the worked fabric as JSON")
    parser.add_argument("--schema", action="store_true", help="print the pattern IR JSON Schema")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.schema:
        print(json.dumps(pattern_json_schema(), indent=2))
        return 0
    if not args.pattern:
        build_parser().error("a pattern file is required unless --schema is given")

    try:
        pattern = Pattern.load(args.pattern)
    except (PatternError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.describe:
        print(pattern.describe())
        print()

    knitter = Knitter(
        pattern,
        rule=ElementaryRule(args.rule),
        shaper=DensityShaper() if args.shape else None,
        seed=args.seed,
        seed_kind=args.seed_kind,
    )
    knitter.goto_row(args.rows if args.rows is not None else len(knitter.plan) - 1)

    if args.json:
        print(json.dumps(knitter.to_dict(), indent=2))
        return 0

    state = knitter.state
    if args.surface:
        automaton = SurfaceAutomaton(
            knitter.graph,
            LifeRule.from_string(args.life_rule, normalize=not args.no_normalize),
            knitter.state,
        )
        automaton.step(args.surface)
        state = automaton.state
        print(f"{pattern.name}: {automaton!r}")
    else:
        print(f"{pattern.name}: {knitter!r}")

    print(render_text(knitter.graph, state, show_counts=args.counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
