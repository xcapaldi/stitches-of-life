"""
The row-wise engine: knit a pattern one row at a time, letting the automaton
choose the texture and (optionally) propose the shaping.

Stepping backward is close to free here. Knitting is monotone -- a row, once
worked, is never modified -- so the fabric *is* the timeline, and un-knitting
is truncation rather than an undo log. Rules and seeding are deterministic, so
any state that has been stepped back to can be stepped forward into again and
come out identical.
"""

from __future__ import annotations

from array import array
from typing import Any

from .graph import OP_NAMES, StitchGraph
from .pattern import Pattern, RowSpec
from .rules import ElementaryRule, seed_row
from .shaping import DensityShaper, build_row_ops

__all__ = ["Knitter"]


class Knitter:
    """Knits a `Pattern`, evolving stitch state as the fabric grows."""

    def __init__(
        self,
        pattern: Pattern,
        rule: ElementaryRule | None = None,
        shaper: DensityShaper | None = None,
        seed: int | None = 0,
        seed_kind: str = "center",
        min_spacing: int = 2,
    ) -> None:
        self.pattern = pattern
        self.rule = rule if rule is not None else ElementaryRule(110)
        self.shaper = shaper
        self.seed = seed
        self.seed_kind = seed_kind
        self.min_spacing = min_spacing
        self.plan: list[RowSpec] = pattern.row_plan()

        self.graph = StitchGraph()
        self.state: array[int] = array("B")
        self.ops_by_row: list[list[int]] = []
        self.reset()

    # -- lifecycle -------------------------------------------------------

    def reset(self) -> None:
        """Return to the cast-on row."""
        self.graph = StitchGraph()
        self.graph.cast_on(self.plan[0].stitches)
        self.state = array("B", seed_row(self.plan[0].stitches, self.seed_kind, self.seed))
        self.ops_by_row = [[]]

    @property
    def current_row(self) -> int:
        return self.graph.n_rows - 1

    @property
    def done(self) -> bool:
        return self.current_row >= len(self.plan) - 1

    # -- stepping --------------------------------------------------------

    def knit_row(self) -> int:
        """Work the next row. Returns its index, or -1 if the piece is done."""
        if self.done:
            return -1
        row = self.current_row
        spec = self.plan[row + 1]
        prev_states = self.row_states(row)

        proposals = self.shaper.propose(prev_states) if self.shaper is not None else None
        spacing = self.shaper.min_spacing if self.shaper is not None else self.min_spacing
        texture_pairs = self.shaper.texture_pairs if self.shaper is not None else 0

        ops = build_row_ops(
            prev_len=len(prev_states),
            delta=spec.stitches - self.graph.row_len[row],
            at=spec.at,
            proposals=proposals,
            min_spacing=spacing,
            texture_pairs=texture_pairs,
        )
        new_row = self.graph.add_row(ops)
        self.state.extend(self.rule.next_row(prev_states, ops))
        self.ops_by_row.append(ops)
        return new_row

    def unknit_row(self) -> int:
        """Take the most recent row back off the needle."""
        if self.current_row <= 0:
            return -1
        start = self.graph.row_start[self.current_row]
        self.graph.pop_row()
        del self.state[start:]
        self.ops_by_row.pop()
        return self.current_row

    def step(self, count: int = 1) -> int:
        """Move `count` rows forward, or backward if `count` is negative."""
        for _ in range(abs(count)):
            moved = self.knit_row() if count > 0 else self.unknit_row()
            if moved < 0:
                break
        return self.current_row

    def goto_row(self, row: int) -> int:
        """Jump to a row, knitting or un-knitting as needed."""
        row = max(0, min(row, len(self.plan) - 1))
        while self.current_row < row and self.knit_row() >= 0:
            pass
        while self.current_row > row and self.unknit_row() >= 0:
            pass
        return self.current_row

    def knit_all(self) -> "Knitter":
        self.goto_row(len(self.plan) - 1)
        return self

    # -- inspection ------------------------------------------------------

    def row_states(self, row: int) -> list[int]:
        return [self.state[i] for i in self.graph.row_indices(row)]

    def stitch_counts(self) -> list[int]:
        return list(self.graph.row_len)

    def to_dict(self) -> dict[str, Any]:
        """Serialise the worked fabric.

        This is the interchange format the golden fixtures compare against,
        so a browser port can be checked against the same expected output
        rather than eyeballed.
        """
        return {
            "pattern": self.pattern.to_dict(),
            "rule": self.rule.number,
            "seed": self.seed,
            "seedKind": self.seed_kind,
            "rows": [
                {
                    "index": row,
                    "stitches": self.graph.row_len[row],
                    "ops": [OP_NAMES[op] for op in self.ops_by_row[row]],
                    "states": self.row_states(row),
                }
                for row in range(self.graph.n_rows)
            ],
        }

    def __repr__(self) -> str:
        return (
            f"<Knitter {self.pattern.name!r} row {self.current_row}/{len(self.plan) - 1} "
            f"{self.rule!r}>"
        )
