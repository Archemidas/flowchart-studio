# Flow Chart — Detection Logic Pipeline

1. **Clean + transcribe.** Strip punctuation/casing (`clean_word`), look up
   CMU Pronouncing Dictionary phones (`get_phones`).
2. **Syllabify.** Segment phones into syllables of (onset)-nucleus-coda
   (`segment_syllables`); mark the primary-stress syllable as the anchor.
   Function words with no genuine primary stress are filtered via a
   stopword list rather than defaulting to "last vowel regardless of
   stress" (this was an early bug — see Errors Fixed below).
3. **Build the word/timing index.** `build_word_index` interpolates a
   per-word timestamp `t` from line-level start/end stamps.
4. **Estimate tempo.** `estimate_bpm` (or, preferably, `tempo_meter.analyze`
   for the refined, non-quantized value) gives BPM; `bars_to_seconds`
   converts a bars-based lookahead into a seconds-based window.
5. **Generate candidates.** `gather_candidates` builds rhyme-unit
   candidates for K = 1, 2, 3 syllables, including cross-word units,
   resolved largest-unit-first so a 3-syllable match takes priority over
   a 1-syllable submatch of the same words. Returns `candidates_by_k`
   plus `internal_candidates` (non-final stressed syllables, feeding
   Compound Split).
6. **Cluster.** `cluster_candidates` groups candidates into chains by tier
   using **complete-linkage**: a new candidate must match every existing
   member of a cluster (not just one) before joining it. This replaced an
   earlier single-linkage/union-find approach that transitively fused
   unrelated words into one 136-member blob at loose tiers.
7. **Compound Split / polyphony.** `find_polyphony` runs a separate pass
   over `internal_candidates` to detect words whose two+ stressed
   syllables independently join different chains.
8. **Vowel Runs.** `find_vowel_runs` pools K=2/3 candidates and clusters by
   exact vowel-sequence equality (ignoring consonants), entirely
   independent of and non-conflicting with the primary chain claiming —
   this is the cross-language (Japanese mora-timing) generalization.
9. **Assemble output.** `build_chains` returns `words, all_chains,
   word_tag, secondary_chains, vowel_runs`; `annotate_lines` wraps the
   whole pipeline and returns the final annotated structure.

## Errors found and fixed (chronological)

- **Unstressed function words falsely chaining** — fixed by requiring a
  genuine primary-stress marker plus a stopword filter.
- **Single-linkage blob fusion** (136-member cluster at loose tiers) —
  fixed by switching to complete-linkage clustering.
- **Meter harmonic-collapse** (true 4/4 read as 8/8, because folding at a
  multiple of the true meter also aligns and inflates score from more
  phase bins) — fixed with a harmonic-collapse correction step in
  `estimate_time_signature` (prefers the smaller divisor candidate when
  its score is within `HARMONIC_TOL=0.55` of the raw winner).
- **BPM grid-quantization** — librosa's `beat_track` snaps tempo to
  `60*sr/(hop*lag)` bins (~1.9 BPM apart near 100 BPM). Fixed by taking
  the correct *octave* from `beat_track` (reliable there) and refining
  *within* it via parabolic interpolation of the raw autocorrelation
  peak. Verified: two real tracks resolved to 98.13 and 100.07 BPM
  respectively instead of both quantizing to 99.38.
- **Studio null-timestamp crash** (`Cannot read properties of null
  (reading 'toFixed')`) — Whisper's word-level timestamps occasionally
  return `null` (usually the last word in a clip). Fixed with
  `sanitizeChunks()` patching nulls from neighboring chunks, plus a
  defensive `?? 0` fallback.
- **Line/section skipping in auto-transcription** — root cause was
  Whisper's internal speech/silence judgment being unreliable inside
  arbitrary fixed 30s chunk windows across instrumental breaks. Fixed by
  replacing blind chunking with energy-based Voice Activity Detection
  (`detectVoiceActivity`) that segments on actual signal energy with
  hysteresis before transcribing each segment.
- **Sandboxed-iframe Cache Storage failure** — PublishWebpage artifacts
  run in a CSP-sandboxed iframe lacking `allow-same-origin`, disabling
  the Cache Storage API transformers.js needs. Fixed by hosting Flow
  Chart Studio on GitHub Pages (a real origin) instead of working around
  it in-sandbox.
