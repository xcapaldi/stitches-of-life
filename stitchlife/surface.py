"""
The surface engine: Conway's Game of Life iterated over a finished piece.

Here the whole garment surface is the grid and a generation is one sweep of
the rule, which is what the pygame prototype does -- except that the surface
now comes from a pattern and carries the real fabric topology, so shaping
points genuinely disrupt the automaton instead of being drawn in by hand.

The fabric does not grow in this mode, so stepping backward needs history.
Snapshots are one byte per stitch, which is cheap enough to keep outright:
a 200-stitch by 300-row piece is 60 KB per generation. `keyframe_every`
trades that memory for recomputation when a piece is large or a run is long,
which is safe because the rule is deterministic.
"""

from __future__ import annotations

from array import array
from typing import Sequence

from .graph import StitchGraph
from .rules import LifeRule

__all__ = ["SurfaceAutomaton"]


class SurfaceAutomaton:
    """Iterates a `LifeRule` over a fixed stitch graph with a timeline."""

    def __init__(
        self,
        graph: StitchGraph,
        rule: LifeRule | None = None,
        initial: Sequence[int] | None = None,
        keyframe_every: int = 1,
    ) -> None:
        if initial is not None and len(initial) != graph.n_stitches:
            raise ValueError(
                f"initial state has {len(initial)} entries, graph has {graph.n_stitches}"
            )
        self.graph = graph
        self.rule = rule if rule is not None else LifeRule()
        self.keyframe_every = max(1, keyframe_every)
        self.initial = array("B", initial if initial is not None else bytes(graph.n_stitches))
        self.state = array("B", self.initial)
        self.generation = 0
        self._keyframes: dict[int, bytes] = {0: bytes(self.initial)}

    # -- stepping --------------------------------------------------------

    def step(self, count: int = 1) -> int:
        """Advance `count` generations, or rewind if `count` is negative."""
        if count < 0:
            return self.goto(self.generation + count)
        for _ in range(count):
            self.state = self.rule.next_state(self.graph, self.state)
            self.generation += 1
            if self.generation % self.keyframe_every == 0:
                self._keyframes[self.generation] = bytes(self.state)
        return self.generation

    def back(self, count: int = 1) -> int:
        return self.goto(self.generation - count)

    def goto(self, generation: int) -> int:
        """Jump to a generation, replaying from the nearest keyframe."""
        generation = max(0, generation)
        if generation > self.generation:
            return self.step(generation - self.generation)

        nearest = max(key for key in self._keyframes if key <= generation)
        self.state = array("B", self._keyframes[nearest])
        self.generation = nearest
        while self.generation < generation:
            self.state = self.rule.next_state(self.graph, self.state)
            self.generation += 1
        return self.generation

    def reset(self) -> int:
        self.state = array("B", self.initial)
        self.generation = 0
        return 0

    # -- inspection ------------------------------------------------------

    @property
    def population(self) -> int:
        return sum(self.state)

    def row_states(self, row: int) -> list[int]:
        return [self.state[i] for i in self.graph.row_indices(row)]

    def __repr__(self) -> str:
        return (
            f"<SurfaceAutomaton gen={self.generation} population={self.population} "
            f"{self.rule!r}>"
        )
