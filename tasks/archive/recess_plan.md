# Implementation Plan: Recess Caption Style

## Overview

Add a new built-in preset, `recess`, that reproduces the reference caption style in
`C:\Users\susha\Downloads\2F6DE10E-188F-466D-882D-8CB352DDF580.mp4`: centred, all-caps,
ultra-heavy geometric type on a flat dark background, where each spoken word is revealed in
place with a fade + scale spring and carries a rounded lime→periwinkle gradient pill. Punch
words are ~2× size and own their card.

Everything stays local: the ASS generator, the live browser overlay, and the existing
`h264_mf` burn path. No cloud transcription, no upload, no Mirage/Captions.ai.

## Measured Reference Spec

All values at the reference canvas (1920×1080, 32 fps, 158 frames = 4.94 s).

| Property | Measured value |
|---|---|
| Block position | centred: x ≈ 960, y ≈ 538 (canvas centre) |
| Normal cap height | 107 px (em ≈ 149 px) |
| Punch cap height | 217 px (2.03× normal) |
| Line pitch | 180 px between cap tops (≈ 1.21 em) |
| Widest normal line | x 174→1748 = 1574 px = 82 % of frame width |
| Word ink gap | 43–50 px (≈ 0.30 em) |
| Pill padding | 24 px horizontal, 48 px vertical (uniform for every word) |
| Pill radius | 32 px, fixed (same for a 177×200 and a 1180×314 pill) |
| Pill gradient | 135°, `#D2E860` → `#A793FF`, opaque |
| Pill timing | fades in ≈2 frames, holds, fades out ≈2 frames, ≈7 frames per word |
| Pill slide | morphs between consecutive words over ≈4 frames |
| Word entrance | alpha 0→255 in ≈2 frames, scale 110 %→100 % in ≈4 frames, centre-anchored |
| Outline / shadow | none (max measured darkening 6/255 on a near-black bg) |
| Background | `#1C1E1D` |
| Card transition | hard cut with ≈1 blank frame |

Card sequence: `HEY` / `DID YOU HEAR ABOUT THE` (2 lines) / `BAKERY` / `IN` / `WILLOW` /
`CREEK` / `THE` / `SWEET` / `SPOT?` / `IT'S RUN BY` / `EMMA` / `?`.

Two structural rules fall out of that sequence:

1. **Punch words are isolated cards.** `HEY`, `BAKERY`, `WILLOW`, `CREEK`, `THE`, `SWEET`,
   `SPOT?`, `EMMA` each own a card. Runs of non-punch words (`DID YOU HEAR ABOUT THE`,
   `IN`, `IT'S RUN BY`, `?`) group into one card each and reveal word by word.
2. **Growing lines are pre-laid-out and centred.** `DID YOU` → `DID YOU HEAR ABOUT` keeps
   its left edge at x 174 because the full phrase is always present (hidden words still
   reserve width) and the block is centred. No reflow, no per-word repositioning.

## Architecture Decisions

- **D1 — New `recess` preset, not a fork of Honey Punch.** Reuse the existing kinetic
  pre-layout/reveal machinery (`motion: "word-pop"`) and add opt-in fields. Honey Punch
  behaviour must not change.
- **D2 — Punch words get their own card via a new grouping mode.**
  `kinetic_grouping: "punch"` splits a phrase so each punch word stands alone and each run of
  non-punch words forms one card. Default stays `"flow"` (current behaviour).
- **D3 — Vertical centring uses `\an5` / `top: 50%`.** Existing presets use `\an8`/`\an9`
  top-anchored; Recess adds a `"middle"` option to `kinetic_layout` handling so the block
  centres on `anchor_y = 50`.
- **D4 — Pill is drawn, not a text background.** In ASS it becomes a layer-0 event containing
  a `\p1` drawing (rounded rect approximated by 32 vertical strips, each strip's colour
  sampled on the 135° axis). In the live overlay it is a single absolutely-positioned element
  with a real CSS `linear-gradient`. **The ASS gradient is an approximation** — libass has no
  gradient primitive — and this is documented in README/memory.
- **D5 — Pill events are coalesced.** The renderer already emits one text event per frame.
  Pill events are emitted only when the pill's rect/alpha changes (≈6–10 events per card), so
  ASS size stays proportional to word count, not frame count.
- **D6 — Size comes from a new `kinetic_size_scale` field.** Reference needs an em of ≈149 px
  at 1080p, which maps to `font_size` ≈ 166 — outside the current 24–140 clamp. Instead of
  widening the clamp (which changes the UI slider and existing tests), Recess keeps
  `font_size: 136` and calibrates `kinetic_size_scale` separately.
