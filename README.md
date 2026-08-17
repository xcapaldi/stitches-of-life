# stitches-of-life

Generate knitting patterns by running cellular automata on a knit surface.

The garment shape comes from a standard-shaped pattern rather than a hand-drawn
border, increases and decreases are first-class, and the whole construction can
be stepped forward and backward.

```
$ python -m stitchlife fixtures/leaf.json --counts
leaf: <Knitter 'leaf' row 34/34 ElementaryRule(110)>
       #.#..                   5 sts  row 34
       #A#.`                   5 sts  row 33
      #..#...                 7 sts  row 32
      #A##.`.                 7 sts  row 31
     ###.#....               9 sts  row 30
     #`###..`.               9 sts  row 29
    #.##.#.....            11 sts  row 28
       ...
      ##.#...                 7 sts  row 2
      .VV#.,,                 7 sts  row 1
       ..#..                   5 sts  row 0
```

`#` is a live stitch and `.` a dead one; `V`/`,` mark stitches born of an
increase and `A`/`` ` `` those born of a decrease.

## The idea

One separation runs through the whole design: **fabric topology is not stitch
state.**

*Topology* is which stitches exist and what touches what. It comes from the
pattern and its shaping, and it is a graph rather than a grid — a stitch's
identity is its position in the fabric's construction, not an `(x, y)`
coordinate. Every stitch has one or two parents (the stitches below that it is
knitted through), one or two children, and left/right siblings:

```
knit   1 parent  -> 1 child
inc    1 parent  -> 2 children    (kfb, M1, yo)
dec    2 parents -> 1 child       (k2tog, ssk)
```

*State* is what the automaton evolves on top of that topology — live/dead
today, knit/purl or two colours of yarn tomorrow.

Because they are separate, shaping a garment does not require teaching the
automaton anything about garments, and running an automaton does not require
drawing a border by hand.

## Two temporal models

Both run on the same graph.

**Rows as generations** (`Knitter`, `ElementaryRule`). Row *t+1* is computed
from row *t*, so the fabric you are looking at is the automaton's spacetime
diagram — the same relationship a Wolfram elementary CA has to its own history.
This matches how knitting actually works, and it is the model in which
increases and decreases mean something.

**The surface as the grid** (`SurfaceAutomaton`, `LifeRule`). The whole
finished piece is iterated, generation by generation, which is Conway's Game of
Life on a non-uniform surface. The fabric no longer grows, so history is kept
as snapshots.

Neighbourhood degree is 8 only in the interior of a plain rectangle; at edges
and at every increase and decrease it is smaller. `LifeRule` therefore rescales
neighbour counts by degree before testing its thresholds, so stitches near
shaping are not doing something different for an uninteresting reason. Pass
`normalize=False` for the literal rule.

## Stepping backward

Knitting is monotone — a row, once worked, is never modified — so in row-wise
mode the fabric *is* the timeline and un-knitting is truncation rather than an
undo log. `Knitter.step(-1)`, `.goto_row(n)` and `.reset()` are all cheap, and
because rules and seeding are deterministic, anything stepped back to can be
stepped forward into again and come out identical.

Surface mode does need history. Snapshots are a byte per stitch (a 200-stitch
by 300-row piece is 60 KB per generation), and `keyframe_every` trades that
memory for recomputation.

## Increases and decreases

Two different questions hide in "rules for shaping", and they get different
answers.

Pattern-driven shaping is deterministic: the armhole decrease is written in the
instructions and is not the automaton's business. It goes in the conventional
place, a stitch in from each end.

Automaton-driven shaping treats the automaton as a *perturbation around the
pattern's required stitch count*. A `DensityShaper` reads the row below and
proposes increases where the fabric is dense and decreases where it is empty;
the reconciler accepts a subset such that the row still lands exactly on the
count the pattern demands, filling any shortfall conventionally. Extra
proposals are accepted in balanced increase/decrease pairs, adding local flare
and pull that cancels out globally — so the texture drives the shape without
the piece ceasing to be wearable.

Guards, because knitters cannot make everything: shaping is kept `min_spacing`
stitches apart (packed increases ruffle the fabric into a lettuce edge),
accepted ops may never overlap, and a decrease cannot run off the end of a row.
The spacing margin is a preference and gives way when a narrow row cannot
otherwise meet its required count.

Short rows are the third shaping op and are not implemented; they break the
row-as-a-contiguous-range assumption and want their own design pass.

## Patterns

Neither Knitspeak (good for authoring) nor knitout (good for machines) is a
convenient runtime representation, so patterns compile through a small
imperative row program:

```json
{"name": "raglan front",
 "castOn": 48,
 "rows": [{"count": 10, "label": "hem"},
          {"count": 12, "every": 4, "shape": {"kind": "dec", "count": 1, "at": "both"}}],
 "bindOff": true}
