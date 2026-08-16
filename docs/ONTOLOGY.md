# Flow Chart — Ontology

## 1. Terms

| Term | Definition |
|---|---|
| Rhyme Unit | Smallest rhyming element compared — a syllable or syllable cluster. |
| Rhyme Anchor | The stressed syllable a rhyme is built around. |
| Rhyme Family / Chain | Set of Rhyme Units judged to rhyme with each other across a passage. |
| Chain Length | Count of members in a Rhyme Family. |
| Carryover | A chain that continues across a line break. |
| End Rhyme | Rhyme Unit falls at the end of a line. |
| Internal Rhyme | Rhyme Unit falls mid-line. |
| Cross-Word Chain | Rhyme spans word boundaries (unit built from parts of 2+ words). |
| Compound Split | A single word whose two+ stressed syllables independently carry different rhyme chains (polyphonic word). |
| Polyphonic Unit | The stressed-syllable candidate feeding the Compound Split pass. |
| Repetition Tag | Marks a chain member that is a literal repeat, not a new rhyme instance. |
| Speaker Tag | Marks which speaker/voice a line belongs to (for multi-MC tracks). |
| Density Score | Rhymes-per-bar metric. Backend-only; not in the current visual grammar. |
| Mora | Japanese-language timing unit (borrowed for cross-language generalization). |
| Vowel Rhyme (母音踏み) | Rhyme defined by matching vowel sequence regardless of consonants — primary tier in Japanese hip-hop rhyme practice, secondary/independent pass in this English-first engine. |
| Echo Callout | A vowel-run member that echoes an earlier anchor without joining its primary chain. |
| Preview Region | The BPM-adaptive lookahead window used to search for the next chain member. |

## 2. Term Sets

- **Position**: End / Internal / Cross-bar
- **Strength**: Consonance / Assonance / Slant / Perfect
- **Span**: Local / Couplet / Chain / Section-spanning / Callback
- **Unit Size**: Mono / Multi-2 / Multi-3+

## 3. Topology

- **Couplet Lock** — two adjacent lines share an end-rhyme pair.
- **Monorhyme Run** — 3+ consecutive lines share one end rhyme.
- **Interlock / Braid** — two or more chains alternate across lines.
- **Nested Rhyme** — a chain member embedded inside a line already carrying a different end-rhyme chain.
- **Cluster Burst** — a short passage with unusually high chain density.
- **Callback / Bookend** — a chain member recurring after a long gap (e.g. hook returning at the outro).

## 4. Logic

See `docs/LOGIC.md`.

## 5. Visual Grammar

- Each Rhyme Family is assigned a distinct color, held constant for the life of the chart.
- Perfect-tier matches render at full saturation; slant/assonance/consonance render progressively desaturated.
- Compound Split words render as a single word with two colored underline segments (one per syllable's chain).
- Vowel Runs render as a subtle outline/underline (not fill) so they never visually compete with primary chain coloring.
- Density Score is not rendered — reserved for backend tooling (e.g. an eval dashboard).

## 6. Language Profiles — Mora-Timing Generalization

English (CMU-based) ranks rhyme tiers Perfect > Slant > Assonance > Consonance,
with the coda consonant carrying real weight. Japanese hip-hop rhyme practice
(母音踏み, vowel rhyme) inverts this: the **vowel sequence** is the primary
rhyme currency, and consonants are secondary. `language_profiles.py`
implements this as a `LanguageProfile` abstraction (`ENGLISH_PROFILE`,
`JAPANESE_PROFILE`) with a mora tokenizer for Japanese (handling yōon small
kana, long-vowel marks ー, and moraic ん) and a `compare_mora_sequences`
function returning `exact_mora / vowel_rhyme / partial / None`.

Status: architecture-ready, tested only against synthetic invented Japanese
phrases (never real third-party lyrics) — not yet production-verified
against a real Japanese track.

## 7. Resolved Decisions

- Lookahead window: BPM-adaptive (bars → seconds via detected tempo), not a fixed word count.
- Compound Split: automatic, not manual-flag-triggered.
- Density Score: stays backend for now, not surfaced visually.
- Vowel Runs: an independent secondary pass, never claims/consumes primary chain candidates.