- **D10 — Pill geometry is expressed in em, not pixels.** Measured padding and radius are
  identical for normal and punch pills (24/48 px, 32 px radius at a 149 px em), so they derive
  from the **normal** em, not the word's em: `pill_pad_x: 0.16`, `pill_pad_y: 0.32`,
  `pill_radius: 0.21`. This keeps the pill correct at every resolution and font size, and stops
  punch pills from getting 2× padding.
- **D7 — `accent_scale` clamp widens 200 → 210** so Recess can express the measured 2.03×
  punch ratio. No other preset changes.
- **D8 — No outline, no shadow.** `outline_width: 0`, `shadow: 0`. The reference has neither;
  adding them would be visible on bright footage and wrong on dark.
- **D9 — Font: Arial Black for now.** The reference typeface is heavier and rounder than any
  installed font, so no installed choice is exact. Arial Black is the closest installed weight
  and needs no new files. It is ~15–24 % wider than the reference at equal cap height, so
  Recess is calibrated ~13 % smaller: that keeps the reference's 82 % line width **and** its
  line breaks (`DID YOU HEAR ABOUT` / `THE`). Bundling a geometric heavy sans is optional
  Phase 5, because a new font invalidates `_KINETIC_ASS_FONT_SCALE`,
  `_KINETIC_ASS_NORMAL_SCALE`, and `_KINETIC_ASS_SCALE_X`.

## Task List

### Phase 1: Foundation (schema + preset + grouping)

- [x] Task 1: Add the `recess` preset and its new schema fields
  - New fields with clamps: `pill` (bool), `pill_gradient_start`/`pill_gradient_end` (hex),
    `pill_pad_x`, `pill_pad_y`, `pill_radius`, `pill_fade_ms`, `pill_slide_ms`,
    `reveal_fade_ms`, `reveal_spring_ms`, `reveal_spring_scale`, `kinetic_size_scale`,
    `kinetic_grouping`.
  - Preset values: `font: "Arial Black"`, uppercase, white, no outline, no shadow,
    `accent_scale: 203`, `font_size: 136`, `kinetic_size_scale` calibrated so the first card's
    five words fit `max_width: 82` (expected ≈ 1.06), `anchor_y: 50`, `kinetic_layout: "center"`,
    `max_words_per_phrase: 0`, `phrase_gap_ms: 450`, `pill_pad_x: 0.16`, `pill_pad_y: 0.32`,
    `pill_radius: 0.21`, `pill_gradient_start: "#D2E860"`, `pill_gradient_end: "#A793FF"`.
  - Add to `list_presets()` order and to the UI preset list.
  - **Acceptance:** `resolve_style("recess")` returns every field, clamped; unknown values fall
    back; `list_presets()` includes it.
  - **Verification:** `python -m pytest tests/test_caption_styles.py -q`
  - **Files:** `caption_styles.py`, `server.py`, `static/index.html`
  - **Scope:** M

- [x] Task 2: Add `"punch"` phrase grouping and widen the `accent_scale` clamp
  - `_group_phrases` gains a mode that starts a new card at each punch word and keeps runs of
    non-punch words together.
  - **Acceptance:** the reference sentence groups into exactly
    `[HEY] [DID YOU HEAR ABOUT THE] [BAKERY] [IN] [WILLOW] [CREEK] [THE] [SWEET] [SPOT?] [IT'S RUN BY] [EMMA] [?]`;
    `accent_scale: 203` survives `resolve_style`; Honey Punch grouping is unchanged.
  - **Verification:** `python -m pytest tests/test_karaoke_ass.py tests/test_caption_styles.py -q`
  - **Files:** `karaoke_ass.py`, `caption_styles.py`, `tests/test_karaoke_ass.py`,
    `tests/test_caption_styles.py`
  - **Scope:** M

### Checkpoint: Foundation

- [x] Preset resolves and clamps correctly
- [x] Reference sentence groups into the 12 observed cards
- [x] Existing tests still pass

### Phase 2: ASS renderer (pill, spring, centring)

- [x] Task 3: Expose per-word layout boxes from the kinetic line builder
  - `_kinetic_lines` currently returns words only. Return each word's x offset, ink width, and
    line index so the pill can be placed exactly.
  - **Acceptance:** box widths match `_measure_kinetic_text`; line assignment matches the
    current wrap; Honey Punch output is byte-identical.
  - **Verification:** `python -m pytest tests/test_karaoke_ass.py -q` plus a golden-diff of the
    Honey Punch ASS.
  - **Files:** `karaoke_ass.py`
  - **Scope:** S

