"""
Pattern IR: the machine-readable middle ground between a written knitting
pattern and a stitch graph.

Neither Knitspeak (good for authoring) nor knitout (good for machines) is a
convenient runtime representation, so patterns are compiled into this small
imperative row program first:

    {"name": "raglan front",
     "castOn": 84,
     "rows": [{"count": 20},
              {"count": 30, "every": 4, "shape": {"kind": "dec", "at": "both"}}],
     "bindOff": true}

That covers most garment pieces: cast on, work N rows, shape every N rows,
bind off. `Pattern.row_plan()` expands it into one `RowSpec` per fabric row,
which is all the knitting engine needs.

The JSON uses camelCase keys so the same documents load unchanged in the
browser port, and `pattern_json_schema()` returns a JSON Schema describing
them -- usable directly as a constrained-decoding target when a language
model is asked to turn raw pattern prose into this IR.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

__all__ = [
    "PatternError",
    "Gauge",
    "Shaping",
    "RowBlock",
    "RowSpec",
    "Pattern",
    "pattern_json_schema",
]


class PatternError(ValueError):
    """Raised when a pattern is malformed or knits to an impossible shape."""


PLACEMENTS = ("both", "left", "right", "center")
KINDS = ("inc", "dec")

#: A piece may never narrow past this many stitches while rows remain.
MIN_STITCHES = 2


@dataclass(frozen=True)
class Gauge:
    """Stitch dimensions, used for rendering aspect ratio and real-world size.

    A knit stitch is wider than it is tall. The ratio depends on yarn, needles
    and knitter, and falls roughly between 1:1 and 1:1.85 (stitches:rows).
    """

    stitches_per_cm: float = 2.2
    rows_per_cm: float = 3.0

    def __post_init__(self) -> None:
        if self.stitches_per_cm <= 0 or self.rows_per_cm <= 0:
            raise PatternError("gauge values must be positive")

    @property
    def aspect(self) -> float:
        """Width:height of a single stitch cell."""
        return self.rows_per_cm / self.stitches_per_cm

    def size_cm(self, stitches: int, rows: int) -> tuple[float, float]:
        return stitches / self.stitches_per_cm, rows / self.rows_per_cm

    def to_dict(self) -> dict[str, Any]:
        return {"stitchesPerCm": self.stitches_per_cm, "rowsPerCm": self.rows_per_cm}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Gauge":
        return Gauge(
            stitches_per_cm=float(data.get("stitchesPerCm", 2.2)),
            rows_per_cm=float(data.get("rowsPerCm", 3.0)),
        )


@dataclass(frozen=True)
class Shaping:
    """A shaping event applied to a row.

    `count` is stitches added or removed *per placement*, so "dec 1 at both
    ends" removes two stitches from the row.
    """

    kind: str = "dec"
    count: int = 1
    at: str = "both"

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise PatternError(f"shape kind must be one of {KINDS}, got {self.kind!r}")
        if self.at not in PLACEMENTS:
            raise PatternError(f"shape at must be one of {PLACEMENTS}, got {self.at!r}")
        if self.count < 1:
            raise PatternError("shape count must be at least 1")

    @property
    def placements(self) -> int:
        return 2 if self.at == "both" else 1

    @property
    def delta(self) -> int:
        """Signed change in stitch count when this shaping fires."""
        magnitude = self.count * self.placements
        return magnitude if self.kind == "inc" else -magnitude

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "count": self.count, "at": self.at}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Shaping":
        return Shaping(
            kind=str(data.get("kind", "dec")),
            count=int(data.get("count", 1)),
            at=str(data.get("at", "both")),
        )


@dataclass(frozen=True)
class RowBlock:
    """A run of rows, optionally carrying a repeating shaping instruction.

    Shaping fires on the first row of the block and every `every` rows after
    that -- rows 1, 1+every, 1+2*every ... within the block. This matches the
    common written form "dec row, then every 4th row".
    """

    count: int
    shape: Shaping | None = None
    every: int = 1
    label: str = ""

    def __post_init__(self) -> None:
        if self.count < 1:
            raise PatternError("row block count must be at least 1")
        if self.every < 1:
            raise PatternError("row block every must be at least 1")

    def fires_on(self, index: int) -> bool:
        """Does shaping fire on `index` (1-based within the block)?"""
        return self.shape is not None and (index - 1) % self.every == 0

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"count": self.count}
        if self.every != 1:
            out["every"] = self.every
        if self.shape is not None:
            out["shape"] = self.shape.to_dict()
        if self.label:
            out["label"] = self.label
        return out

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "RowBlock":
        shape = data.get("shape")
        return RowBlock(
            count=int(data["count"]),
            shape=Shaping.from_dict(shape) if shape else None,
            every=int(data.get("every", 1)),
            label=str(data.get("label", "")),
        )


@dataclass(frozen=True)
class RowSpec:
    """One fabric row after the block program has been expanded.

    `stitches` is the count this row must end up with; `delta` is the change
    from the row below. The automaton may propose its own increases and
    decreases, but a row still has to land on `stitches` for the piece to fit.
    """

    index: int
    stitches: int
    delta: int
    at: str
    label: str = ""

    @property
    def is_cast_on(self) -> bool:
        return self.index == 0


@dataclass(frozen=True)
class Pattern:
    """A single garment piece."""

    name: str
    cast_on: int
    blocks: tuple[RowBlock, ...] = ()
    gauge: Gauge = Gauge()
    bind_off: bool = True

    def __post_init__(self) -> None:
        if self.cast_on < MIN_STITCHES:
            raise PatternError(f"castOn must be at least {MIN_STITCHES}")
        # Surfaces the impossible-shape error at construction rather than
        # halfway through knitting.
        self.row_plan()

    @property
    def n_rows(self) -> int:
        """Total fabric rows, including the cast-on row."""
        return 1 + sum(block.count for block in self.blocks)

    def row_plan(self) -> list[RowSpec]:
        """Expand the block program into one `RowSpec` per fabric row."""
        plan = [RowSpec(index=0, stitches=self.cast_on, delta=0, at="both", label="cast on")]
        stitches = self.cast_on
        row_index = 1
        for block_no, block in enumerate(self.blocks):
            for i in range(1, block.count + 1):
                delta = block.shape.delta if block.fires_on(i) else 0
                at = block.shape.at if block.shape is not None else "both"
                stitches += delta
                if stitches < MIN_STITCHES:
                    raise PatternError(
                        f"row {row_index} of block {block_no} narrows to {stitches} "
                        f"stitches; minimum is {MIN_STITCHES}"
                    )
                plan.append(
                    RowSpec(
                        index=row_index,
                        stitches=stitches,
                        delta=delta,
                        at=at,
                        label=block.label,
                    )
                )
                row_index += 1
        return plan

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "castOn": self.cast_on,
            "gauge": self.gauge.to_dict(),
            "rows": [block.to_dict() for block in self.blocks],
            "bindOff": self.bind_off,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Pattern":
        if not isinstance(data, dict):
            raise PatternError("pattern must be a JSON object")
        if "castOn" not in data:
            raise PatternError("pattern is missing required key 'castOn'")
        rows = data.get("rows", [])
        if not isinstance(rows, list):
            raise PatternError("pattern 'rows' must be a list")
        gauge = data.get("gauge")
        return Pattern(
            name=str(data.get("name", "untitled")),
            cast_on=int(data["castOn"]),
            blocks=tuple(RowBlock.from_dict(row) for row in rows),
            gauge=Gauge.from_dict(gauge) if gauge else Gauge(),
            bind_off=bool(data.get("bindOff", True)),
        )

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @staticmethod
    def from_json(text: str) -> "Pattern":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise PatternError(f"pattern is not valid JSON: {exc}") from exc
        return Pattern.from_dict(data)

    @staticmethod
    def load(path: str) -> "Pattern":
        with open(path, "r", encoding="utf-8") as handle:
            return Pattern.from_json(handle.read())

    def describe(self) -> str:
        """Render the pattern back into readable instructions.

        Round-tripping IR to prose is how a parse gets verified: a
        mis-parsed pattern otherwise produces a silently wrong garment.
        """
        lines = [f"{self.name}", f"Cast on {self.cast_on} sts."]
        for block in self.blocks:
            prefix = f"{block.label}: " if block.label else ""
            if block.shape is None:
                lines.append(f"{prefix}Work {block.count} rows even.")
                continue
            verb = "Increase" if block.shape.kind == "inc" else "Decrease"
            where = {
                "both": "at each end",
                "left": "at the beginning",
                "right": "at the end",
                "center": "at the center",
            }[block.shape.at]
            cadence = "every row" if block.every == 1 else f"every {block.every} rows"
            lines.append(
                f"{prefix}Work {block.count} rows, {verb.lower()} {block.shape.count} st "
                f"{where} on the first row and {cadence} thereafter."
            )
        final = self.row_plan()[-1].stitches
        lines.append(f"Bind off all {final} sts." if self.bind_off else f"{final} sts remain.")
        return "\n".join(lines)


def pattern_json_schema() -> dict[str, Any]:
    """JSON Schema for the pattern IR.

    Handed to a language model as a constrained-decoding target so that
    "raw pattern prose in, valid IR out" cannot produce free-form text. The
    model normalizes; the compiler in `graph.py` does the real work.
    """
    shape_schema = {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": list(KINDS)},
            "count": {"type": "integer", "minimum": 1},
            "at": {"type": "string", "enum": list(PLACEMENTS)},
        },
        "required": ["kind"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "castOn": {"type": "integer", "minimum": MIN_STITCHES},
            "gauge": {
                "type": "object",
                "properties": {
                    "stitchesPerCm": {"type": "number", "exclusiveMinimum": 0},
                    "rowsPerCm": {"type": "number", "exclusiveMinimum": 0},
                },
                "additionalProperties": False,
            },
            "rows": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer", "minimum": 1},
                        "every": {"type": "integer", "minimum": 1},
                        "label": {"type": "string"},
                        "shape": shape_schema,
                    },
                    "required": ["count"],
                    "additionalProperties": False,
                },
            },
            "bindOff": {"type": "boolean"},
        },
        "required": ["castOn", "rows"],
        "additionalProperties": False,
    }
