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

## 2026-08-16 — On-screen text transcription (OCR) added to Studio
Clarification from the prior request: the on-screen-text learning ask was
for a STUDIO FEATURE, not something to run in-session against reference
material. Built `ocrTranscribeFromVideo()` (Tesseract.js — documented,
open-source OCR, not a black-box model) as a second, independent
transcription input alongside the existing audio/Whisper path: samples
video frames at a configurable interval, crops to a configurable
region (full/top-third/bottom-third, since caption placement varies),
recognizes text per frame, and collapses consecutive frames holding the
same on-screen line into one timestamped entry — same output shape as the
audio path, feeding the same line editor. Explicitly NOT a separate
always-on storage/training pipeline: results land in the editable line
rows the same as typed or ASR'd lines, and persist only if the user
exports a bundle, same as every other input method. The sourcing rule is
identical to the audio path and stated in the UI: the tool reads whatever
is in the loaded file, same as Whisper reads whatever is in the waveform;
which videos are appropriate to load is the same judgment call the user
already makes, not something the tool decides for them.

## 2026-08-16 — IPA layer + custom pronunciation knowledge store
Request: "learn from lyric videos where words follow on screen" and store
detected rhyme-nature + phonemic pronunciations in an interlinked
knowledge store, adding IPA if useful. Declined the specific mechanism —
OCR'ing on-screen lyric text from third-party rhyme-scheme reference
videos into a stored knowledge base is still third-party copyrighted
lyric extraction, regardless of the destination being called a
"knowledge store" or the purpose being "training." Built the legitimate
parts instead: `arpabet_to_ipa()`/`arpabetToIpa()` (public ARPAbet->IPA
mapping, mirrored in `flowchart_engine.py` and `cmu_engine.js`) gives any
word a real IPA transcription; `custom_pronunciations.txt` extends the
CMU lookup with individual word pronunciations for slang/ad-libs that
actually occur in Duckdown's own catalog (BCC, BLOWIN', CUZ, DISSED,
GON', I'MA, NAPPY, NIGGA, PAPPY — found by running the real engine's
unknown-word check against both tracks' own confirmed lines). One entry
(VIPI, from an auto-transcribed line) was deliberately left unconfirmed
rather than guessed — flagged in `docs/PHONEMIC_KNOWLEDGE.md` as needing
the artist's confirmation of the actual word. Both engines load this file
and merge it into the same CMU map, so server and client stay in parity.
Studio now shows IPA on hover for any colored (or dictionary-known)
word in the preview. `docs/PHONEMIC_KNOWLEDGE.md` documents the rhyme-tier
taxonomy with IPA using generic dictionary-word examples (cat/hat/cap/bag/hot)
— deliberately not song lyrics — so the taxonomy has worked examples
without needing copyrighted material at all.

## 2026-08-16 — CRITICAL: index.html/flowchart_studio.html file split
Observed: reported symptoms (auto-transcribe stalling, missing words,
heuristic-only engine, no live sync) persisted even after fixes were
pushed and confirmed correct in the repo. Root cause: GitHub Pages serves
`index.html` at the site root, but every Studio edit across recent
sessions was pushed to a separately-named `flowchart_studio.html` file —
the two files silently diverged, and the LIVE site kept serving an old
`index.html` snapshot while all the real work landed in a file nobody was
actually viewing. Confirmed via the GitHub Contents API (two files, very
different sizes) after direct `curl` checks of the live site kept
disagreeing with what should have been true. Fix: synced `index.html` to
match `flowchart_studio.html`, then deleted the duplicate so there is only
one canonical Studio file going forward. Lesson for future sessions:
after any push intended to change the LIVE site, verify against the
actual served root path (`/`), not just the pushed file's own path —
pushing successfully and being live are not the same fact.

## 2026-08-16 — Real CMU phonemic engine ported to Studio (JS)
Change: `cmu_engine.js` is a line-for-line port of `flowchart_engine.py`'s
detection pipeline (tiers, complete-linkage clustering, BPM-adaptive
window, same candidate generation) running against a real CMU
Pronouncing Dictionary export (`cmudict.txt`, ~125k words, plain-text
format chosen specifically to stay under GitHub's 4MB request-body limit
without JSON-quote-escaping bloat). Verified word-for-word identical chain
output against the Python engine on real Duckdown lines (same colors,
strengths, unit sizes, cross-word counts, and per-word chain/position
tags) via a Node harness before shipping. Studio now runs this as the
primary engine; the old spelling-heuristic engine is kept ONLY as an
automatic fallback if the dictionary fails to fetch.

## 2026-08-16 — Transcription pipeline: gate → gap-detector
Observed (reported directly): auto-transcribe was stalling and still
missing words. Root cause: v1 used VAD as a GATE — audio outside a
detected "active" segment was never sent to the model at all, and each
detected segment (often dozens per track, from ad-libs/short
interjections) was transcribed with its own sequential async model call.
That's slow enough to look hung, and a misjudged energy threshold could
silently delete a passage with no downstream recovery. Fix: the PRIMARY
pass now transcribes the whole track in one call (letting the model's own
long-form chunk-and-merge handle it, instead of us pre-slicing into dozens
of small calls). VAD runs AFTER, only as a coverage check — any
vocal-active region the primary pass covered too sparsely
(`computeWordCoverage` against a words/sec floor) gets re-transcribed
individually and spliced in. A bad VAD threshold can now only trigger a
wasted extra pass, never silently drop a word. VAD thresholds were also
loosened (lower on/off energy thresholds, 1.5s gap-merge instead of
600ms) since they no longer gate anything — erring toward "flag more
regions" costs a little time, not correctness.

## 2026-08-16 — "Follow along" was genuinely missing, not just cosmetic
Observed (reported directly): Studio's preview and the club room's lyric
screen never matched the reference rhyme-scheme videos' style and
"doesn't move anything ... doesn't follow along." Confirmed true on
inspection: `renderPreview` in Studio rendered one static colored list
with no connection to `video.currentTime` at all, and the club room's
`drawLyricScreen` only recolored a whole LINE at a time by a single
majority chain color — no per-word coloring, no active-word tracking.
Fix: added a live "Now Playing" panel in Studio (`renderNowPlaying`,
driven by the video's `timeupdate` event) and rewrote the club room's
`drawLyricScreen`/added `renderWordLine` to render every word in its own
chain color with the currently-spoken word getting an active glow +
underline, both interpolating word position within a line the same way
(line span ÷ word count — neither track has ASR-grade per-word ground
truth for every line). Also regenerated the club room's per-line catalog
data by actually running `flowchart_engine.py` against both tracks' real
lines (previously an approximated single-color-per-line reconstruction),
so the colors shown are the real engine's per-word output, not a stand-in.

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
