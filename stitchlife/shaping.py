"""
Deciding where a row's increases and decreases go.

Two different things are bundled up in "rules for increasing and decreasing",
and they get different answers here.

Pattern-driven shaping is deterministic: the armhole decrease is written in
the instructions and is not the automaton's business. `build_row_ops` with no
proposals places it in the conventional spot -- a stitch in from each end.

Automaton-driven shaping is the interesting one, and the trick to keeping the
result wearable is to treat it as a perturbation *around* the pattern's
required stitch count. A `DensityShaper` reads the row below and proposes
increases where the fabric is dense and decreases where it is empty; the
reconciler in `build_row_ops` then accepts a subset such that the row still
lands exactly on the count the pattern demands. Extra proposals may be
accepted in balanced increase/decrease pairs, which adds local flare and pull
that cancels out globally.

Physical guards, because knitters cannot make everything:

* shaping is kept `min_spacing` stitches apart -- increases packed together
  ruffle the fabric into a lettuce edge;
* a decrease consumes two parents, so accepted ops may never overlap;
* a decrease cannot run off the end of the row.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .graph import DEC, INC, KNIT, produced

__all__ = ["Proposal", "Occupancy", "DensityShaper", "build_row_ops", "ShapingError"]

#: columns consumed by an op placed at a position
_WIDTH = {INC: 1, DEC: 2}
#: change in row length caused by an op
_DELTA = {INC: 1, DEC: -1}


class ShapingError(ValueError):
    """Raised when a row's required stitch count cannot be met."""


@dataclass(frozen=True)
class Proposal:
    """A shaping op the automaton would like to perform.

    `position` is a column in the row below; `kind` is `INC` or `DEC`.
    """

    position: int
    kind: int
    score: float


class Occupancy:
    """Tracks which columns are spoken for, including a spacing margin.

    `min_spacing` is writable so the reconciler can relax it when a row is
    too narrow to place the shaping the pattern requires.
    """

    __slots__ = ("length", "min_spacing", "_blocked")

    def __init__(self, length: int, min_spacing: int = 2) -> None:
        self.length = length
        self.min_spacing = max(0, min_spacing)
        self._blocked = bytearray(length)

    def fits(self, position: int, width: int) -> bool:
        if position < 0 or position + width > self.length:
            return False
        lo = max(0, position - self.min_spacing)
        hi = min(self.length, position + width + self.min_spacing)
        return not any(self._blocked[lo:hi])

    def take(self, position: int, width: int) -> None:
        for column in range(position, position + width):
            self._blocked[column] = 1

    def snapshot(self) -> bytes:
        return bytes(self._blocked)

    def restore(self, snapshot: bytes) -> None:
        self._blocked = bytearray(snapshot)


class DensityShaper:
    """Proposes shaping from local automaton density.

    Dense neighbourhoods bulge outward (increase), empty ones pull in
    (decrease). Thresholds are fractions of the sampled window, so they do
    not need retuning when `window` changes.
    """

    __slots__ = ("window", "inc_threshold", "dec_threshold", "min_spacing", "texture_pairs")

    def __init__(
        self,
        window: int = 2,
        inc_threshold: float = 0.85,
        dec_threshold: float = 0.15,
        min_spacing: int = 3,
        texture_pairs: int = 1,
    ) -> None:
        if not 0.0 <= dec_threshold < inc_threshold <= 1.0:
            raise ValueError("need 0 <= dec_threshold < inc_threshold <= 1")
        self.window = max(1, window)
        self.inc_threshold = inc_threshold
        self.dec_threshold = dec_threshold
        self.min_spacing = min_spacing
        self.texture_pairs = texture_pairs

    def density(self, states: Sequence[int], column: int) -> float:
        lo = max(0, column - self.window)
        hi = min(len(states), column + self.window + 1)
        span = hi - lo
        return sum(states[lo:hi]) / span if span else 0.0

    def propose(self, states: Sequence[int]) -> list[Proposal]:
        out: list[Proposal] = []
        for column in range(len(states)):
            value = self.density(states, column)
            if value >= self.inc_threshold:
                out.append(Proposal(column, INC, value))
            elif value <= self.dec_threshold and column + 1 < len(states):
                out.append(Proposal(column, DEC, 1.0 - value))
        return out


