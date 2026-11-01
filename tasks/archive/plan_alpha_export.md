# Implementation Plan: Transparent Alpha Overlay Export (.mov)

## Overview
Add a third export path next to `.ass` and burned MP4: a transparent QuickTime
`.mov` that contains only the captions on an invisible canvas at the source
video's display size, frame rate and duration. An editor drops it on a track
above the original footage and the captions line up with no re-encode and no
second subtitle file.

The render is built in our repo, from our own ASS generator, with our own probe
and command builder. BolCAP's `render.py` was read as a reference for the idea
and the encoder choice only; no code is copied.

## What already exists (read, not changed)
- `video_burner.burn_subtitles_to_video()` — the path to mirror: tempdir cwd so
  libass never sees a Windows colon path, `subprocess.run` with
  `CREATE_NO_WINDOW`, timeout, and a `{success, output_path, error}` return.
- `karaoke_ass.generate_karaoke_ass(segments, title, style, aspect)` — the single
  ASS source. The overlay must call this, not a second generator.
- `server.py` `/api/export/burn-video` — the upload → tempdir → `FileResponse`
  with `BackgroundTask(shutil.rmtree)` shape to mirror.
- `static/app.js` 4148–4259 — the ASS + burn handlers; the overlay handler goes
  beside them and reuses the same `currentSegments` / `currentStyle` state.

## Architecture Decisions

**D1 — Overlay canvas = source display size, source FPS, source duration.**
Not a preset. The overlay must land on the timeline already registered to the
footage, so `ffprobe` picks width, height, frame rate and duration from the
uploaded file. The ASS `aspect` passed to the generator is derived from the same
geometry, so PlayRes and the rendered canvas agree.

**D2 — `qtrle` with `-pix_fmt argb`, no fallback encoder.**
Verified on this machine: `qtrle` exists and supports `rgb24 rgb555be argb gray`;
`prores_ks` also exists. QuickTime Animation is lossless, so caption edges and
anti-aliasing survive, and every NLE reads it natively. No fallback to a lossy or
opaque encoder — an overlay that silently loses alpha is worse than an error.

**D3 — Same ASS, same style, `alpha=1` on the filter.**
`ffmpeg -h filter=ass` on this machine confirms `alpha` is a boolean that enables
alpha-channel processing. The captions are rendered by libass into the alpha
channel of a transparent source instead of being blended onto pixels.

**D4 — Colour source, not a generated PNG sequence.**
`color=c=black@0.0:s=WxH:r=FPS:d=DURATION,format=argb` as the input, then
`ass=filename='sub.ass':alpha=1`. No frame dumps, no second process, no disk
churn. Verified end to end with a 1 s 320×240 render: output is `qtrle` /
`argb`, 30 frames, and the alpha plane averages 3.45/255 (text ink present,
background transparent, constant across frames).

**D5 — Upload-based endpoint, like the burn.**
The server needs `ffprobe` geometry and rotation side data, which the browser
cannot see (the `<video>` element exposes no FPS or display matrix). Reusing the
existing multipart upload keeps one code path, one work-dir lifecycle and one
download handler in the UI. Cost: the file is copied to a temp dir first; see
risks.

**D6 — `argb` input format is explicit, before the filter.**
Without `format=argb` the colour source may negotiate a non-alpha format and
libass has nowhere to write the alpha channel.

## Command Contract (the one thing that must not drift)

```
ffmpeg -y -t {duration}
  -f lavfi -i color=c=black@0.0:s={w}x{h}:r={fps}:d={duration},format=argb
  -vf ass=filename='sub.ass':alpha=1
  -c:v qtrle -pix_fmt argb
  -an
  {out}.mov
```
Run with `cwd` = the temp dir holding `sub.ass`, so the filter path stays a bare
relative filename.

## Task List

### Phase 1: Geometry and command (no ffmpeg process yet)
- [ ] Task 1: `overlay_export.py` — `probe_overlay_geometry()` and
      `overlay_ffmpeg_args()`
- [ ] Task 2: `export_alpha_overlay()` — real 1 s render plus alpha-channel proof

### Checkpoint: Render Core
- [ ] Pure tests pass without invoking ffmpeg
- [ ] Real render produces `qtrle` + `argb` at the requested size/FPS/duration
- [ ] Alpha plane is non-zero where text is, zero elsewhere

### Phase 2: Endpoint
- [ ] Task 3: `POST /api/export/overlay-video`

### Checkpoint: API
- [ ] TestClient call returns `video/quicktime` with a real `.mov` body
- [ ] Temp dir is removed after the response

### Phase 3: UI
- [ ] Task 4: export button + download handler

### Checkpoint: End to End
- [ ] Clicking the button in the running app downloads a `.mov`
- [ ] Opening it in a player shows captions on a transparent background

### Phase 4: Evidence, docs, review
- [ ] Task 5: overlay render of one real corpus clip, numbers recorded
- [ ] Task 6: README + `memory.md`, full pytest, ponytail-review, commit

### Checkpoint: Complete
- [ ] Full suite green (`python -m pytest tests -q`)
- [ ] `node --check static/app.js` clean
- [ ] Working tree committed

