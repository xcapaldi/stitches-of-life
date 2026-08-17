"""
The stitch graph: fabric topology, separated from stitch state.

A stitch's identity is its position in the fabric's construction, not an
(x, y) coordinate. It has one or two parents (the stitches below that it is
knitted through), one or two children, and left/right siblings in its own
row. Increases and decreases change that wiring without the automaton
needing to know anything about them:

    knit   1 parent  -> 1 child
    inc    1 parent  -> 2 children   (kfb, M1, yo)
    dec    2 parents -> 1 child      (k2tog, ssk)

Storage is flat arrays rather than an object per stitch. Real garments run
to six figures of stitches, and `array('i')` maps one-to-one onto an
`Int32Array` in the browser port.
"""

from __future__ import annotations

from array import array
from typing import Iterable, Iterator

__all__ = ["KNIT", "INC", "DEC", "OP_NAMES", "GraphError", "StitchGraph", "produced", "consumed"]

KNIT = 0
INC = 1
DEC = 2

OP_NAMES = {KNIT: "knit", INC: "inc", DEC: "dec"}

#: parents consumed and children produced by each op
_CONSUMES = {KNIT: 1, INC: 1, DEC: 2}
_PRODUCES = {KNIT: 1, INC: 2, DEC: 1}


class GraphError(ValueError):
    """Raised when a row of ops does not fit the row below it."""


def _lookup(table: dict[int, int], op: int) -> int:
    try:
        return table[op]
    except KeyError:
        raise GraphError(f"unknown op {op!r}") from None


def consumed(ops: Iterable[int]) -> int:
    """Stitches the op sequence takes off the needle."""
    return sum(_lookup(_CONSUMES, op) for op in ops)


def produced(ops: Iterable[int]) -> int:
    """Stitches the op sequence puts back on the needle."""
    return sum(_lookup(_PRODUCES, op) for op in ops)


