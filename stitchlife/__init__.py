"""
stitchlife -- knitting patterns as cellular automata.

The core carries no dependencies and does no drawing. It is built around one
separation: *fabric topology* (which stitches exist and what touches what,
determined by the pattern and its shaping) is not the same thing as *stitch
state* (what the automaton evolves). Keeping them apart is what lets a
garment shape come from a standard pattern rather than a hand-drawn border,
lets increases and decreases be first-class, and makes the timeline nearly
free.

    from stitchlife import Pattern, Knitter, ElementaryRule, render_text

    pattern = Pattern.load("fixtures/leaf.json")
    knitter = Knitter(pattern, ElementaryRule(110)).knit_all()
    print(render_text(knitter.graph, knitter.state))

Everything here is plain functions over flat arrays so the browser port is
mechanical: `array('i')` becomes `Int32Array`, `array('B')` becomes
`Uint8Array`, and the golden fixtures under `fixtures/` check that the port
produces the same fabric.
"""

from .chart import GLYPHS, layout, render_text
from .graph import DEC, INC, KNIT, OP_NAMES, GraphError, StitchGraph, consumed, produced
from .knitter import Knitter
from .pattern import (
    Gauge,
    Pattern,
    PatternError,
    RowBlock,
    RowSpec,
    Shaping,
    pattern_json_schema,
)
from .rules import ElementaryRule, LifeRule, seed_row
from .shaping import DensityShaper, Occupancy, Proposal, ShapingError, build_row_ops
from .surface import SurfaceAutomaton

__version__ = "0.1.0"

__all__ = [
    "DEC",
    "GLYPHS",
    "INC",
    "KNIT",
    "OP_NAMES",
    "DensityShaper",
    "ElementaryRule",
    "Gauge",
    "GraphError",
    "Knitter",
    "LifeRule",
    "Occupancy",
    "Pattern",
    "PatternError",
    "Proposal",
    "RowBlock",
    "RowSpec",
    "Shaping",
    "ShapingError",
    "StitchGraph",
    "SurfaceAutomaton",
    "build_row_ops",
    "consumed",
    "layout",
    "pattern_json_schema",
    "produced",
    "render_text",
    "seed_row",
]
