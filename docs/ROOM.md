# The Club — Three.js 90s Hip-Hop Room

File: `club_room.html` (root of the repo when deployed).

## What it is

A first-person 3D room: dark club floor with an animated emissive tile
grid, a raised stage platform at the back with sweeping colored spotlights
(pink / cyan / gold / purple) and a DJ-booth glow, haze planes for
atmosphere. The stage back wall carries two adjacent screens:

- **Video screen** — sized to the real aspect ratio of the loaded video
  once its metadata loads (no letterbox margin dead space inside the
  frame).
- **Lyric-chart screen** — directly beside the video screen (right side by
  default; swap `videoX`/`lyricX` in `layoutScreens()` to put it on the
  left instead), auto-scrolling in sync with `video.currentTime`, showing
  the current line large and colored by its rhyme chain, with the
  previous/next lines faded above/below. Text wraps and clips to the
  screen's own canvas bounds — it never spills outside its frame or into
  the video screen's frame.

## Controls

| Platform | Move | Look | Jump |
|---|---|---|---|
| Desktop | WASD / arrow keys | mouse drag | Space |
| Mobile / touch | left virtual joystick | right virtual joystick | on-screen JUMP button |
| VR (WebXR / Quest / OVR) | controller thumbstick | head tracking | (movement only; jump omitted in VR to avoid motion discomfort) |

VR entry uses three.js's standard `VRButton`, which drives any WebXR-
compliant headset — including Meta Quest ("OVR") browsers — with no
native SDK required.

## Jump / stage physics

Simple gravity+velocity model (`GRAVITY=-16`, `JUMP_SPEED=6.5`). The stage
platform is a raised box (`STAGE_H=0.9`); `groundHeightAt(x,z)` returns the
stage height when standing over the platform footprint and `0` elsewhere,
so pressing jump while approaching the stage lets the player hop up onto
it.

## Proximity-triggered controls

`updateStageProximity(camPos)` checks distance to the stage front; within
range, `#stageControls` (play/pause, seek bar, time label, track picker)
fades in at the bottom of the viewport. Outside that range it fades out —
the video keeps playing/paused as-is, only the UI visibility changes.

## Avatar integration

A `.glb`/`.gltf` file input (top-center overlay) lets a user load their
own avatar model via `GLTFLoader`; once loaded it's positioned at the
player's feet each frame and shown when the "third-person view" checkbox
is on. This is a single-user visual slot, ready to be wired to real
multiplayer networking later (not implemented here — no networking layer
exists yet).

## Catalog

`CATALOG` at the top of the file is the fan-facing track list — see
`docs/PARAMETERS.md` for the entry shape. Currently populated only with
tracks whose audio/video and lyric text were supplied directly by
Duckdown in this project (Two Turntables & A Mic). Add further tracks by
appending entries once supplied the same way; `catalog.json` in the repo
root mirrors this list for use outside the room (e.g. a landing page).

## Known gaps

- VR controller "select"/jump input isn't wired (movement only).
- Third-person camera offset is a stub (`avatarModel` renders in third
  person but the camera itself still follows first-person rules — full
  third-person orbit camera not yet built).
- No multiplayer/networking — the avatar loader is single-local-user only.
