# Implementation Plan: Phase 4 — Caption Templates, Style Editor & True Preview

## Overview

Expose the existing word-level karaoke pipeline as a set of editable caption styles, add a custom-style editor with import/export, and add a true libass preview. The generator already produces `\k` word timing; this phase makes the look selectable, canvas-aware, and verifiable before a full burn. Built-ins are immutable; edits clone into one saved custom style. Scope is Windows-only, matching the rest of the app.

Task lists in this repo use the existing `plan_phaseN.md` / `todo_phaseN.md` convention (Phases 1–3 already use it). This plan does not overwrite any prior plan; `tasks/plan_phase1..3.md` and their todos are complete.

## Architecture Decisions

1. **Styles are data, not code.** One `caption_styles.py` module owns the schema, the five built-in presets, the blank preset, normalization/clamping, ABGR conversion, and the three aspect profiles. The API and generator both import it. No duplicated preset JSON in `static/`.
2. **Built-ins are read-only.** Editing any control clones the active preset into a single `Custom` style. The custom style is persisted under `caption_style` in `launch_config.json`. Import/export is client-side JSON.
3. **System fonts only in v1.** The app is Windows-only; stock `Impact`, `Arial Black`, `Segoe UI`, `Georgia`, and `Consolas` are deterministic and require no download, no `fontsdir`, and no variable-font weight guessing. Bundling Montserrat/Inter/Bebas is deferred. The current default `Montserrat ExtraBold` is removed because it is not installed and silently falls back.
4. **Canvas comes from the source video, not a constant.** `/api/export/ass` accepts `aspect` (`9:16`, `16:9`, `1:1`). The client detects it from the loaded video's metadata and falls back to `9:16` (short pacing) or `16:9` (long pacing). PlayRes, font size, and margins come from the aspect profile.
5. **Word colour is the dynamic core; motion is line-level.** The spike confirmed inline `\t` *does* scope per word, but a two-stage pop-and-settle does not work (the second `\t` wins from t=0) and a single `\t` leaves the word enlarged for the rest of the card. A timed per-word pop still needs one event per word plus text measurement. v1 ships `\k` fill plus a short `\fad` entry per card. `\fshy` is invalid and is ignored. Do not use `\r` or static per-word scale inside a `\k` line: both corrupt the karaoke colour state (observed).
6. **Pills are per-line.** `BorderStyle=3` draws one box per event. Since an event is one caption card, the "pill" preset boxes the whole line, not each word. Per-word pills need separate events and are out of scope.
7. **Preview is a real libass render, on a bundled backdrop.** A short MP4 is rendered with the exact style through FFmpeg on a generated dark gradient, cached by `hash(style, aspect)`. This proves font, color, outline, box, margins, and animation without re-uploading the user's video. The CSS sample in the drawer is for instant feedback and is labelled approximate.
8. **The client stops trusting the precomputed ASS blob.** `hinglish_engine.py` and `hindi_to_english_engine.py` precompute `ass_karaoke` at transcribe time with default style. Both export handlers currently short-circuit to that blob when `hasManualEdits()` is false, which would ignore any chosen style. Export and burn always request fresh ASS with the active style.
9. **Backward compatibility.** The Hormozi preset keeps the ASS style name `HormoziYellow` so existing tests and scripts keep working. Existing generator keywords stay valid; `style` is a new optional argument.
10. **No new dependencies.** Python stdlib + existing FFmpeg. No font downloads, no Pillow, no canvas renderer.

## Spike Findings (Task 1, observed frames)

- `\fshy-60` produced an identical frame to no tag: **unknown tag, ignored**.
- `BorderStyle=3` draws **one box around the whole line**, not per word.
- `Impact`, `Arial Black`, `Segoe UI`, `Georgia`, `Consolas` all resolve and render distinctly.
- Inline `\t` **is scoped per word**: a 200% transform on the middle word scaled only that word.
- **Chained `\t` in one block does not work**: `\t(1000,1080,130%)` + `\t(1080,1160,100%)` left the word at 100% at t=1040 ms — the second transform won from t=0.
- `\r` inside a `\k` line **shifted the karaoke highlight** (a future word turned yellow early). Avoid.
- Static per-word `\fscx130` + reset also shifted the karaoke highlight. Avoid.
- `\k` colour semantics: **Primary = spoken/current, Secondary = upcoming** (opposite of the docstring). With Primary yellow and Secondary white, spoken words are yellow; with the current preset (Primary white, Secondary yellow), *upcoming* words are yellow. The preset mapping must be corrected in Task 3.
- Per-word colour via `\t` was unreliable: a future word turned yellow ~600 ms before its transform start. Not used.

