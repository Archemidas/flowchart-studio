# Changelog

## v0.6 — 2026-08-16
- Added `club_room.html`: 90s hip-hop club 3D room. WASD + mouse (desktop),
  dual virtual joysticks + jump button (mobile/touch), full WebXR VR support
  (Meta Quest/OVR compatible via standard `VRButton`). Jump physics onto a
  raised stage platform. Dual stage screens (video sized to true aspect,
  adjacent auto-scrolling lyric-chart screen) with proximity-triggered
  playback controls. Optional user-supplied `.glb` avatar loader.
- Added full documentation set: `SKILL.md`, `docs/ONTOLOGY.md`,
  `docs/LOGIC.md`, `docs/PARAMETERS.md`, `docs/ROOM.md`,
  `docs/LEARNING_LOG.md` (self-training/accumulated-understanding log).
- Added `catalog.json`: fan-facing track catalog, currently listing Two
  Turntables & A Mic (the only track with a fully supplied audio/video +
  lyric-text chain in this repo so far).

## v0.5 — prior session
- `find_vowel_runs` cross-language (Japanese mora-timing-inspired) vowel-run
  detection pass added to `flowchart_engine.py`.
- Flow Chart Studio: Whisper `large-v3-turbo` model swap, energy-based Voice
  Activity Detection (fixes line/section skipping), center-channel vocal
  isolation.
- Null-timestamp crash fix, Cache Storage sandbox fix (GitHub Pages hosting).

## v0.4 and earlier
- Core `flowchart_engine.py` phonemic detection pipeline, `tempo_meter.py`
  BPM/meter analysis (grid-quantization fix, harmonic-collapse fix),
  `language_profiles.py` architecture, Flow Chart Studio manual-entry tool.