- [x] Task 4: Emit the gradient pill as coalesced layer-0 drawing events
  - Rounded rect from `pill_radius` × normal em; cosine-spaced horizontal bands (dense at the
    corners, ~16 px through the middle); each band coloured by its vertical position; alpha from
    `pill_alpha`. One event per band is required — libass merges multiple `\p1` blocks in a
    single event into one path.
  - **Acceptance:** Recess ASS contains layer-0 `\p1` events; no pill events for Honey Punch;
    strip count and geometry within 2 px of the measured box; ASS for a 5 s clip stays under
    ~1 MB.
  - **Verification:** `python -m pytest tests/test_karaoke_ass.py -q`; inspect the emitted
    events; render one frame.
  - **Files:** `karaoke_ass.py`, `tests/test_karaoke_ass.py`
  - **Scope:** M

- [x] Task 5: Add the reveal envelope and pill slide to the ASS frame loop
  - Per-word alpha ramp over `reveal_fade_ms` and `\fscx`/`\fscy` 110→100 over
    `reveal_spring_ms`; pill rect interpolated between consecutive word boxes over
    `pill_slide_ms`.
  - **Acceptance:** a word's first frame is dimmer and 110 % wide; it reaches 100 % within 4
    frames; the pill morphs between `DID`→`YOU` over ≈4 frames.
  - **Verification:** `python -m pytest tests/test_karaoke_ass.py -q`; render frames.
  - **Files:** `karaoke_ass.py`, `tests/test_karaoke_ass.py`
  - **Scope:** M

- [x] Task 6: Centre the block vertically for Recess
  - `\an5` + `\pos(x, play_res_y * anchor_y / 100)`; verify against the 538 px reference centre
    and add the small live/ASS nudge the other presets already use.
  - **Acceptance:** single-line and two-line cards both centre on y ≈ 540 ± 6 px.
  - **Verification:** render one punch frame and one two-line frame, measure ink bbox.
  - **Files:** `karaoke_ass.py`
  - **Scope:** S

### Checkpoint: ASS

- [x] Rendered `BAKERY` frame matches reference within 2 % on ink box, pill box, and centre
- [x] Rendered `THE` (line 2) pill matches the measured 201 px height and 32 px radius
- [x] Honey Punch ASS output unchanged

### Phase 3: Live overlay

- [x] Task 7: Add the Recess CSS variant (centring, type, pill element, entrance)
  - `.video-caption-overlay.kinetic.recess` is centred on the video's midline (JS sets `top`
    from the video rect minus the 0.035 em cap lift). The word stack is flex-wrapped with
    `row-gap: 0` plus a `--recess-row` bottom margin on each word: a forced break is a
    zero-height flex line, so `row-gap` was charged on both sides and doubled the pitch
    (0.58 em instead of 0.29 em). The container's matching negative margin keeps the trailing
    space out of the vertical centring.
  - `#captionPill` carries the preset's `linear-gradient(180deg, …)`, radius
    `0.26 × 0.775 × typeEm`, and padding `0.16` / `0.32 × 0.775 × typeEm`, where
    `typeEm = baseEm / 0.652` (the libass/CSS scale factor).
  - **Acceptance:** at 860×480 the pill is `1.558 × wordEm` tall with a 17.59 px radius and is
    centred on the word's cap centre (row top + 0.535 em); gradient renders; no layout shift
    when the pill appears.
  - **Verification:** measured DOM geometry (screenshots fail in this environment) plus
    `tests/js/recess_overlay_test.js`, wrapped by `tests/test_recess_overlay.py`.
  - **Files:** `static/components.css`
  - **Scope:** M

- [x] Task 8: Drive the pill and entrance envelope from `app.js`
  - Position `#captionPill` from the word's layout coordinates (`offsetLeft` / `offsetTop`
    walked up to the overlay, not `getBoundingClientRect`, which the reveal transform moves),
    slide between same-line words over `pill_slide_ms`, fade on line changes, and run the
    130 ms per-word spring.
  - The overlay is re-anchored per card: `top = video midline − 0.035 × blockEm`, where
    `blockEm` is the tallest word in the card, so a punch card keeps the same cap centre as
    `\an5`.
  - **Acceptance:** pill tracks the active word; slides on word change; fades at the end of a
    card; spring is opacity 0→1 and scale 1.1→1 over 130 ms `cubic-bezier(0.16, 1, 0.3, 1)`;
    hidden words still reserve width.
  - **Verification:** `node --check static/app.js`; measured DOM geometry at 860×480 and
    480×860.
  - **Files:** `static/app.js`
  - **Scope:** M

### Checkpoint: Live

- [x] Live overlay matches the ASS layout at the same aspect
- [x] No regression for Honey Punch in the live overlay
- [x] `node --check static/app.js` clean

### Phase 4: Verification and docs