---

## Task 1: Geometry probe and command builder

**Description:** New module `overlay_export.py`. `probe_overlay_geometry(path)`
runs `ffprobe -show_streams -show_format` on the first video stream and returns
display width, display height (swapped when rotation is ±90/270), frame rate as
a rational plus float, duration in seconds, and the derived `aspect` string for
the ASS generator. `overlay_ffmpeg_args(geometry, sub_name, out_path)` returns
the argument list from the contract above, with no subprocess call, so the exact
command is unit-testable.

**Acceptance criteria:**
- [ ] Rotation of ±90/270 swaps width and height; 0/180 do not
- [ ] Frame rate comes from `avg_frame_rate` and falls back to `r_frame_rate`
      when it is `0/0`
- [ ] Duration prefers `format.duration`, then the stream duration
- [ ] Missing file, no video stream, unparseable fps and zero duration each
      return a specific error, not an exception
- [ ] `overlay_ffmpeg_args` emits `qtrle`, `argb`, `-an`, and `alpha=1`
- [ ] Aspect string is the nearest of the three supported canvases (`9:16`,
      `16:9`, `1:1`) using the same 0.85 / 1.2 thresholds as the browser

**Verification:**
- [ ] `python -m pytest tests/test_overlay_export.py -q` passes
- [ ] Manual check: probe one real clip in `%TEMP%\...` and print the geometry

**Dependencies:** None
**Files likely touched:** `overlay_export.py`, `tests/test_overlay_export.py`
**Estimated scope:** S (2 files)

## Task 2: Real alpha render

**Description:** Add `export_alpha_overlay(video_path, subtitle_path, output_path,
timeout_sec)` that copies the ASS into a temp dir, runs the Task 1 command with
`cwd` set there, and returns `{success, output_path, width, height, fps, duration,
file_size, error}` in the shape `burn_subtitles_to_video` uses. Tests generate a
16×16 (later 64×64) 1 s source clip with ffmpeg, render a known one-word ASS, then
assert codec, pixel format, frame count and alpha coverage.

**Acceptance criteria:**
- [ ] Output is `qtrle` with `pix_fmt=argb`
- [ ] Output frame count ≈ fps × duration (±1 frame)
- [ ] Alpha coverage is >0 where the caption sits and 0 on a corner pixel
- [ ] A missing input returns `{success: False, error: ...}` without raising
- [ ] Timeout path returns a clear error and leaves no partial file
- [ ] Temp work dir is gone after the call, success or failure

**Verification:**
- [ ] `python -m pytest tests/test_overlay_export.py -q` passes
- [ ] Manual: extract `alphaextract` stats from the generated `.mov` and read them

**Dependencies:** Task 1
**Files likely touched:** `overlay_export.py`, `tests/test_overlay_export.py`
**Estimated scope:** S (2 files)

## Task 3: Export endpoint

**Description:** `POST /api/export/overlay-video` in `server.py`, modelled on
`api_burn_video`: multipart `video` + `subtitles`; writes both to a
`tempfile.mkdtemp(prefix="ovl_")`; calls `export_alpha_overlay`; returns
`FileResponse(..., media_type="video/quicktime", filename="{base}_overlay.mov")`
with `BackgroundTask(shutil.rmtree)`, and cleans up on the error path.

Deviation from the first draft: `format_type` was dropped. The overlay is built
from the karaoke ASS only, so accepting an SRT that the `ass` filter cannot read
would be a trap rather than a feature.

**Acceptance criteria:**
- [ ] Returns 200 and a non-empty `.mov` body for a valid upload
- [ ] Response media type is `video/quicktime`, filename ends in `_overlay.mov`
- [ ] A non-video upload returns a 4xx/500 with a readable detail, not a traceback
- [ ] Duplicate `Content-Disposition` filename is derived from the uploaded name
      with no path components

**Verification:**
- [ ] `python -m pytest tests/test_overlay_export.py tests/test_caption_api.py -q`
- [ ] Manual: `curl`/TestClient round trip printed byte count

**Dependencies:** Task 2
**Files likely touched:** `server.py`, `tests/test_overlay_export.py`
**Estimated scope:** S (2 files)

## Task 4: Export button and handler

**Description:** Add `EXPORT ALPHA OVERLAY` to the floating export bar in
`static/index.html` beside the burn button, and a handler in `static/app.js` that
reuses the burn flow: POST `/api/export/ass` for the current style and
`currentSegments`, then POST multipart to `/api/export/overlay-video`, then
download the blob as `{base}_overlay.mov`. Disable and relabel while running;
restore in `finally`. Tooltip explains the transparent `.mov` and where to drop it.

**Acceptance criteria:**
- [ ] Button appears next to the MP4 burn button with a clear label
- [ ] Handler sends the same segments and style as the burn export
- [ ] Failure shows the server detail and restores the button
- [ ] No new global state; reuses existing element lookup and download helper
- [ ] `node --check static/app.js` passes

