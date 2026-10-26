# Task List: 9:16 Safe Zones & Dead Space Indicator Polish

Plan: `tasks/plan.md`

## Phase 1: Indicator Discoverability & Auto-On
- [x] Task 1: Auto-enable dead space overlay & clarify button label (`index.html`, `app.js`, `components.css`)

## Phase 2: Calibrated 2026 Geometry & Collisions
- [x] Task 2: Calibrate dead-space constants and collision thresholds (`app.js`, `components.css`, `tests/js/safe_zone_test.js`)

### Checkpoint: Indicator & Geometry Verification
- [x] Safe-zone overlay opens automatically on portrait video
- [x] Overlay dimensions match 11.5% / 23.5% / 15.2%
- [x] All JS tests in `safe_zone_test.js` pass

## Phase 3: "Sweet Spot" Placement & Docs
- [x] Task 3: Add one-click placement chips under POSITION slider (`index.html`, `app.js`, `components.css`)
- [x] Task 4: Persistent Memory & Documentation update (`memory.md`)

### Checkpoint: Complete
- [x] Full regression test suite (`pytest`) passes (332/332)
- [x] `node safe_zone_test.js` passes
- [x] Working tree clean
