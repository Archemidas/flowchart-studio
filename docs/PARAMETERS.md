# Flow Chart — Engine Parameters / API Reference

## `flowchart_engine.py`

### `annotate_lines(lines, bpm=None, bars_lookahead=8, lookahead_seconds=None, min_tier="perfect", max_k=3, polyphony_min_tier="slant")`
Primary entry point.
- `lines`: list of `(start_seconds, end_seconds, text)` tuples.
- `bpm`: track tempo; if `None`, estimated internally. Prefer passing the
  value from `tempo_meter.analyze()` (refined, non-quantized) over the
  engine's own `estimate_bpm`.
- `bars_lookahead`: how many bars ahead to search for a chain continuation
  (converted to seconds via `bars_to_seconds(bpm, bars_lookahead)`).
- `lookahead_seconds`: overrides the bars-derived window directly, if set.
- `min_tier`: minimum rhyme strength required to form a primary chain
  (`perfect | slant | assonance | consonance`).
- `max_k`: maximum syllable-span (K) considered for a rhyme unit (1–3).
- `polyphony_min_tier`: minimum tier for the Compound Split pass.

**Returns**: `{lines, chains, secondary_chains, polyphonic_word_count, vowel_runs}`

### `gather_candidates(word_index, max_k=3)`
Returns `(candidates_by_k, internal_candidates)`.

### `cluster_candidates(candidates, lookahead_seconds, min_tier)`
Complete-linkage clustering. Returns list of chain dicts
`{tier, members: [...]}`.

### `find_polyphony(internal_candidates, lookahead_seconds, min_tier)`
Returns list of polyphonic word events.

### `find_vowel_runs(candidates_by_k, lookahead_seconds, min_run_length=3)`
Cross-language vowel-sequence pass. Returns list of run dicts
`{members: [...]}`, each with 2+ members after filtering.

## `tempo_meter.py`

### `analyze(audio_path)`
Returns: `bpm, bpm_quantized_librosa, bpm_median_local, bpm_drift_std,
beat_confidence, beats_per_bar, meter_confidence, meter_scores,
downbeat_phase, n_beats, n_bars, overall_confidence`.

### `analyze_beats(y, sr)`
Returns: `bpm_global, bpm_grid, bpm_median, bpm_drift_std, beat_times,
beat_strengths, beat_confidence, onset_env, sr, hop_length`.

### `estimate_time_signature(beat_times, beat_strengths)`
Returns: `beats_per_bar, confidence, scores, downbeat_phase, raw_best,
harmonic_collapsed`. `HARMONIC_TOL = 0.55` controls the harmonic-collapse
correction sensitivity.

### `detect_downbeats(...)`, `time_to_bar_beat(...)`
Bar/beat position mapping utilities.

## `language_profiles.py`

### `LANGUAGE_PROFILES = {"en": ENGLISH_PROFILE, "ja": JAPANESE_PROFILE}`

### `JAPANESE_PROFILE["tokenize_mora"](text)`
Kana → mora tokenizer (handles yōon small kana, long-vowel マーク ー,
moraic ん).

### `JAPANESE_PROFILE["compare_mora_sequences"](a, b)`
Returns `exact_mora | vowel_rhyme | partial | None`.

## `reprocess_bundle.py`

### `reprocess(bundle)`
Takes a Flow Chart Studio JSON export (heuristic JS phonetics), re-runs
every line's text through `flowchart_engine.annotate_lines`, and returns
a same-shape bundle tagged `engine: "flowchart-engine-full-v0.5"` with a
`reprocessedFrom` provenance field.

## `club_room.html` — `CATALOG` entry shape

```js
{
  id: "track-slug",
  title: "Track Title",
  album: "Album (Year)",
  videoUrl: "https://...mp4",
  bpm: 98.13,                     // from tempo_meter.analyze()
  lines: [
    [startSeconds, endSeconds, "line text", "chainKey-or-null"],
    ...
  ],
}
```
`chainKey` maps to `RHYME_COLORS` in `club_room.html` for lyric-screen
coloring. Only add entries here for tracks whose audio/video and lyric
text were supplied directly by Duckdown.