**Verification:**
- [ ] `node --check static/app.js`
- [ ] Manual: start the app, export, confirm a `.mov` lands in Downloads with a
      non-trivial size and plays with transparency in a player

**Dependencies:** Task 3
**Files likely touched:** `static/index.html`, `static/app.js`
**Estimated scope:** S (2 files)

## Task 5: Real-clip evidence

**Description:** Run the overlay export on one real vertical corpus clip, then
record measured numbers in this plan: output size, duration vs source, fps vs
source, alpha coverage at a caption frame and a gap frame, and wall-clock render
time. If the result is wrong (cropped, stretched, mistimed), fix before docs.

**Acceptance criteria:**
- [ ] Overlay canvas equals the source display size (post-rotation)
- [ ] Overlay duration within one frame of the source
- [ ] Caption position matches the burned MP4 frame-for-frame on the same clip
- [ ] Numbers written under "Measured Results" below

**Verification:**
- [ ] Compare one overlay frame and one burned frame at the same timestamp
- [ ] `ffprobe` on both files, side by side

**Dependencies:** Task 4
**Files likely touched:** `tasks/plan_alpha_export.md` (results only)
**Estimated scope:** XS (evidence)

## Task 6: Docs, full suite, review, commit

**Description:** README export section gains the overlay option with the one-line
"drop it above your footage" instruction; `memory.md` gains an entry with the
verified numbers and the command contract. Run the full suite and
`/ponytail-review`, then commit.

**Acceptance criteria:**
- [ ] README documents the three export formats consistently
- [ ] `memory.md` entry states the measured numbers, not claims
- [ ] Full suite green; working tree clean after commit
- [ ] ponytail-review findings addressed or explicitly waived

**Verification:**
- [ ] `python -m pytest tests -q`
- [ ] `node --check static/app.js`, `node tests/js/caption_clock_test.js`
- [ ] `git status --short` empty

**Dependencies:** Task 5
**Files likely touched:** `README.md`, `memory.md`
**Estimated scope:** S

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Rotation metadata ignored → overlay sideways or wrong aspect | High | Task 1 swaps W/H for ±90/270 and derives aspect from that; Task 5 checks a rotated clip if one exists |
| `qtrle` is lossless and larger than H.264 | Med | Measured: 15.4 MB/min at 1080×1920 with sparse captions (~1.7 MB for a 59 s 360×640 clip). Stated in README; users who need small files burn an MP4 instead |
| VFR source: constant FPS overlay drifts from footage | Med | Use `avg_frame_rate`; note the limitation in README; do not pretend it is frame-exact for VFR |
| Duration mismatch between `-t` and the colour source | Low | Same `duration` value feeds both `d=` and `-t`; test tolerance ±1 frame |
| Odd width/height × 4 bytes per row | Low | qtrle `argb` has no 2-pixel constraint; still assert the exact requested size in tests |
| Long render has no progress and a fixed timeout | Med | Reuse the burn timeout pattern (600 s), surface the timeout error in the UI |
| Upload copies a large file to temp before probing | Med | Local single-user app; the work dir is removed in a background task. Note the cost in README |
| Player/NLE shows premultiplied grey fringes | Low | `argb` is straight alpha; verify visually in Task 5, not just in ffprobe |
| Font substitution in libass changes metrics | Med | Same generator and system fonts as the burn; Task 5 compares against the burned frame |

## Measured Results
Measured on 2026-10-30, this machine (ffmpeg 4.4-class build, no `libx264`).

**Real clip** — `static/samples/genius_ad.mp4`
- Source: 360×640, `30000/1001`, container 58.932 s.
- Overlay: 360×640, `qtrle` / `argb`, 1766 frames, 58.9255 s (0.2 frame short),
  1,746,855 bytes, 0.6 s wall clock.
- Alpha at t=3.0 s (caption on screen): peak 255, 0.98% of pixels inked.
- Alpha at t=6.0 s (gap): peak 0. Fully transparent, as it must be.
- Ink box vs an opaque black render of the same ASS at the same size:
  Δx −1/−2, Δy −2, Δw +4/+5, Δh +4 px. The offset is the alpha threshold
  (16) versus luma (40) catching more anti-aliased fringe; the caption sits in
  the same place, it is not shifted or rescaled.

**1080×1920 size and speed** — 10 s synthetic source
- 2,568,745 bytes for 10 s → **15.4 MB per minute**, 1.57 s wall clock.
- So the earlier "hundreds of MB" worry was wrong: qtrle RLE spends almost
  nothing on empty frames. The README now quotes the measured figure.

**Return shape:** flattened keys (`width`, `height`, `fps`, `duration`, `aspect`,
`rotation`) rather than a nested `geometry` dict, so the endpoint and the tests
read the same names. `fps_rational` stays internal.


## Open Questions
- Overlay only, or also a ProRes 4444 option for editors that prefer it?
  Recommendation: overlay only for now; `prores_ks` is one flag away if asked.
- Should the overlay endpoint accept a bare geometry JSON (no upload) for the
  hosted-style "render without the source" case? Recommendation: no. Our app is
  local and needs the real file for rotation/FPS.