## Dependency Graph

```
Task 1  libass spike (decision gate)
            │
Task 2  schema + presets ──────────┐
            │                      │
Task 3  generator style/aspect     │
            │                      │
Task 4  API + preferences ─────────┤
            │                      │
Task 5  preset picker UI ──────────┘
            │
      ┌─────┴─────┐
Task 6 custom   Task 7 preview
      └─────┬─────┘
Task 8 aspect detection + burn verify
            │
Task 9 regression + docs
```

## Task List

### Phase 1: Foundation and de-risk

#### Task 1: libass behaviour spike (decision gate)

**Description:** Render a small throwaway ASS file through the local FFmpeg/libass and settle five questions before any generator work: does inline `\t` scope per word inside one event; is `\fshy` ignored; does `BorderStyle=3` box the whole line; does `\k` interact correctly with `\t`; do the five stock Windows fonts resolve by name. This is a scratch experiment under `%TEMP%`, not a repo change.

**Acceptance criteria:**
- [ ] Each question is answered with an observed frame, not an assumption.
- [ ] The v1 animation decision (line pop vs per-word pop) is recorded in this plan.
- [ ] The five font names render distinctly in a captured frame.

**Verification:**
- [ ] Tests pass: `python -m pytest tests -q` (unchanged, proves no collateral damage)
- [ ] Manual check: inspect extracted PNG frames for the tag/font cases
- [ ] Findings appended to "Risks and Mitigations" or "Open Questions"

**Dependencies:** None

**Files likely touched:** none in the repo; scratch files under `%TEMP%\ass_spike\`

**Estimated scope:** XS (scratch only)

#### Task 2: Style schema, presets, and aspect profiles

**Description:** Add `caption_styles.py` with a validated style dict, RGB→ASS ABGR conversion, clamping, five built-in presets, a blank preset, and aspect profiles. This is the single source of truth used by the generator and the API.

**Acceptance criteria:**
- [ ] `PRESETS` contains `hormozi`, `vox`, `cyber`, `blackout`, `editorial`, `blank`.
- [ ] `normalize_style()` rejects unknown ids, clamps numeric ranges, and validates hex colours.
- [ ] Style exposes `base_color` (upcoming words) and `highlight_color` (spoken words), matching libass `\k` semantics.
- [ ] `#FFC700` converts to `&H0000C7FF`; `#00000080` alpha is honoured.
- [ ] Aspect profiles return the documented PlayRes/font/margin for 9:16, 16:9, 1:1.
- [ ] Every preset normalizes without error.

**Verification:**
- [ ] Tests pass: `python -m pytest tests/test_caption_styles.py -q`
- [ ] Manual check: print normalized presets and eyeball values

**Dependencies:** Task 1 (confirms font names and box behaviour)

**Files likely touched:**
- `caption_styles.py` (new)
- `tests/test_caption_styles.py` (new)

**Estimated scope:** S (2 files)

#### Task 3: Generator accepts style and aspect

**Description:** Extend `generate_karaoke_ass()` with optional `style` and `aspect`, keeping all existing keyword arguments and defaults working. Emit the selected style name, PlayRes from the profile, style-derived font/colours/margins, uppercase handling, and the v1 animation chosen in Task 1.

**Acceptance criteria:**
- [ ] Calling with no `style` keeps the `HormoziYellow` style name, `\k` tags, and timings; colour mapping is corrected so spoken words take the highlight colour and upcoming words the base colour.
- [ ] `style=PRESETS["vox"]` changes font, colours, outline, and margins in the header.
- [ ] `aspect="16:9"` sets `PlayResX: 1920` / `PlayResY: 1080`; `1:1` sets 1080×1080.
- [ ] Uppercase presets uppercase the dialogue text; Hinglish/word selection is unchanged.
- [ ] Each card emits a short `\fad(80,0)`; no `\fshy`, no `\r`, and no static per-word scale.
- [ ] ASS colours are emitted ABGR, not RGB.

**Verification:**
- [ ] Tests pass: `python -m pytest tests/test_karaoke_ass.py -q`
- [ ] Manual check: render one 3 s clip per aspect and inspect a frame

**Dependencies:** Tasks 1, 2

