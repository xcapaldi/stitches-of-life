"""
Layout and text charting.

Layout is deliberately a separate concern from topology. `layout()` returns
nothing but stitch centres in stitch-width/row-height units, which is all a
canvas or SVG renderer needs, and centring each row on the widest row is
enough to make the silhouette appear for free -- decreases visibly draw the
fabric in, increases flare it out. (A relaxation pass in the style of a
stitch map would be more faithful still, and can replace this function
without anything else changing.)

`render_text` is the same layout in ASCII: cast-on row at the bottom, as on a
real chart. It exists so the engine can be checked without a display, and so
golden fixtures are readable in a diff.
"""

from __future__ import annotations

from typing import Sequence

from .graph import DEC, INC, KNIT, StitchGraph
from .pattern import Gauge

__all__ = ["layout", "render_text", "GLYPHS"]

#: (dead, live) glyph per op, chosen so shaping is legible in plain text
GLYPHS = {
    KNIT: (".", "#"),
    INC: (",", "V"),
    DEC: ("`", "A"),
}


def layout(graph: StitchGraph, gauge: Gauge | None = None) -> list[tuple[float, float]]:
    """Stitch centres, one per stitch index.

    X is in stitch widths and Y in row heights, with row 0 at y = 0 and the
    fabric growing upward. Multiply by the cell size a renderer wants; use
    `Gauge.aspect` to keep stitches wider than they are tall.
    """
    widest = graph.max_row_len
    aspect = gauge.aspect if gauge is not None else 1.0
    out: list[tuple[float, float]] = []
    for row in range(graph.n_rows):
        count = graph.row_len[row]
        inset = (widest - count) / 2.0
        for column in range(count):
            out.append(((inset + column + 0.5) * aspect, row + 0.5))
    return out


def render_text(
    graph: StitchGraph,
    state: Sequence[int] | None = None,
    mark_shaping: bool = True,
    show_counts: bool = False,
) -> str:
    """Chart the fabric as text, cast-on row last.

    With `mark_shaping`, stitches born of an increase or decrease get their
    own glyphs (V/v and A/a) so shaping reads at a glance.
    """
    widest = graph.max_row_len
    lines: list[str] = []
    for row in range(graph.n_rows - 1, -1, -1):
        count = graph.row_len[row]
        pad = " " * ((widest - count) // 2)
        cells = []
        for index in graph.row_indices(row):
            alive = 1 if state is not None and state[index] else 0
            op = graph.op_of[index] if mark_shaping else 0
            cells.append(GLYPHS.get(op, GLYPHS[0])[alive])
        line = pad + "".join(cells)
        if show_counts:
            line = f"{line.ljust(widest + len(pad))}  {count:>4} sts  row {row}"
        lines.append(line.rstrip() if not show_counts else line)
    return "\n".join(lines)
