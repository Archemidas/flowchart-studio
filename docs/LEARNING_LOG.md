# Flow Chart — Learning Log

This file is the system's persistent, append-only record of what it has
learned while building/debugging itself. Every detection-behavior change,
bug fix, or ontology decision gets a dated entry here before (or as part
of) the code change that implements it — this is the "self-training
storage" mechanism: the engine doesn't retrain weights, but its operating
knowledge (what breaks it, what fixed it, what's still open) accumulates
here in a form any future session (agent or human) can read and act on
without re-deriving it from scratch.

**Format**: `## YYYY-MM-DD — short title` then a short paragraph:
what was observed, what the root cause was, what changed, how it was
verified.

---

## 2026-08-XX — Unstressed function-word false chains
Observed: common function words (e.g. "the", "and") were chaining with
unrelated words. Root cause: falling back to "last vowel regardless of
stress" when a word had no clear primary-stress marker. Fix: require a
genuine primary-stress marker plus a stopword filter. Verified on Two
Turntables & A Mic transcript.

## 2026-08-XX — Single-linkage blob fusion
Observed: at loose (consonance) tier, one 136-member cluster formed,
absorbing unrelated words transitively. Root cause: union-find
single-linkage clustering only requires matching *one* existing member.
Fix: switched to complete-linkage clustering (`cluster_candidates`),
requiring a match against every existing cluster member. Verified: chain
sizes returned to plausible ranges (single digits to low teens) on the
same transcript.

## 2026-08-XX — Meter harmonic collapse (4/4 read as 8/8)
Observed: time-signature estimator sometimes returned 8 beats/bar for
tracks that are clearly 4/4. Root cause: folding the beat grid at a
multiple of the true meter also aligns (because it's a multiple) and
scores higher purely from having more phase bins. Fix: added a
harmonic-collapse step in `estimate_time_signature` preferring a smaller
divisor within `HARMONIC_TOL=0.55` of the raw winner's score. Verified on
both Two Turntables & A Mic and Who Got Da Props audio (both correctly
resolve to 4).

## 2026-08-XX — BPM grid-quantization
Observed: two different tracks, and two different code paths, both
returned exactly 99.38 BPM (or flipped between 97.51/99.38). Root cause:
librosa's `beat_track` snaps tempo to bins `60*sr/(hop*lag)`, spaced
~1.9 BPM apart near 100 BPM. First fix attempt (median inter-beat
interval from beat_track's own output) was circular — still quantized.
Second attempt (raw autocorrelation peak) locked onto octave errors
(197 / 50 BPM). Final fix: take the correct octave from `beat_track`
(reliable there), refine *within* it via parabolic interpolation of the
raw autocorrelation peak. Verified: Two Turntables → 98.13 BPM, Who Got
Da Props → 100.07 BPM (previously both would have quantized to the same
grid value).

## 2026-08-XX — Studio null-timestamp crash
Observed: `Cannot read properties of null (reading 'toFixed')` during
auto-transcription. Root cause: Whisper's word-level timestamps
occasionally return `null` (usually the last word in a clip). Fix:
`sanitizeChunks()` patches nulls from neighboring chunks; defensive `?? 0`
fallback on final `.toFixed()` calls.

## 2026-08-XX — Auto-transcribe skipping lines/sections
Observed: entire lines and sections of a song were missing from
auto-transcribed output. Root cause: blind fixed-30s chunking made
Whisper's internal speech/silence judgment unreliable across instrumental
breaks — it would sometimes judge a chunk containing a faded-in verse as
silence. Fix: replaced blind chunking with energy-based Voice Activity
Detection (hysteresis thresholds from percentile energy, min-gap merging,
padding) that segments on real signal energy before transcribing each
segment individually with timestamp offsetting.

## 2026-08-XX — Sandboxed-iframe Cache Storage failure
Observed: `Cache storage is disabled because the context is sandboxed`
when running transformers.js inside a PublishWebpage artifact. Root
cause: sandboxed iframes lack `allow-same-origin`, which Cache Storage
requires. Short-term fix: `env.useBrowserCache = false`. Durable fix:
host Flow Chart Studio on GitHub Pages (a real origin) and remove the
workaround.

## 2026-08-XX — Cross-language Vowel Run pass added
Change (not a bug fix): grafted Japanese hip-hop's vowel-rhyme (母音踏み)
convention as an independent secondary detection pass, `find_vowel_runs`,
clustering candidates by exact vowel-sequence equality regardless of
consonants. Deliberately does not consume/claim primary-chain candidate
positions, so it can never conflict with the primary chains. Verified on
Two Turntables & A Mic: 19 primary chains + 7 independently-detected
vowel-run groups, zero conflicts.

## 2026-08-16 — Club room video playback fix (CORS-tainted WebGL texture)
Observed: the stage video screen never played in `club_room.html`; mobile
control bars also overflowed narrow viewports. Root cause (video): the
video element had `crossOrigin='anonymous'` set so it could feed a
`THREE.VideoTexture`, but the published video host (pub.hyperagent.com)
sends no `Access-Control-Allow-Origin` header (confirmed via `curl -I`).
A `crossOrigin` request against a host with no CORS headers fails outright
— the video never loads, so nothing plays. Removing `crossOrigin` would
have fixed loading but broken the WebGL texture instead (uploading a
cross-origin, non-CORS video frame into a WebGL texture throws a
tainted-canvas `SecurityError` on `texImage2D`). Fix: stopped feeding the
video through a WebGL texture entirely — added a `CSS3DRenderer` layer
behind the (now alpha-transparent-cleared) WebGL canvas and render the
actual `<video>` DOM element there as a `CSS3DObject`, positioned/scaled
to sit exactly where the old WebGL video plane was. Plain DOM video
playback needs no CORS headers at all. Known limitation: CSS3DRenderer
doesn't support WebXR stereo presentation, so the video layer is hidden
while in a VR session (documented in docs/ROOM.md). Root cause (mobile
overflow): `#stageControls` had no max-width/wrap and depended on
fixed pixel widths; fixed with `max-width:92vw`, `flex-wrap`, and a
480px-wide media query shrinking controls, joysticks, and the jump button.

## 2026-08-16 — Club room + documentation pass
Change: built `club_room.html` (90s club aesthetic, WASD/touch/VR
movement, jump physics on a raised stage platform, proximity-triggered
playback controls, dual video+lyric screens sized to avoid frame margin,
optional user-supplied avatar loader) and this documentation set
(`SKILL.md`, `docs/ONTOLOGY.md`, `docs/LOGIC.md`, `docs/PARAMETERS.md`,
`docs/ROOM.md`, this log, `catalog.json`), all pushed to
`Archemidas/flowchart-studio`. Open items carried forward: VR
controller jump/select input, true third-person orbit camera, forced
alignment backbone, coverage-audit instrumentation, graded phonetic
matching, gold-standard eval set, and multiplayer/avatar networking —
none of these are built yet.