```

Shaping fires on the first row of a block and every `every` rows after that,
matching the written form "dec row, then every 4th row". `Pattern.row_plan()`
expands this into the stitch count every row must hit; `Pattern.describe()`
renders it back into prose, which is how a parse gets checked — a mis-parsed
pattern otherwise produces a silently wrong garment.

Fixtures live in `fixtures/`: a plain `scarf`, a `leaf` that widens then
tapers, and a `raglan-front` with waist and raglan shaping.

## Usage

```bash
python -m stitchlife fixtures/raglan-front.json --counts
python -m stitchlife fixtures/raglan-front.json --rule 30 --shape
python -m stitchlife fixtures/scarf.json --seed-kind random --seed 7 --surface 4
python -m stitchlife fixtures/leaf.json --rows 12          # stop partway
python -m stitchlife fixtures/leaf.json --json             # machine-readable fabric
python -m stitchlife --schema                              # pattern IR JSON Schema
```

```python
from stitchlife import Pattern, Knitter, ElementaryRule, DensityShaper, render_text

knitter = Knitter(
    Pattern.load("fixtures/raglan-front.json"),
    ElementaryRule(110),
    shaper=DensityShaper(),
).knit_all()

print(render_text(knitter.graph, knitter.state))
knitter.step(-10)          # back ten rows
knitter.goto_row(3)        # or jump anywhere
```

## Layout and rendering

`layout()` returns nothing but stitch centres in stitch-width/row-height units,
which is all a canvas or SVG renderer needs. Centring each row on the widest
row is enough for the silhouette to appear on its own — decreases visibly draw
the fabric in, increases flare it out. A relaxation pass in the style of a
stitch map would be more faithful and can replace that function without
anything else changing.

`Gauge` carries the wale-to-course ratio, which falls between roughly 1:1 and
1:1.85 (stitches:rows) depending on yarn, needles and knitter — stitches are
wider than they are tall, and charts that ignore this lie about the shape.

## Tests

```bash
python -m unittest discover -s tests -t .
```

Golden fixtures under `fixtures/goldens/` record complete worked fabrics.
Regenerate deliberately after an intended change:

```bash
python -m tests.test_goldens --regen
```

## Layout of the code

| module | what it holds |
| --- | --- |
| `stitchlife/pattern.py` | pattern IR, validation, JSON, prose round-trip, JSON Schema |
| `stitchlife/graph.py` | the stitch graph: flat arrays, ops, neighbourhoods |
| `stitchlife/rules.py` | `ElementaryRule` (row-wise) and `LifeRule` (surface) |
| `stitchlife/shaping.py` | shaping proposals and the count reconciler |
| `stitchlife/knitter.py` | the row-wise engine and its timeline |
| `stitchlife/surface.py` | the surface engine and its snapshot timeline |
| `stitchlife/chart.py` | layout and text charting |
| `stitchlife/cli.py` | command line front end |

The core has no dependencies and does no drawing. `stitch.py`, the original
pygame prototype, is left as it was; see [docs/porting.md](docs/porting.md) for
how it and the browser port relate to this core.
