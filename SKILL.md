---
name: flow-chart-rhyme-engine
description: Detects and visualizes rhyme schemes (including multisyllabic, cross-word, compound/polyphonic, and cross-language vowel-run rhymes) in song lyrics using CMU phonemic transcription, tempo-adaptive windowing, and complete-linkage clustering. Use when a Duckdown Records track (audio + confirmed lyric text, supplied directly by the rights holder) needs a rhyme-scheme chart, a colored lyric visualization, or a Flow Chart Studio / Three.js room build.
---

# Flow Chart — Rhyme Scheme Engine

## What this is

A rhyme-scheme detection and visualization system built for Duckdown Records,
covering: phonemic rhyme detection (`flowchart_engine.py`), tempo/meter
analysis (`tempo_meter.py`), cross-language mora-timing generalization
(`language_profiles.py`), a browser-based manual/auto-transcription tool
(Flow Chart Studio), and a Three.js 3D club room that plays a track back
with a synced lyric-chart display.

**Source of lyric text**: only text supplied directly by the rights holder
(Duckdown, via file upload or first-party confirmation) is ever run through
this engine. No lyric text is scraped from Genius or any third-party site,
and no third-party artist's copyrighted lyrics are used to calibrate or
fine-tune any part of this system — including as abstraction/distillation
input. Reference material studied for this project's *methodology* (rhyme
notation conventions, mora-timing research) was studied structurally only;
no lyric text from those references was captured, stored, or used as data.

## Ontology (see docs/ONTOLOGY.md for full detail)

- **Rhyme Unit** — the smallest rhyming element (a syllable or syllable
  cluster) being compared.
- **Rhyme Anchor** — the stressed syllable a rhyme is built around.
- **Rhyme Family / Chain** — the set of Rhyme Units judged to rhyme with
  each other across a passage.
- **Chain Length** — number of members in a Rhyme Family.
- **Carryover** — a chain continuing across a line break.
- **End Rhyme** / **Internal Rhyme** / **Cross-Word Chain** — position
  classifications for where a rhyme unit falls.
- **Compound Split** — a single word whose two (or more) stressed syllables
  each independently carry different rhyme chains (polyphonic word).
- **Vowel Run** — a cross-language-inspired secondary pass (grafted from
  Japanese mora-timing / vowel-rhyme conventions) that groups words sharing
  an identical vowel sequence regardless of consonants, run independently
  of and without conflicting with the primary phonemic chains.
- **Density Score** — backend-only metric (rhymes per bar), not currently
  surfaced in the visual grammar.

Term Sets: **Position** (End / Internal / Cross-bar), **Strength**
(Consonance / Assonance / Slant / Perfect), **Span** (Local / Couplet /
Chain / Section-spanning / Callback), **Unit Size** (Mono / Multi-2 /
Multi-3+).

Topology patterns detected/labelable: Couplet Lock, Monorhyme Run,
Interlock/Braid, Nested Rhyme, Cluster Burst, Callback/Bookend.

## Detection logic (see docs/LOGIC.md for full pipeline)

1. Clean + phonemically transcribe every word (CMU Pronouncing Dictionary).
2. Segment into syllables (nucleus + coda), mark primary-stress anchors.
3. Generate rhyme-unit candidates for K = 1, 2, 3 syllables, cross-word
   included, resolved largest-unit-first.
4. Cluster candidates by tier (perfect → slant → assonance → consonance)
   using **complete-linkage** clustering (a candidate must match every
   existing member of a cluster, not just one — this replaced an earlier
   single-linkage/union-find approach that fused unrelated words into one
   136-member blob).
5. Apply a **BPM-adaptive time window**: rhyme lookahead is computed in
   bars, converted to seconds via the track's detected tempo, rather than
   using a fixed word-count window.
6. Run a separate **Compound Split** pass over non-final stressed syllables
   to catch polyphonic words.
7. Run a separate **Vowel Run** pass (cross-language, non-conflicting with
   the primary chains) grouping candidates by exact vowel-sequence match.

## Parameters (see docs/PARAMETERS.md for full signatures)

Primary entry point: `annotate_lines(lines, bpm=None, bars_lookahead=8,
lookahead_seconds=None, min_tier="perfect", max_k=3,
polyphony_min_tier="slant")` → `{lines, chains, secondary_chains,
polyphonic_word_count, vowel_runs}`.

## Instructions for using this skill

1. Confirm the lyric text and audio/video come directly from the rights
   holder (Duckdown) — never proceed on third-party or scraped text.
2. Run `tempo_meter.analyze(audio_path)` to get bpm / beats_per_bar /
   confidence for that track.
3. Run `flowchart_engine.annotate_lines(lines, bpm=<detected bpm>)` to get
   the chain-tagged output.
4. For fan-facing/demo delivery: feed the chain output into
   `club_room.html`'s `CATALOG` array (video URL, bpm, per-line chain tags)
   or into Flow Chart Studio for manual/auto-transcribed tracks.
5. For self-improvement: record any new bug fix, detection edge case, or
   ontology decision as a dated entry in `docs/LEARNING_LOG.md` — do not
   silently change detection behavior without a corresponding log entry.

## Known limitations / open workstreams

Forced alignment backbone, coverage-audit instrumentation, graded
phonetic (articulatory-feature) matching, and a gold-standard eval set are
planned but not yet built. Vocal isolation is currently center-channel DSP
only (not a trained source-separation model). See `docs/LEARNING_LOG.md`
for the running list.
