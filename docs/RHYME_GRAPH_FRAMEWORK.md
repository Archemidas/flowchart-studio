# Flow Chart — Compositional Framework (Operations 201–210)

Source: a Duckdown-authored specification document ("Operations 201–210 —
Compositional & Structural Calculus for Rhyme, Rime, Meter, and Lyric
Pattern Analysis") describing a 10-operation pipeline and an accompanying
rhyme/meter ontology for computational lyric analysis. This document maps
that framework onto what `flowchart_engine.py` actually implements, and
records what was newly added because of it. The source document contains
no song lyrics — only generic linguistic examples (night/light,
motion/ocean, etc.) used to illustrate the operations.

## The 10 operations, mapped to this engine

| # | Operation | What it means | Where it already lives here |
|---|---|---|---|
| 201 | Decomposition | Break a performance into constituents (song→section→bar→word→syllable→phoneme) | `clean_word`, `segment_syllables`, `build_word_index` |
| 202 | Composition | Build higher-order rhyme/metrical structures from constituents | `gather_candidates` → `cluster_candidates` → chains |
| 203 | Aggregation | Collect rhyme-bearing candidates without asserting structure | `candidates_by_k` (pre-clustering candidate pools) |
| 204 | Segmentation | Partition into temporal/textual/metric regions | Line-level `{start, end, text}` input + `tempo_meter.py`'s bar/beat mapping |
| 205 | Clustering | Group by similarity in a feature space | `cluster_candidates` (complete-linkage, phonetic feature space only so far) |
| 206 | Layering | Represent simultaneous rhyme/meter as distinct, non-collapsing layers | Primary chains + secondary (polyphonic) chains + vowel runs, kept as separate directories rather than merged |
| 207 | Nesting | Rhyme structures inside larger rhyme structures | Compound Split / polyphonic words (a word anchoring two chains at once) |
| 208 | Embedding | Represent rhyme units in a feature vector space | **Not implemented** — the engine uses discrete tier comparison, not continuous vectors. See "Deferred" below. |
| 209 | Weaving | Interleave multiple overlapping rhyme trajectories across time | Implicit — multiple chains can and do coexist over the same span; no dedicated visualization of the interleaving yet |
| 210 | Fusion | Combine layers into one structure while preserving provenance | `annotate_lines()`'s combined output — each word's tag keeps its originating chain/tier/cross-word/cross-bar provenance rather than collapsing to a single color |

## What this pass added (newly built, not previously in the engine)

- **Rhyme graph** (`build_rhyme_graph`) — the framework's "rhyme_scheme =
  graph, not string" principle. Returns `{nodes, edges}`: nodes are word
  indices; edges connect consecutive members within a chain, typed
  (`rhyme` / `cross_word_rhyme` / `polyphonic_rhyme` / `vowel_run`) and
  carrying tier + continuous strength score. Additive — the existing
  line/chain output is unchanged, this is a second view of the same data.
- **Continuous rhyme strength score** (`rhyme_strength_score`) — the
  framework's `R = w1·V + w2·C + w3·S + w4·T + ...` idea, implemented as a
  tier-based baseline (perfect=1.0, slant=0.75, assonance=0.55,
  consonance=0.4) modulated by temporal proximity across the chain's
  members. Supplements the discrete tier, doesn't replace it — both are in
  the output now (`chains[].strength` is the tier, `chains[].strength_score`
  is the continuous value).
- **Cross-bar flag** (`word_bar_index`, `chains[].cross_bar`,
  `words[].cross_bar`) — the framework's Cross-Bar Rhyme concept: does a
  chain span a bar boundary. Computed from each word's existing
  interpolated timestamp and the track's BPM; only set when `bpm` is
  provided to `annotate_lines()` (never guessed). Uses a flat downbeat
  assumption (bar 0 starts at t=0) unless a real downbeat phase is wired
  in from `tempo_meter.py` — a known approximation, stated here rather than
  silently treated as exact.
- **Stress pattern strings** (`stress_pattern_string`,
  `lines[].stress_pattern`) — an `S u S u` style string per line, surfacing
  the primary-stress flags `segment_syllables()` already computed
  internally, per the framework's Stress Representation section.

## Deferred, and why

- **Embedding (true vector space)** — the framework proposes representing
  each rhyme unit as a feature vector (vowel/coda/onset similarity,
  syllable count, stress similarity, temporal distance, bar distance) and
  analyzing relations geometrically. This is a real, larger workstream —
  it's also exactly the shape of the previously-approved "graded phonetic
  matching / articulatory feature distance" item already sitting in the
  Plan Tasks list from the engine-improvement plan. Not duplicated here;
  tracked as one item.
- **Performed stress vs. lexical stress** — the framework distinguishes
  dictionary (lexical) stress from performance intensity (how hard a
  syllable actually hit in the recording). Only lexical stress (from CMU)
  is available today; performed stress would need audio-level loudness/
  duration analysis per syllable, tied to the same forced-alignment
  workstream already planned but not built.
- **Notation Integration** (linking lyric events to musical pitch/duration)
  — a genuinely new, separate future workstream; no MIDI/notation handling
  exists in this system today.
- **Weaving as its own visualization** — multiple simultaneous chains
  already coexist in the data; a dedicated view showing them as
  interleaved trajectories (rather than reading it off the graph) is a UI
  task, not an engine one — a candidate for a club-room or Studio view.
