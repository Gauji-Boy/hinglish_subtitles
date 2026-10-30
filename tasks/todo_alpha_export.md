# TODO: Transparent Alpha Overlay Export (.mov)

Done 2026-10-30. Plan: `tasks/plan_alpha_export.md` (results at the bottom).
`tasks/plan.md` + `tasks/todo.md` still hold the unchecked safe-zone plan; untouched.

## Phase 1: Geometry and command

- [x] Task 1 — `overlay_export.py` pure helpers
  - [x] `probe_overlay_geometry(path)` → width, height (rotation-aware), fps
        (avg, then r_frame_rate), duration, aspect
  - [x] `overlay_ffmpeg_args(geometry, sub_name, out_path)` → exact list, no run
  - [x] Specific errors: missing file, no video stream, bad fps, zero duration
  - [x] `tests/test_overlay_export.py` covers rotation 0/90/180/270, fps
        fallback, aspect selection, arg list
  - [x] `python -m pytest tests/test_overlay_export.py -q` green

- [x] Task 2 — real 1 s alpha render
  - [x] `export_alpha_overlay(...)` mirrors `burn_subtitles_to_video` return shape
  - [x] tempdir `cwd` isolation for the ASS path
  - [x] test renders a generated clip: `qtrle`, `argb`, frames ≈ fps × duration
  - [x] alpha proof: ink where the caption is, 0 on a corner pixel, 0 after the
        caption ends
  - [x] failure + timeout return `{success: False}` and clean the temp dir
  - [x] `python -m pytest tests/test_overlay_export.py -q` green

### Checkpoint: Render Core
- [x] Pure tests run with no ffmpeg process
- [x] Real `.mov` verified by ffprobe, not by assertion alone
- [x] Alpha channel proven non-opaque in the empty region
- [x] Human review of the plan/approach before wiring the API

## Phase 2: Endpoint

- [x] Task 3 — `POST /api/export/overlay-video`
  - [x] multipart `video`, `subtitles` (`format_type` dropped: ASS-only by design)
  - [x] `video/quicktime`, `{base}_overlay.mov`
  - [x] `BackgroundTask(shutil.rmtree)`; cleanup on the error path
  - [x] bad upload → readable error, no traceback
  - [x] TestClient test asserts `qtrle` in the returned bytes
  - [x] `python -m pytest tests/test_overlay_export.py tests/test_caption_api.py -q`

### Checkpoint: API
- [x] Endpoint returns a playable `.mov`
- [x] No temp dirs left in `%TEMP%` after the call

## Phase 3: UI

- [x] Task 4 — export button + handler
  - [x] button in the floating export bar, label states what it is
  - [x] handler regenerates ASS with `currentSegments` + current style
  - [x] POSTs to `/api/export/overlay-video`, downloads `{base}_overlay.mov`
  - [x] busy state + `finally` restore + visible error
  - [x] `node --check static/app.js`

### Checkpoint: End to End
- [x] Endpoint round trip downloads a `.mov` (TestClient, real render)
- [x] File plays with a transparent background and captions in the right place
      (alpha plane verified; ink box matches an opaque render within 2 px)
- [x] Browser click on the new button: Playwright, real app, 1440x900 →
      `genius_ad_overlay.mov`, 1.63 MB, 0.8 s, no console errors
- [ ] Follow-up (found during that check, not fixed): the export row is 1302 px
      of content in 1106 px, so the last two buttons need a horizontal scroll

## Phase 4: Evidence, docs, review

- [x] Task 5 — real corpus clip
  - [x] display size, duration, fps match the source
  - [x] overlay ink box vs opaque render at the same timestamp agrees (±2 px)
  - [x] numbers written under "Measured Results" in the plan

- [x] Task 6 — ship
  - [x] README export section covers `.ass` / MP4 / overlay
  - [x] `memory.md` entry with measured numbers and the command contract
  - [x] `python -m pytest tests -q` green
  - [x] `node tests/js/caption_clock_test.js`
  - [x] `/ponytail-review` findings addressed or waived
  - [x] commit

### Checkpoint: Complete
- [x] Full suite green
- [x] Working tree clean