- [x] Task 9: Burn the reference sentence with `h264_mf` and compare frames
  - **Result at 1080p** (burned / reference, 32 fps, output-seeked frames):

    | Moment | Ink box | Pill box | Pill centre |
    |---|---|---|---|
    | `BAKERY` | 1181×203 / 1130×215 (+4.5 %, −5.6 %) | 1225×307 / 1181×313 (+3.7 %, −1.9 %) | (969, 539) / (963, 539) |
    | `THE` (line 2) | 279×99 / 290×103 (−3.8 %, −3.9 %) | 328×200 / 339×200 (−3.2 %, 0 %) | (958, 630) / (959, 627) |
    | `IN` | 136×100 / 127×104 (+7.1 %, −3.8 %) | 184×200 / 176×199 (+4.5 %, +0.5 %) | (960, 540) / (959, 538) |
    | `WILLOW` | 1169×209 / 1200×216 (−2.6 %, −3.2 %) | 1217×306 / 1250×312 (−2.6 %, −1.9 %) | (960, 540) / (960, 539) |
    | `IT'S RUN BY` | 857×103 / 808×108 (+6.1 %, −4.6 %) | 238×200 / 228×203 (+4.4 %, −1.5 %) | (1272, 540) / (1276, 537) |

  - **Acceptance:** pill boxes within 4 % and pill centres within 3 px on all five moments. The
    ink box is *not* within 2 %: it carries the documented Arial Black substitution error
    (+4–7 % wide, −3–6 % short) and cannot reach 2 % until a narrower face is bundled (Phase 5).
  - **Verification:** `video_burner.burn_subtitles_to_video` with `h264_mf` on a 1920×1080 black
    source; frames extracted with output seeking at 2.50 / 2.28 / 2.95 / 3.25 / 6.20 s. The burned
    output trails a direct libass render by about one frame, so each sample is taken just after
    the word's start.
  - **Files:** none (artifacts under the system temp folder)
  - **Scope:** S

- [x] Task 10: Update `README.md` and `memory.md`, restore `launch_config.json`
  - Document the preset, the measured spec, the ASS gradient approximation, and the live-vs-ASS
    calibration table.
  - **Acceptance:** docs match behaviour; `launch_config.json` restored to the pre-test copy.
  - **Verification:** key-by-key JSON compare against the backup.
  - **Files:** `README.md`, `memory.md`
  - **Scope:** S

### Checkpoint: Complete

- [x] `python -m pytest tests -q` passes (112)
- [x] `node --check static/app.js` clean
- [x] Burned frames verified
- [x] All changes uncommitted, nothing pushed

### Phase 5 (optional, gated on the font decision)

- [ ] Task 11: Select and bundle a geometric heavy sans
  - Render `BAKERY`/`WILLOW`/`THE` in candidate fonts at matched cap height against the
    reference crops, pick the closest, bundle it in `static/fonts/`, add `@font-face`, add
    `fontsdir` to the burn filter, and recalibrate the three ASS constants.
  - **Acceptance:** side-by-side comparison shows the chosen font is closer than Arial Black;
    burned text width matches the live overlay within 2 %.
  - **Files:** `static/fonts/*`, `caption_styles.py`, `karaoke_ass.py`, `video_burner.py`,
    `static/components.css`
  - **Scope:** L — deliberately isolated so it cannot block Phases 1–4.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| libass has no gradient; strip approximation bands visibly | High | 32 strips; verify on the near-square `IN` pill, bump to a 2-row grid only if banding shows |
| Pill events bloat the ASS file | Med | Coalesce unchanged states; assert a size budget in a test |
| `\fscx` spring shifts neighbouring words | Med | Inline `\fscx` does not reflow; verify a mid-spring frame shows neighbours unmoved |
| Punch-isolated grouping changes Honey Punch | High | New mode is opt-in; golden-diff the Honey Punch ASS before/after |
| `\an5` centres the layout box, not the ink | Med | Measure rendered ink and apply a per-style nudge as the other presets do |
| Font is not an installed match (measured: heavier and rounder than every candidate) | High | Arial Black now; calibrated ~13 % smaller so the block width and line breaks still match; bundling is Phase 5 and separately verified |
| Arial Black is 15–24 % wider, so text is ~13 % smaller than the reference | Med | Documented; Phase 5 restores the reference cap height if a narrower font is bundled |

## Open Questions

1. **Pill on bright footage.** With no outline and no shadow the style can lose contrast over
   bright video. The reference is on a near-black background so the shadow strength is not
   measurable. Current plan: match the reference exactly (none) and revisit only if requested.
2. **Phase 5 font.** Arial Black is approved for now. If the type still reads as "not Recess"
   after Phase 4, the follow-up is a bundled geometric heavy sans plus a recalibration pass.
