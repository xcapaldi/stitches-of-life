# stitches-of-life

Design a knitted hat by running Conway's Game of Life — or a Wolfram elementary
automaton — over the actual stitch map of the hat, then step back through the
history to the generation you like and export the knitting instructions.

Runs entirely in the browser. No build step, no dependencies.

## Running it

Because the app is made of ES modules it needs to be served over HTTP rather
than opened from the file system:

```sh
python3 -m http.server 8080   # or: npm start
```

Then open <http://localhost:8080>.

Tests (pure logic, no browser needed):

```sh
npm test
```

## The hat

The stitch counts follow the *Hats That Fit* worksheet by Nancy Lindberg:

| | |
|---|---|
| A | head circumference at the thickest part above the ears |
| B | ear lobe to ear lobe, over the top of the head |
| C | body stitches = (A − ease) × stitch gauge |
| D | cuff stitches = C − 10% of C |
| E | body length = B ÷ 4 + 1" |

Choose a cuff (hemmed, rolled or ribbed) and a crown (square, pointed or
round), and the app lays out every round of the hat: the cuff at D stitches,
the increase round to C, the body, and the crown decreases running down to the
last 8 stitches.

## The map is not a grid

A hat is a tube that narrows at the top, so the map the automaton runs on is
not rectangular:

- **Every round wraps.** The last stitch of a round is beside the first.
- **Rounds change width.** The increase round after the cuff adds stitches;
  every crown decrease round takes 8 (or 4) away.

Each stitch is treated as an arc of its round. Two stitches in neighbouring
rounds touch when their arcs overlap, once the arc has been widened by one
stitch on each side — which gives the familiar eight neighbours where rounds
are the same width, and merges neighbours sensibly where a decrease pulls two
stitches into one. The relation is then made mutual, so if a stitch influences
another, that stitch influences it back.

Chart rounds are listed at the stitch count they *end* with, so a decrease
round is one stitch narrower per decrease than the round below it.

## Simulations

**2D** — a life-like rule in `B/S` notation over the whole map. Ten presets
are included (Life, HighLife, Day & Night, Maze, Seeds, Replicator and more) or
type your own. The app watches for still lifes and oscillators and pauses when
the design stops changing.

**1D** — a Wolfram elementary rule (0–255). One round is worked out from the
round before it, so each generation adds one round to the hat. The first
generation can sit at the **bottom**, growing towards the crown, or at the
**top**, growing down towards the cuff. Rule 90 from a single stitch gives a
Sierpinski triangle that runs up the hat and through the crown shaping.

## History

Every generation is kept. Step forward and back, drag the generation slider, or
click the population timeline to jump around, and export whichever generation
you like the look of. Drawing on the chart edits the current generation and
discards the ones after it.

Everything is deterministic: the same measurements, rule and random-seed number
always give the same hat, which is what makes saved projects small.

## Ribbing and the crown

The cuff and the crown can each be part of the map or left out of it:

- **In the map** — those rounds evolve with everything else. A ribbed cuff can
  be used as the automaton's first generation, so the ribbing grows into the
  pattern.
- **Out of the map** — the rounds hold still and are worked plain (a ribbed
  cuff keeps its K2/P2), but they still act as neighbours, so the pattern in
  the body reacts to them.

## Exports

- **Pattern** (`.md`) — measurements, calculations, cuff/body/crown
  instructions, a round-by-round list of the stitches in the order they are
  worked, and a text chart.
- **Chart** (`.png`) — the chart at 120 dpi.
- **Project** (`.json`) — everything needed to reopen the design.

Charts are read right to left, bottom round first, the way knitting charts are.

## Working as colourwork or texture

The two cell states are either two colours (MC and CC) for stranded
colourwork, or knit and purl for a textured hat. The choice only changes how
the pattern is written up.

## Keyboard

| | |
|---|---|
| space | play / pause |
| ← → | step back / forward |
| R | back to the first generation |
| F | fit the chart to the window |

Drag on the chart to draw. Shift-drag or right-drag to pan, scroll to zoom.

## History of this repo

This started as a Python/pygame prototype (`stitch.py`) that ran Life on a flat
grid. It has been rewritten in JavaScript so it runs in a browser, narrowed to
hats, and given the non-uniform topology, history and pattern export described
above. The prototype is still in the git history.
