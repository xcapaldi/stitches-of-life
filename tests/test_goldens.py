"""
End-to-end golden fixtures.

These are the contract for the browser port: whatever language the engine is
written in, the same pattern with the same rule and seed must produce the same
fabric, byte for byte. Regenerate deliberately after an intended change:

    python -m tests.test_goldens --regen
"""

from __future__ import annotations

import os
import unittest
from dataclasses import dataclass, field

from stitchlife import (
    DensityShaper,
    ElementaryRule,
    Knitter,
    LifeRule,
    Pattern,
    SurfaceAutomaton,
    render_text,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(ROOT, "fixtures")
GOLDENS = os.path.join(FIXTURES, "goldens")


@dataclass(frozen=True)
class Case:
    name: str
    pattern: str
    rule: int = 110
    seed: int = 0
    seed_kind: str = "center"
    shape: bool = False
    rows: int | None = None
    surface: int = 0
    life_rule: str = "B3/S23"
    normalize: bool = True


CASES: tuple[Case, ...] = (
    Case("scarf-rule110", "scarf.json", rule=110),
    Case("scarf-rule30-random", "scarf.json", rule=30, seed=7, seed_kind="random"),
    Case("leaf-rule110", "leaf.json", rule=110),
    Case("leaf-partial", "leaf.json", rule=110, rows=12),
    Case("raglan-rule30", "raglan-front.json", rule=30, seed=3, seed_kind="random"),
    Case(
        "raglan-rule30-shaped",
        "raglan-front.json",
        rule=30,
        seed=3,
        seed_kind="random",
        shape=True,
    ),
    Case(
        "scarf-surface-life",
        "scarf.json",
        rule=90,
        seed=7,
        seed_kind="random",
        surface=4,
    ),
    Case(
        "scarf-surface-life-unnormalized",
        "scarf.json",
        rule=90,
        seed=7,
        seed_kind="random",
        surface=4,
        normalize=False,
    ),
)


def render_case(case: Case) -> str:
    pattern = Pattern.load(os.path.join(FIXTURES, case.pattern))
    knitter = Knitter(
        pattern,
        rule=ElementaryRule(case.rule),
        shaper=DensityShaper() if case.shape else None,
        seed=case.seed,
        seed_kind=case.seed_kind,
    )
    knitter.goto_row(case.rows if case.rows is not None else len(knitter.plan) - 1)

    state = knitter.state
    header = [
        f"case: {case.name}",
        f"pattern: {case.pattern}  rule: {case.rule}  seed: {case.seed} ({case.seed_kind})",
        f"shaper: {'density' if case.shape else 'none'}  rows: {knitter.graph.n_rows}"
        f"  stitches: {knitter.graph.n_stitches}",
    ]
    if case.surface:
        automaton = SurfaceAutomaton(
            knitter.graph,
            LifeRule.from_string(case.life_rule, normalize=case.normalize),
            knitter.state,
        )
        automaton.step(case.surface)
        state = automaton.state
        header.append(
            f"surface: {case.life_rule} normalize={case.normalize} "
            f"generations={case.surface} population={automaton.population}"
        )
    header.append("")
    return "\n".join(header) + render_text(knitter.graph, state, show_counts=True) + "\n"


def golden_path(case: Case) -> str:
    return os.path.join(GOLDENS, f"{case.name}.txt")


def regenerate() -> None:
    os.makedirs(GOLDENS, exist_ok=True)
    for case in CASES:
        with open(golden_path(case), "w", encoding="utf-8") as handle:
            handle.write(render_case(case))
        print(f"wrote {golden_path(case)}")


class TestGoldens(unittest.TestCase):
    def test_cases_have_unique_names(self):
        names = [case.name for case in CASES]
        self.assertEqual(len(names), len(set(names)))

    def test_output_matches_the_recorded_fabric(self):
        for case in CASES:
            with self.subTest(case=case.name):
                path = golden_path(case)
                self.assertTrue(
                    os.path.exists(path),
                    f"missing golden {path}; run: python -m tests.test_goldens --regen",
                )
                with open(path, "r", encoding="utf-8") as handle:
                    expected = handle.read()
                self.assertEqual(render_case(case), expected)

    def test_rendering_is_deterministic(self):
        for case in CASES:
            with self.subTest(case=case.name):
                self.assertEqual(render_case(case), render_case(case))


if __name__ == "__main__":
    import sys

    if "--regen" in sys.argv:
        regenerate()
    else:
        unittest.main()
