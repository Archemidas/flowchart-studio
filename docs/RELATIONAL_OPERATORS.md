# Flow Chart — Relational & Expressive-Formation Operators (191–220)

Source: two more Duckdown-authored specification docs extending the
201–210 compositional framework (`docs/RHYME_GRAPH_FRAMEWORK.md`):
**191–200, Relational Precomposition** (how elements become positioned/
qualified/coupled *before* composition) and **211–220, Expressive
Formation** (how composed structures become recognizable expressive
units). Both contain only generic illustrative examples (night/light,
static/attic/automatic/panic as toy phonological examples), no song
content. This doc maps every operation in both sets onto what's actually
built, same format as the 201–210 mapping.

## 191–200 — Relational operators

| # | Operation | Core question | Status here |
|---|---|---|---|
| 191 | Alignment | What corresponds across a coordinate system? | Implicit — words are aligned to time/line position throughout; no standalone alignment utility |
| 192 | Orientation | Does the relation have a direction? | **Now explicit** — `rhyme_graph` edges run earlier→later member by construction; graph carries `directed: true` |
| 193 | Coupling | What interacts while remaining distinct? | Partial — phonology and meter are computed by separate modules (`flowchart_engine.py` / `tempo_meter.py`) but not joined into one relation record yet. Deferred: see below. |
| 194 | Binding | What belongs together without becoming a new object? | Matches Cross-Word Chain candidate grouping (words treated as one unit for a rhyme span without merging into a new lexical item) |
| 195 | Anchoring | What's the reference frame? | **Already a core term** — "Rhyme Anchor" is in `docs/ONTOLOGY.md` §1, predates this mapping |
| 196 | Referencing | What points toward what? | Matches the "Callback/Bookend" topology pattern in `docs/ONTOLOGY.md` §3 |
| 197 | Echoing | What recurs with recognizable transformation? | Matches "Echo Callout" (ontology §1) and the Vowel Run pass (drift-tolerant recurrence) |
| 198 | Contrasting | What difference is structurally meaningful? | **Deferred** — requires semantic/meaning analysis; this engine is phonemic/metrical only, no semantic layer exists |
| 199 | Gradating | What changes continuously/incrementally? | **Deferred** — a "chain complexity progression" metric (tier or unit-size trending up/down across a chain) is a natural future addition, not built |
| 200 | Phasing | What stays related while shifting position? | **Deferred** — needs a chain member's beat-subdivision position over time, which requires wiring `tempo_meter.py`'s beat grid into `flowchart_engine.py` (currently only a scalar bpm crosses that boundary) |

## 211–220 — Expressive formation operators

| # | Operation | Core question | Status here |
|---|---|---|---|
| 211 | Formation | Do components become a recognizable unit? | Matches chain formation generally — no separate build needed |
| 212 | Morphing | Does an identity persist through transformation? | **Already implemented as `custom_pronunciations.txt`** — GON'/I'MA/BLOWIN'/CUZ are exactly A→A' morphs (canonical form → performed form) with identity preserved. Documented connection, no new code. |
| 213 | Compounding | Do independent units join while staying recoverable? | Matches Compound Split / polyphony detection (`find_polyphony`) — a word anchoring two chains at once, each half analytically recoverable |
| 214 | Phrase-Binding | Does a rhyme cross a lexical boundary as a phrase unit? | **Already implemented** — Cross-Word Chain candidates (`word_start != word_end`) |
| 215 | Phonetic-Bridging | Does connected speech blend across a word boundary? | **Deferred** — would need cross-word resyllabification (detecting when word-final and word-initial phones blend acoustically, e.g. "my own"→/maɪoʊn/); real future work, not attempted here |
| 216 | Syllabic-Bending | Does performance change syllable count vs. the dictionary form? | **Already implemented as the mechanism**, not a separate feature — custom pronunciation entries ARE how this engine handles performed syllable count differing from canonical (e.g. BLOWIN' at 2 syllables vs. dictionary "blowing" at 3) |
| 217 | Rhyme-Chaining | Does the chain have a measurable trajectory, not just membership? | **Newly built this pass** — `chain_metrics()` returns `chain_length`, `mean_similarity`, `phonetic_drift`, `stress_continuity`, `temporal_span` per chain (see below) |
| 218 | Metrical-Warping | Does performance deviate measurably from a reference meter? | **Deferred** — needs the same beat-grid wiring as Phasing (200) |
| 219 | Cross-Bar-Weaving | Does a structure persist across a bar boundary? | **Already implemented** (previous pass) — `cross_bar` flag on chains and words |
| 220 | Semantic-Phonetic Fusion | Do sound and meaning reinforce each other? | **Deferred** — requires semantic analysis; same gap as Contrasting (198) |

## What got built this pass: chain metrics (217)

`chain_metrics(candidates)` in `flowchart_engine.py`, attached as
`chains[].metrics` in `annotate_lines()`'s output:

- `chain_length` — member count.
- `mean_similarity` — average pairwise tier-similarity across all member
  pairs (0–1, reusing the same tier→similarity mapping as
  `rhyme_strength_score`).
- `phonetic_drift` — how much the tail phones differ between the chain's
  first and last member (0 = no drift, 1 = fully different) — the "chain
  has a trajectory, not just a bin" idea from 217's definition.
- `stress_continuity` — constant `1.0`, documented as such rather than
  measured: every primary-chain candidate is built from a primary-stressed
  anchor by construction (`gather_candidates`), so this is trivially true
  in the current design, not a real per-chain signal yet.
- `temporal_span` — seconds between the chain's first and last member.

## Deferred items requiring real future work (stated plainly)

- **Coupling (193)** and **Metrical-Warping (218)** / **Phasing (200)**
  all point at the same gap: `flowchart_engine.py` and `tempo_meter.py`
  aren't wired together beyond a scalar BPM. Passing the real beat grid
  (from `tempo_meter.analyze_beats`) into `build_chains` would unlock all
  three at once — a good next integration, not started here.
- **Contrasting (198)** and **Semantic-Phonetic Fusion (220)** both need a
  semantic/meaning layer this engine doesn't have (it's phonemic/metrical
  only). A real addition, not a small one — would likely mean an LLM-based
  or embedding-based semantic-similarity pass, kept clearly separate from
  the deterministic phonemic pipeline if built.
- **Phonetic-Bridging (215)** needs cross-word resyllabification detection
  — real, scoped future work, not attempted here.
- **Gradating (199)** — a "chain complexity trending up/down" metric is
  small and could be added alongside `chain_metrics()` later; skipped this
  pass to keep the change set focused on what's concretely finished.
