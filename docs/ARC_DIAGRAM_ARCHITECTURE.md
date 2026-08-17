# Flow Chart — Arc-Diagram Architecture (rhymekit)

Source: a three-part Duckdown-authored specification, "A General Theory
of Rhyme-Scheme Indication Architecture" — Part 1 (theory: strata,
ontology, algebra, operators, taxonomy, logic, schema, topology,
meta-ontology, regime instantiations), Part 2 (Artifact A: typed
pseudocode; Artifact B: a complete example cue-sheet, explicitly labeled
"original pastiche... not real lyrics"; Artifact C: the arc-diagram
renderer spec), and Part 3 (`rhymekit.py` — a complete, runnable reference
implementation of Artifacts A + C). This is a substantially different and
complementary design from `flowchart_engine.py`: instead of coloring
words in a scrolling lyric view, it renders rhyme relationships as an
**arc diagram** — a chord/pseudoknot diagram in the style of RNA
secondary-structure visualization, where crossing arcs are a deliberate,
meaningful signal (rhyme density/complexity), not noise to avoid.

## What this design adds that flowchart_engine.py doesn't have

- **Ortho-divergence / heterograph detection** — the same sound, spelled
  differently ("villain" vs. "ill in us"), tracked as its own tier axis
  parallel to the phonemic one, so a chart can show "one hue, two
  spellings" instead of missing the relationship or treating it as a
  spelling mismatch.
- **Multi-voice tracking** — main vocal, ad-libs, and samples as distinct
  voices that can still participate in the same rhyme group (sample
  call/response), which `flowchart_engine.py` has no concept of at all
  (single implicit voice).
- **Latency / resolve semantics** — a rhyme group can be "latent" (one
  member fired, waiting) for bars before its second member resolves it,
  rendered as a dashed arc that turns solid on resolution. Models
  DOOM-style delayed/cross-bar rhyme directly, rather than just widening
  the lookahead window.
- **A continuous complexity fingerprint (Φ)** with named regimes — R0
  (simple end-rhyme), R1 (André-style layered/interlocked), R2
  (DOOM-style displaced/latent) — each with expected Φ ranges, so a track
  can be classified by its own rhyme complexity, not just charted.
- **The arc-diagram lane renderer itself** — genuinely new visual
  language for this project: Bézier arcs per rhyme group, stacked by
  layer (SAMPLE/LOCAL/INTERNAL/ADLIB/ORTHO/SPINE), with a heavy spine
  polyline as the verse's structural backbone.

## What got built and verified this pass

1. **`rhymekit.py`** — saved as provided, with real bugs found and fixed
   while getting it to actually run (see "Bugs found and fixed" below).
   Verified: the self-demo runs and produces the tier-clustering behavior
   described (PERF/FAM/ASSON/ORTHO), and the renderer produces valid SVG
   from Artifact B's example cue sheet.
2. **`arc_bridge.py`** — bridges `flowchart_engine.py`'s real detection
   output into rhymekit's schema, so the arc-diagram renderer runs on
   **actual Duckdown catalog data**, not just the spec's illustrative
   example. Verified end-to-end on both tracks in the catalog:
   - Two Turntables & A Mic: 21 groups, 29 arcs, Φ = {d:0.6, X:11, N:3, L:10.4}
   - Who Got Da Props: 63 groups, 197 arcs, Φ = {d:1.01, X:138, N:4, L:10.5}

   The two Φ fingerprints are meaningfully different (WGTP is denser, more
   crossings, deeper nesting) — the fingerprint concept works as a real
   differentiator, not just decoration.
3. **Colour-uniqueness fix in the bridge** — `render()`'s own QA check
   requires every group to get a unique hue. The spec's small example
   (≤8 groups, mapped by hand) never hit this; real full-song data (21-63
   groups drawn from ~12 vowel families) hits it immediately by pigeonhole.
   `arc_bridge.py` keeps the "hue = phonetic family" principle (same base
   hue per vowel) but varies lightness/hue-angle deterministically per
   chain sharing a family, with an explicit dedup pass as a backstop.

## Bugs found and fixed in `rhymekit.py` (documented, not silently patched)

- A `@dataclass` field list got line-wrapped across two lines in the
  source document in a way that isn't valid Python (`Site`'s field
  declaration) — rejoined into one line.
- The self-demo passed `orth=` to `Site()`, which has no such field; it
  belongs on `K()` (the `Key` constructor lambda) — moved.
- `Site`/`Key`/etc. are plain `@dataclass`, which Python makes unhashable
  by default (since `eq=True` implies `__hash__ = None` unless frozen).
  `curate()` puts `Site` instances in a set. Fixed with `@dataclass(eq=False)`
  on `Site` (identity-based hash/equality, which is what the identity-based
  usage here actually needs).
- An operator-precedence bug divided a generator expression by `bars`
  before `max()` consumed it (`max((...) / bars, default=0)` instead of
  `max((...), default=0) / bars`) — fixed.
- The arc height-stacking block in `render()` stored only one endpoint per
  arc in its lookup key, making it structurally impossible to recover the
  arc's span for the overlap comparison it was trying to do (`S[oa]` was
  being indexed with a *group id*, not a site id). Rewritten to track
  each placed arc's full `(lane, xa, xb, height)` instead — same intent
  (stack overlapping arcs in a lane for readability), working
  implementation.
- `GROUP_FAMILY`'s hardcoded example mapping put two conceptually
  different groups (`gSP`, a vowel-family spine group, and `gORT`, a
  homophone/spelling-divergence annotation) on the same hue, which is
  both semantically wrong (ortho-divergence isn't a vowel family) and
  trips the hue-uniqueness assert. Fixed by giving `gORT` the palette's
  dedicated neutral gray and adding a distinct "mosaic" color for `gMOS`
  (the heterograph/mosaic annotation group), which had the same collision
  with `gEY`.

## A discrepancy noted, not silently resolved

The spec's Part 3 prose claims the self-demo's `ORTHO` tier keeps
`villainous` and `ill_in_us` separate ("not merged... while HOMO/PERF
would"). Running the actual code with its own default threshold
(`TH["ORTHO"] = 0.4`) merges them — their normalized edit distance is
0.3, under the threshold. This is a real mismatch between the narrative
description and the shipped threshold value, not something introduced by
running it. Left as-is (didn't silently retune the threshold to match the
prose) since that's a design tuning choice belonging to whoever owns this
spec, not something to guess at.

## Scope note — what this is NOT yet

`rhymekit.py` and `arc_bridge.py` are **server-side Python**. They are not
wired into the browser-based Flow Chart Studio (`index.html`), which is
JavaScript. Producing an in-browser "Export Arc Diagram" button would mean
porting the renderer (or at minimum the layout math) to JS — a real,
scoped follow-up, not attempted in this pass so as not to ship a rushed
partial port. Today, generating an arc diagram means running
`arc_bridge.py` against a track's lines locally.

## Files

- `rhymekit.py` — reference implementation (Artifacts A + C), fixed to run.
- `r2.json` — Artifact B's example cue sheet (original pastiche, not real
  lyrics), used to verify the renderer against the spec's own worked
  example before trusting it on real data.
- `arc_bridge.py` — `flowchart_engine.py` output → rhymekit schema → SVG.
