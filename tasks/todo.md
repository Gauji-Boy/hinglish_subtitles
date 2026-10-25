# Task List: Recess Caption Style

Plan: `tasks/plan.md`

## Phase 1: Foundation

- [x] Task 1: Add the `recess` preset and its new schema fields (pill, reveal, size scale, grouping)
- [x] Task 2: Add `"punch"` phrase grouping and widen the `accent_scale` clamp to 210

### Checkpoint: Foundation
- [x] `resolve_style("recess")` clamps every field
- [x] Reference sentence groups into 12 cards: HEY / DID YOU HEAR ABOUT THE / BAKERY / IN / WILLOW / CREEK / THE / SWEET / SPOT? / IT'S RUN BY / EMMA / ?
- [x] Full test suite passes (112)

## Phase 2: ASS renderer

- [x] Task 3: Expose per-word layout boxes from `_kinetic_lines`
- [x] Task 4: Emit the gradient pill as coalesced layer-0 drawing events
- [x] Task 5: Add the reveal envelope (fade + 110→100 spring) and pill slide
- [x] Task 6: Centre the block vertically with `\an5`

### Checkpoint: ASS
- [x] `BAKERY` frame matches reference within 2 % (ink box, pill box, centre)
- [x] `THE` line-2 pill matches 201 px height / 32 px radius
- [x] Honey Punch ASS unchanged

## Phase 3: Live overlay

- [x] Task 7: Add the Recess CSS variant (centring, pill element, entrance)
- [x] Task 8: Drive pill position/slide/fade and the word spring from `app.js`

### Checkpoint: Live
- [x] Live layout matches ASS at 860×480 and 480×860
- [x] Honey Punch live overlay unchanged
- [x] `node --check static/app.js` clean
- [x] `tests/js/recess_overlay_test.js` green (wrapped by `tests/test_recess_overlay.py`)

## Phase 4: Verification and docs

- [x] Task 9: Burn the reference sentence with `h264_mf` and compare frames
- [x] Task 10: Update `README.md` + `memory.md`, restore `launch_config.json`

### Checkpoint: Complete
- [x] `python -m pytest tests -q` passes (112)
- [x] Burned frames verified against reference (pill ≤4 %, centre ≤3 px; ink carries the Arial Black substitution error)
- [x] All changes uncommitted

## Phase 5 (optional — gated on the font decision)

- [ ] Task 11: Select and bundle a geometric heavy sans, then recalibrate the ASS constants