def _candidate_order(length: int, width: int, at: str) -> list[int]:
    """Conventional placement positions, most preferred first.

    Shaping normally sits one stitch in from the edge rather than on it,
    which leaves a tidy selvedge to seam.
    """
    last = length - width
    if last < 0:
        return []
    if at == "left":
        return list(range(1, last + 1)) + [0]
    if at == "right":
        return list(range(last - 1, -1, -1)) + [last]
    if at == "center":
        middle = (length - width) // 2
        order = [middle]
        for step in range(1, length):
            for position in (middle - step, middle + step):
                if 0 <= position <= last:
                    order.append(position)
        return order
    # "both": alternate ends, working inward
    left = list(range(1, last + 1)) + [0]
    right = list(range(last - 1, -1, -1)) + [last]
    order = []
    for a, b in zip(left, right):
        order.append(a)
        order.append(b)
    return order


def _accept(
    accepted: dict[int, int],
    occupancy: Occupancy,
    position: int,
    kind: int,
) -> bool:
    width = _WIDTH[kind]
    if not occupancy.fits(position, width):
        return False
    occupancy.take(position, width)
    accepted[position] = kind
    return True


def _fill_from_pattern(
    accepted: dict[int, int],
    occupancy: Occupancy,
    kind: int,
    count: int,
    at: str,
) -> int:
    """Place `count` ops in conventional positions, returning how many landed.

    Spacing is relaxed step by step if the row is too narrow to honour it.
    The pattern's stitch count is a requirement and the anti-ruffling margin
    is only a preference, so a narrow row packs its shaping tighter rather
    than refusing to knit -- which is what a knitter does at a sleeve cuff.
    """
    placed = 0
    preferred = occupancy.min_spacing
    for spacing in range(preferred, -1, -1):
        occupancy.min_spacing = spacing
        for position in _candidate_order(occupancy.length, _WIDTH[kind], at):
            if placed >= count:
                break
            if _accept(accepted, occupancy, position, kind):
                placed += 1
        if placed >= count:
            break
    occupancy.min_spacing = preferred
    return placed


def build_row_ops(
    prev_len: int,
    delta: int,
    at: str = "both",
    proposals: Iterable[Proposal] | None = None,
    min_spacing: int = 2,
    texture_pairs: int = 0,
) -> list[int]:
    """Ops that knit a row of `prev_len + delta` stitches onto `prev_len`.

    Automaton `proposals` are honoured where they fit and where they move the
    row toward its required count; whatever the automaton fails to supply is
    placed conventionally, so the piece always comes out the size the pattern
    says it should.
    """
    if prev_len < 1:
        raise ShapingError("previous row is empty")
    target = prev_len + delta
    if target < 1:
        raise ShapingError(f"row would shrink to {target} stitches")

    occupancy = Occupancy(prev_len, min_spacing)
    accepted: dict[int, int] = {}

    ranked = sorted(proposals or (), key=lambda p: p.score, reverse=True)
    wanted = INC if delta > 0 else DEC
    remaining = abs(delta)

    # Honour the automaton first for the shaping the pattern requires.
    for proposal in ranked:
        if remaining <= 0:
            break
        if proposal.kind != wanted:
            continue
        if _accept(accepted, occupancy, proposal.position, proposal.kind):
            remaining -= 1

    # Anything it could not supply goes in the conventional place.
    if remaining > 0:
        placed = _fill_from_pattern(accepted, occupancy, wanted, remaining, at)
        remaining -= placed
        if remaining > 0:
            raise ShapingError(
                f"cannot place {remaining} more {'increase' if wanted == INC else 'decrease'}(s) "
                f"in a row of {prev_len} stitches at spacing {min_spacing}"
            )

    # Balanced extras: texture that changes the fabric without changing size.
    if texture_pairs > 0:
        spare_inc = [p for p in ranked if p.kind == INC and p.position not in accepted]
        spare_dec = [p for p in ranked if p.kind == DEC and p.position not in accepted]
        pairs = 0
        while pairs < texture_pairs and spare_inc and spare_dec:
            inc = spare_inc.pop(0)
            dec = spare_dec.pop(0)
            saved_occupancy = occupancy.snapshot()
            saved_accepted = dict(accepted)
            if _accept(accepted, occupancy, inc.position, INC) and _accept(
                accepted, occupancy, dec.position, DEC
            ):
                pairs += 1
            else:
                # Half a pair would change the row count; roll both back.
                occupancy.restore(saved_occupancy)
                accepted.clear()
                accepted.update(saved_accepted)

    ops: list[int] = []
    column = 0
    while column < prev_len:
        kind = accepted.get(column)
        if kind == DEC and column + 1 < prev_len:
            ops.append(DEC)
            column += 2
        elif kind == INC:
            ops.append(INC)
            column += 1
        else:
            ops.append(KNIT)
            column += 1

    built = produced(ops)
    if built != target:
        raise ShapingError(f"built a row of {built} stitches, needed {target}")
    return ops