class StitchGraph:
    """Rows of stitches wired parent-to-child.

    Rows are contiguous index ranges, so a stitch's row and column are
    recoverable from its index alone and neighbour lookups stay array
    accesses rather than dictionary probes.
    """

    __slots__ = (
        "parent_a",
        "parent_b",
        "child_a",
        "child_b",
        "op_of",
        "row_start",
        "row_len",
    )

    def __init__(self) -> None:
        self.parent_a = array("i")
        self.parent_b = array("i")
        self.child_a = array("i")
        self.child_b = array("i")
        self.op_of = array("b")
        self.row_start: list[int] = []
        self.row_len: list[int] = []

    # -- construction ----------------------------------------------------

    def cast_on(self, count: int) -> int:
        """Create the foundation row. Its stitches have no parents."""
        if self.row_start:
            raise GraphError("cast_on may only be called on an empty graph")
        if count < 1:
            raise GraphError("cast_on count must be at least 1")
        self.row_start.append(0)
        self.row_len.append(count)
        for _ in range(count):
            self._append_stitch(-1, -1, KNIT)
        return 0

    def add_row(self, ops: list[int]) -> int:
        """Knit one row using `ops`, returning the new row index."""
        if not self.row_start:
            raise GraphError("cast on before adding rows")
        prev_row = len(self.row_start) - 1
        prev_start = self.row_start[prev_row]
        prev_len = self.row_len[prev_row]

        need = consumed(ops)
        if need != prev_len:
            raise GraphError(
                f"ops consume {need} stitches but row {prev_row} has {prev_len}"
            )
        new_len = produced(ops)
        if new_len < 1:
            raise GraphError("a row must produce at least one stitch")

        new_start = len(self.parent_a)
        self.row_start.append(new_start)
        self.row_len.append(new_len)

        cursor = prev_start
        for op in ops:
            if op == KNIT:
                child = self._append_stitch(cursor, -1, KNIT)
                self._attach_child(cursor, child)
                cursor += 1
            elif op == INC:
                first = self._append_stitch(cursor, -1, INC)
                second = self._append_stitch(cursor, -1, INC)
                self._attach_child(cursor, first)
                self._attach_child(cursor, second)
                cursor += 1
            elif op == DEC:
                child = self._append_stitch(cursor, cursor + 1, DEC)
                self._attach_child(cursor, child)
                self._attach_child(cursor + 1, child)
                cursor += 2
            else:
                raise GraphError(f"unknown op {op!r}")
        return len(self.row_start) - 1

    def pop_row(self) -> int:
        """Un-knit the most recent row, returning how many stitches went.

        Knitting is monotone -- a finished row is never modified -- so
        stepping backward through the fabric is just truncation.
        """
        if len(self.row_start) <= 1:
            raise GraphError("cannot pop the cast-on row")
        start = self.row_start.pop()
        count = self.row_len.pop()

        del self.parent_a[start:]
        del self.parent_b[start:]
        del self.child_a[start:]
        del self.child_b[start:]
        del self.op_of[start:]

        for i in self.row_indices(len(self.row_start) - 1):
            self.child_a[i] = -1
            self.child_b[i] = -1
        return count

    def _append_stitch(self, parent_a: int, parent_b: int, op: int) -> int:
        index = len(self.parent_a)
        self.parent_a.append(parent_a)
        self.parent_b.append(parent_b)
        self.child_a.append(-1)
        self.child_b.append(-1)
        self.op_of.append(op)
        return index

    def _attach_child(self, parent: int, child: int) -> None:
        if self.child_a[parent] < 0:
            self.child_a[parent] = child
        else:
            self.child_b[parent] = child

    # -- queries ---------------------------------------------------------

    @property
    def n_rows(self) -> int:
        return len(self.row_start)

    @property
    def n_stitches(self) -> int:
        return len(self.parent_a)

    @property
    def max_row_len(self) -> int:
        return max(self.row_len) if self.row_len else 0

    def row_indices(self, row: int) -> range:
        start = self.row_start[row]
        return range(start, start + self.row_len[row])

    def row_of(self, index: int) -> int:
        """Binary search for the row containing `index`."""
        lo, hi = 0, len(self.row_start) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.row_start[mid] <= index:
                lo = mid
            else:
                hi = mid - 1
        return lo

    def column_of(self, index: int) -> int:
        return index - self.row_start[self.row_of(index)]

    def left(self, index: int) -> int:
        row = self.row_of(index)
        return index - 1 if index > self.row_start[row] else -1

    def right(self, index: int) -> int:
        row = self.row_of(index)
        return index + 1 if index < self.row_start[row] + self.row_len[row] - 1 else -1

    def parents(self, index: int) -> tuple[int, ...]:
        return tuple(p for p in (self.parent_a[index], self.parent_b[index]) if p >= 0)

    def children(self, index: int) -> tuple[int, ...]:
        return tuple(c for c in (self.child_a[index], self.child_b[index]) if c >= 0)

    def neighbors(self, index: int) -> list[int]:
        """Stitches touching `index` in the fabric.

        Siblings, parents and children give only the four cardinal
        neighbours. The diagonals of a knit fabric are the parents' and
        children's own siblings, so those are included too -- which makes
        this exactly the Moore 8-neighbourhood in the interior of a plain
        rectangle, and something smaller at edges and shaping points.

        Degree therefore varies, which is why the Life rule normalizes its
        thresholds by degree rather than testing raw counts.
        """
        out: list[int] = []
        seen = {index}

        def push(value: int) -> None:
            if value >= 0 and value not in seen:
                seen.add(value)
                out.append(value)

        push(self.left(index))
        push(self.right(index))
        for relative in self.parents(index) + self.children(index):
            push(relative)
            push(self.left(relative))
            push(self.right(relative))
        return out

    def iter_rows(self) -> Iterator[range]:
        for row in range(self.n_rows):
            yield self.row_indices(row)

    def __repr__(self) -> str:
        return (
            f"<StitchGraph rows={self.n_rows} stitches={self.n_stitches} "
            f"widest={self.max_row_len}>"
        )
