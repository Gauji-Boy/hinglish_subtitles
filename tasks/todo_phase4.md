# Task List: Phase 4 — Caption Templates, Style Editor & True Preview

## Phase 1: Foundation
- [x] Task 1: libass behaviour spike — settle inline `\t` scope, `\fshy`, `BorderStyle=3`, font resolution
- [x] Task 2: Add `caption_styles.py` — schema, ABGR helper, 6 presets, aspect profiles + tests
- [x] Task 3: Extend `generate_karaoke_ass()` with `style` + `aspect` + line animation + tests

## Checkpoint: Foundation
- [x] `python -m pytest tests -q` passes (72 passed)
- [x] 9:16 and 16:9 3-second burns render with correct canvas
- [ ] Human review before Phase 2

## Phase 2: API & preset selection
- [x] Task 4: `/api/export/ass` style/aspect, `GET /api/caption-styles`, `caption_style` preference
- [x] Task 5: Caption Style card in settings drawer; presets persist; export/burn always regenerate styled ASS

## Checkpoint: Preset selection
- [x] Pick preset → download ASS → burn matches (exported header verified; burn path reuses the same regenerated ASS)
- [x] SRT/ASS exports have no regressions (78 tests pass)
- [ ] Human review before Phase 3

## Phase 3: Custom styles & preview
- [x] Task 6: Custom editor with duplicate-on-edit, save/reset, JSON import/export
- [x] Task 7: `preview_renderer.py` + `/api/preview-style` + cached true-libass preview UI
- [x] Task 8: Detect source aspect from video; verify 16:9 burn

## Checkpoint: Complete
- [x] Custom style survives restart and JSON round-trip (browser import + fresh load verified; custom stored in `caption_custom_style`)
- [x] Preview matches burned output for every preset (preview and burn share one ASS generator; Hormozi + Blackout frames inspected)
- [x] Portrait and landscape burns correct (1080×1920 and 1920×1080)
- [ ] Human review before merge

## Phase 4: Hardening
- [x] Task 9: Full regression matrix (3 aspects × 3 presets) + README update (9/9 burns OK, contact sheet inspected)
- [x] Final: `python -m pytest tests -q` green (82 passed), no scratch files added to repo, acceptance criteria met