**Files likely touched:**
- `karaoke_ass.py`
- `tests/test_karaoke_ass.py`

**Estimated scope:** M (2 files)

### Checkpoint: Foundation
- [ ] All tests pass
- [ ] A 9:16 and a 16:9 3-second burn render with correct canvas and readable captions
- [ ] Review with human before proceeding

### Phase 2: API and preset selection

#### Task 4: API style passthrough and preferences

**Description:** Accept `style` and `aspect` in `/api/export/ass`, add `GET /api/caption-styles`, and persist the active style through the existing preferences endpoints. Add `caption_style` to the GET defaults, the POST form, and the initial-config injection whitelist.

**Acceptance criteria:**
- [ ] POST `/api/export/ass` with `style: "vox"` returns a Vox-styled `.ass`.
- [ ] Unknown style ids fall back to the default preset rather than erroring.
- [ ] `GET /api/caption-styles` returns presets plus the saved custom style.
- [ ] `caption_style` survives a preferences POST, a GET, and a page reload.
- [ ] Existing payloads without `style` still return 200.

**Verification:**
- [ ] Tests pass: `python -m pytest tests/test_caption_api.py -q`
- [ ] Manual check: restart the server and confirm the saved style is injected

**Dependencies:** Tasks 2, 3

**Files likely touched:**
- `server.py`
- `tests/test_caption_api.py` (new)
- `launch_config.json` (default key only)

**Estimated scope:** S (3 files)

#### Task 5: Preset picker in the settings drawer

**Description:** Add a "Caption Style" card to the settings drawer with five preset swatches, a live CSS sample labelled approximate, and persistence. Wire both export handlers to always request fresh ASS with the active style and detected aspect.

**Acceptance criteria:**
- [ ] Selecting a preset updates the sample and the persisted preference.
- [ ] Downloading `.ass` after selecting Vox produces Vox values in the header.
- [ ] Burn uses the selected style, not the precomputed `ass_karaoke` blob.
- [ ] The card works on first load using the injected config.

**Verification:**
- [ ] Tests pass: `python -m pytest tests -q`
- [ ] Manual check: switch presets, download ASS, grep the style line, then burn a 3 s clip
- [ ] Manual check: reload the page; selection persists

**Dependencies:** Task 4

**Files likely touched:**
- `static/index.html`
- `static/app.js`
- `static/components.css` (or existing style block)

**Estimated scope:** M (3 files)

### Checkpoint: Preset selection
- [ ] End-to-end: pick preset → download ASS → burn → output matches
- [ ] No regression in SRT/ASS export
- [ ] Review with human before proceeding

### Phase 3: Custom styles and true preview

#### Task 6: Custom style editor with import/export

**Description:** Add a compact customizer for the active style: font, size, uppercase, base colour, active colour, outline width, box on/off, vertical position. Editing clones a built-in into a single `Custom` style. Add save, reset, and JSON import/export.

**Acceptance criteria:**
- [ ] Editing a built-in does not mutate it; a `Custom` clone becomes active.
- [ ] Saving persists `caption_style` and reloads it on restart.
- [ ] Exported JSON re-imports to an identical normalized style.
- [ ] Invalid/oversized values are clamped server-side, not trusted from the client.

**Verification:**
- [ ] Tests pass: `python -m pytest tests/test_caption_styles.py tests/test_caption_api.py -q`
- [ ] Manual check: clone, save, restart, re-import

**Dependencies:** Task 5

**Files likely touched:**
- `static/index.html`
- `static/app.js`
- `caption_styles.py`
- `tests/test_caption_styles.py`

**Estimated scope:** M (4 files)

#### Task 7: True libass preview

**Description:** Add `preview_renderer.py` and `GET /api/preview-style` that render a 2.5 s MP4 of the active style on a generated dark gradient at the target aspect, using the same ASS path as the final burn. Cache by style/aspect hash. In the UI, add a "Verify render" button that plays the cached MP4 and a 400 ms debounce while controls are moving.

**Acceptance criteria:**
- [ ] Preview MP4 is produced by the real `ass` filter, not CSS.
- [ ] Repeat requests for the same style/aspect return the cached file in under 150 ms.
- [ ] A cold render finishes under 3 s on this machine and is silent.
- [ ] The CSS sample is visibly labelled approximate.
- [ ] Preview works with no video uploaded.

