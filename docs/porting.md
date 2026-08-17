# Porting to the browser

The destination is a browser app, and Chrome's built-in model only exists
there, so this core was written to be ported rather than to be permanent.

## What was done to make the port mechanical

**Flat typed arrays, not an object per stitch.** `StitchGraph` keeps
`array('i')` for parent and child links and `array('B')` for state. Those are
`Int32Array` and `Uint8Array` with no change in meaning. A real garment runs to
six figures of stitches, and an object per stitch with a dictionary probe per
neighbour does not survive that in either language.

**No global registry.** The pygame prototype keeps every stitch in a
class-level `Stitch.stitches` dict, which allows exactly one fabric per
process, cannot be snapshotted, and makes the timeline and the tests awkward.
Each `StitchGraph` here is an ordinary value.

**No rendering in the core.** Nothing below `chart.py` knows what a pixel is.
`layout()` returns stitch centres in stitch-width and row-height units;
`pygame.draw.rect` becomes a Canvas 2D `fillRect` and nothing else moves.
Canvas handles tens of thousands of rects comfortably; WebGL is a later problem
if it ever becomes one.

**Rules that are pure functions.** `ElementaryRule.next_row(prev, ops)` takes
a sequence and a list of ints and returns a list of ints. It touches no graph
and no global state, which is what makes it trivially portable and trivially
testable.

## The contract

`fixtures/goldens/` holds complete worked fabrics for a set of
pattern/rule/seed combinations. The JS implementation is correct when it
reproduces those files byte for byte, so "did the port work" is a test run
rather than a judgement call. `Knitter.to_dict()` emits the same fabric as
JSON if a structural comparison is more convenient than a textual one.

Two details the port must match exactly, because they are choices rather than
consequences:

* An increase gives both of its children the same automaton state.
* A decrease ORs the state of its two parents to form the centre of its window.

## Skip Pyodide

Running the Python core in the browser through Pyodide buys a working prototype
at the cost of a large runtime download, a slow start, and an awkward seam at
exactly the place the interesting work happens — the model integration. The
core is small; port it.

## The model front end

Chrome's built-in **Prompt API** runs Gemini Nano, needs no download, and is
Chrome-only; it has spent time behind flags and origin trials, so check its
current availability before depending on it. Running real Gemma weights
yourself through MediaPipe LLM Inference or WebLLM on WebGPU works across
browsers instead, at the cost of a several-hundred-megabyte download. Either
choice fits behind the same interface.

What matters more than the choice is the shape of the integration:

**The model never emits the design.** Its only job is raw pattern prose in,
pattern IR out. `pattern_json_schema()` returns a JSON Schema describing that
IR, suitable for constrained decoding (the Prompt API takes one as a response
constraint), so the model cannot answer with free-form text. A deterministic
compiler turns the IR into a stitch graph, and `Pattern.from_dict` rejects
anything malformed before it reaches the graph.

**Parse deterministically first.** A Knitspeak grammar handles most
well-formed patterns without a model at all. Reach for the model only for the
messy remainder — the abbreviations, the prose asides, the parts real patterns
are inconsistent about. On-device models are small and will confidently invent
stitch counts.

**Round-trip to verify.** `Pattern.describe()` renders the IR back into
readable instructions. Show the knitter what was understood before knitting
anything, because a misparse otherwise produces a silently wrong garment and no
error at all.

## Formats worth exporting to later

* **Knitspeak** — the standard written form for hand knitting, and the natural
  input format. `Pattern.describe()` is a rough first step toward emitting it.
* **knitout** — an open, machine-independent format with needle-level
  operations, from the CMU Textiles Lab. Too low-level to author in, but the
  right target if a machine should ever knit the output. The op vocabulary here
  (`knit`, `inc`, `dec`) maps onto it through transfers.
* **Craft Yarn Council chart symbols** — the standard glyph set, and the
  vocabulary a graphical chart renderer should speak. `chart.py` uses ASCII
  stand-ins.
