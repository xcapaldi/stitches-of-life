"""
Automaton rules over the stitch graph.

Two temporal models are supported, because they suit different questions and
the same graph serves both.

`ElementaryRule` treats each *row* as a generation: row t+1 is computed from
row t and nothing else, so the fabric you are looking at is the automaton's
spacetime diagram. This is the model that matches how knitting actually
works, and the one in which increases and decreases mean something.

`LifeRule` treats the whole finished surface as the grid and iterates it,
which is Conway's Game of Life on a non-uniform surface -- the original idea,
and the mode the pygame prototype runs.
"""

from __future__ import annotations

from array import array

from .graph import DEC, INC, KNIT, StitchGraph

__all__ = ["ElementaryRule", "LifeRule", "seed_row"]


class ElementaryRule:
    """A Wolfram elementary cellular automaton evaluated along the fabric.

    Each new stitch reads a three-cell window of the row below -- its
    parent and that parent's siblings -- giving an eight-entry lookup keyed
    by the rule number. Rule 110 and rule 30 are the interesting ones; 110
    is Turing complete and produces the triangular fabric people knit into
    scarves.

    Shaping is handled without special cases:

    * a decrease has two parents, so the window's centre is the OR of both
      and its edges come from outside the consumed pair;
    * an increase has one parent and two children, which are given the same
      window -- live regions widen at an increase, which is the visible
      behaviour you want.
    """

    __slots__ = ("number",)

    def __init__(self, number: int = 110) -> None:
        if not 0 <= number <= 255:
            raise ValueError("elementary rule number must be in 0..255")
        self.number = number

    def cell(self, prev: "array[int] | list[int]", i: int, j: int) -> int:
        """Evaluate the window spanning parents `i`..`j` of the row below."""
        left = prev[i - 1] if i - 1 >= 0 else 0
        centre = prev[i] | prev[j]
        right = prev[j + 1] if j + 1 < len(prev) else 0
        index = (left << 2) | (centre << 1) | right
        return (self.number >> index) & 1

    def next_row(self, prev: "array[int] | list[int]", ops: list[int]) -> list[int]:
        """States for the row produced by applying `ops` to `prev`."""
        out: list[int] = []
        cursor = 0
        for op in ops:
            if op == KNIT:
                out.append(self.cell(prev, cursor, cursor))
                cursor += 1
            elif op == INC:
                value = self.cell(prev, cursor, cursor)
                out.append(value)
                out.append(value)
                cursor += 1
            elif op == DEC:
                out.append(self.cell(prev, cursor, cursor + 1))
                cursor += 2
            else:
                raise ValueError(f"unknown op {op!r}")
        return out

    def __repr__(self) -> str:
        return f"ElementaryRule({self.number})"


class LifeRule:
    """Conway-style birth/survival rule over the whole stitch graph.

    Neighbourhood degree is 8 only in the interior of a plain rectangle. At
    edges, and at every increase or decrease, it is smaller. Comparing raw
    live-neighbour counts against 2/3 would therefore make stitches near
    shaping behave differently for an uninteresting reason, so by default
    counts are rescaled to their eight-neighbour equivalent before the
    thresholds are tested. Pass ``normalize=False`` for the literal rule.
    """

    __slots__ = ("born", "survive", "normalize")

    def __init__(
        self,
        born: tuple[int, ...] = (3,),
        survive: tuple[int, ...] = (2, 3),
        normalize: bool = True,
    ) -> None:
        self.born = frozenset(born)
        self.survive = frozenset(survive)
        self.normalize = normalize

    @staticmethod
    def from_string(spec: str, normalize: bool = True) -> "LifeRule":
        """Parse the usual ``B3/S23`` notation."""
        try:
            born_part, survive_part = spec.upper().split("/")
            if not born_part.startswith("B") or not survive_part.startswith("S"):
                raise ValueError
            born = tuple(int(c) for c in born_part[1:])
            survive = tuple(int(c) for c in survive_part[1:])
        except ValueError as exc:
            raise ValueError(f"expected B/S notation like 'B3/S23', got {spec!r}") from exc
        return LifeRule(born=born, survive=survive, normalize=normalize)

    def next_state(self, graph: StitchGraph, state: "array[int]") -> "array[int]":
        out = array("B", bytes(len(state)))
        for i in range(graph.n_stitches):
            neighbors = graph.neighbors(i)
            degree = len(neighbors)
            if degree == 0:
                continue
            live = sum(state[n] for n in neighbors)
            if self.normalize and degree != 8:
                live = round(live * 8 / degree)
            thresholds = self.survive if state[i] else self.born
            out[i] = 1 if live in thresholds else 0
        return out

    def __repr__(self) -> str:
        born = "".join(str(b) for b in sorted(self.born))
        survive = "".join(str(s) for s in sorted(self.survive))
        return f"LifeRule(B{born}/S{survive}, normalize={self.normalize})"


def seed_row(width: int, kind: str = "center", seed: int | None = None) -> list[int]:
    """Initial states for the cast-on row.

    Deterministic given `seed`, which is what makes the timeline replayable
    rather than something that has to be snapshotted.
    """
    if kind == "center":
        row = [0] * width
        row[width // 2] = 1
        return row
    if kind == "edges":
        row = [0] * width
        row[0] = 1
        row[-1] = 1
        return row
    if kind == "full":
        return [1] * width
    if kind == "random":
        import random

        rng = random.Random(seed)
        return [rng.randint(0, 1) for _ in range(width)]
    raise ValueError(f"unknown seed kind {kind!r}")