**Verification:**
- [ ] Tests pass: `python -m pytest tests/test_preview_renderer.py -q`
- [ ] Manual check: preview each preset; confirm fonts/colours match the burned output
- [ ] Manual check: measure cold vs cached latency

**Dependencies:** Tasks 3, 5

**Files likely touched:**
- `preview_renderer.py` (new)
- `server.py`
- `static/app.js`
- `static/index.html`
- `tests/test_preview_renderer.py` (new)

**Estimated scope:** M (5 files)

#### Task 8: Aspect detection and burn verification

**Description:** Detect source aspect from the loaded video metadata in the browser, use it for ASS export and burn, and verify the 16:9 path end-to-end. Fall back to pacing-derived aspect when only audio is loaded.

**Acceptance criteria:**
- [ ] A 1920×1080 upload produces `PlayResX: 1920` / `PlayResY: 1080`.
- [ ] A 1080×1920 upload keeps 9:16.
- [ ] Audio-only export uses 9:16 for short pacing and 16:9 for long pacing.
- [ ] Burned 16:9 output has readable margins and no stretched glyphs.

**Verification:**
- [ ] Tests pass: `python -m pytest tests -q`
- [ ] Manual check: burn one landscape and one portrait sample, inspect frames

**Dependencies:** Task 5

**Files likely touched:**
- `static/app.js`
- `karaoke_ass.py` (only if aspect fallback logic belongs there)

**Estimated scope:** S (2 files)

### Checkpoint: Complete
- [ ] Custom style survives restart and round-trips through JSON
- [ ] Preview matches burned output for all presets
- [ ] Portrait and landscape burns are correct
- [ ] Review with human before merge

### Phase 4: Hardening

#### Task 9: Regression pass and documentation

**Description:** Run the full suite, exercise the matrix (3 aspects × 3 presets), and document the feature in the README: presets, editing, import/export, preview, and the known per-word animation limitation.

**Acceptance criteria:**
- [ ] Full suite passes (55 existing + new tests).
- [ ] README documents the style workflow and the v1 animation limits.
- [ ] No leftover debug endpoints or scratch files in the repo.

**Verification:**
- [ ] Tests pass: `python -m pytest tests -q`
- [ ] Manual check: follow the README flow from a clean start

**Dependencies:** Tasks 6, 7, 8

**Files likely touched:**
- `README.md`
- `tests/` (only if a gap is found)

**Estimated scope:** S (2 files)

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Inline `\t` chained pop-and-settle does not work | High | Spike-confirmed; v1 uses `\k` colour + `\fad`. Per-word motion stays v2 with per-word events |
| `\r` / static per-word scale corrupts `\k` state | High | Spike-confirmed; generator forbids both in karaoke lines |
| `\k` colours are inverted vs the old docstring | High | Preset schema names them `base`/`highlight`; Task 3 corrects the mapping (intentional visual change) |
| Precomputed `ass_karaoke` bypasses the chosen style | High | Remove the client short-circuit; always regenerate with style (Task 5) |
| PlayRes/video mismatch on 16:9 | High | Aspect detection from video metadata; 16:9 burn check in Task 8 |
| Preview adds upload/latency cost | Med | Render on a bundled gradient sample, cache by hash, debounce 400 ms |
| Stock font availability differs | Low | All five are stock Windows; fallback is libass's normal substitution, documented |
| `caption_style` bloats the config and breaks old readers | Low | Whitelist + normalize; unknown keys preserved; default added |
| Per-word pill expectation | Low | Document that `BorderStyle=3` boxes the line; per-word pills are v2 |

## Open Questions

1. **Fonts:** system-only for v1 (recommended, zero bytes) or bundle Montserrat/Bebas OFL TTFs (~500 KB, needs `fontsdir` and variable-font handling)?
2. **Preview content:** gradient sample (recommended, no re-upload) or the user's own footage (requires caching the last upload server-side)?
3. **Custom styles:** one `Custom` slot (recommended) or per-preset overrides?
4. **Per-word animation:** accept colour fill + `\fad` for v1 (recommended; spike proved chained transforms unreliable) and revisit per-word scale/bounce in v2?

## Out of Scope (v2+)

- Per-word scale/bounce, per-word pills (needs per-word events + text measurement).
- Auto emoji (colour emoji is unreliable through libass).
- Speaker-aware caption colours (diarization data exists; separate phase).
- Full canvas/keyframe editor, beat-reactive effects, per-word drag positioning.
- Bundled fonts and `fontsdir` plumbing (only if Open Question 1 flips).
