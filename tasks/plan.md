# Implementation Plan: 9:16 Safe Zones & Dead Space Indicator Polish

## Overview
Polish the vertical 9:16 safe zone and dead space indicator in `hinglish_subtitles` so creators immediately see where platform UI conflicts occur without hunting for a hidden button. Calibrate overlay boundaries to 2026 short-form specs (TikTok, Reels, Shorts from Blitzcut guide), auto-enable the indicator on portrait clips, and add a one-click "Sweet Spot" positioning snap.

## Architecture Decisions
- **D1 — Auto-enable on portrait video load, off on landscape:** Instead of resetting `safeZoneOn = false` on every video load, portrait videos (`video-portrait`) automatically initialize with `safeZoneOn = true`. Landscape videos disable the button and hide the overlay.
- **D2 — Explicit Button Labeling:** Rename the player button from `9:16` to `🛡️ SAFE ZONE` with clear tooltip and high-contrast active state styling.
- **D3 — 2026 Calibrated Cross-Platform Universal Percentages:**
  Update hardcoded constants in `app.js` and `components.css`:
  - `SAFE_ZONE_TOP`: **`11.5%`** (was 10%, clears Reels/TikTok search & tabs)
  - `SAFE_ZONE_BOTTOM`: **`23.5%`** (was 25%, accounts for Reels late-2025 audio bar expansion up to 450 px)
  - `SAFE_ZONE_RIGHT`: **`15.2%`** (was 15%, accounts for TikTok Jan 2026 "Add to Playlist" button up to 164 px)
- **D4 — Quick Placement Chips Under Slider:** Add 4 quick preset chips (`Top 20%`, `Center 50%`, `Sweet Spot 68%`, `Bottom 80%`) directly beneath the Position slider. Clicking any chip sets the slider and invokes the existing `stylePositionPatch()` to update both kinetic (`anchor_y`) and classic (`margin_v`) styles synchronously.

## Task List

### Phase 1: Indicator Discoverability & Auto-On
- [ ] Task 1: Auto-enable dead space overlay & clarify button label (`index.html`, `app.js`, `components.css`)

### Phase 2: Calibrated 2026 Geometry & Collisions
- [ ] Task 2: Calibrate dead-space constants and collision thresholds (`app.js`, `components.css`, `tests/js/safe_zone_test.js`)

### Checkpoint: Indicator & Geometry Verification
- [ ] Safe-zone overlay opens automatically on portrait video.
- [ ] Overlay dimensions match 11.5% / 23.5% / 15.2%.
- [ ] All JS tests in `safe_zone_test.js` pass with zero failures.

### Phase 3: "Sweet Spot" Placement & Docs
- [ ] Task 3: Add one-click placement chips under POSITION slider (`index.html`, `app.js`, `components.css`)
- [ ] Task 4: Persistent Memory & Documentation update (`memory.md`)

### Checkpoint: Complete
- [ ] Full regression test suite (`pytest`) passes (332/332).
- [ ] `node safe_zone_test.js` passes.
- [ ] Working tree clean.

## Risks and Mitigations
| Risk | Impact | Mitigation |
|---|---|---|
| Auto-enabling overlay might distract users who want a clean preview | Low | Toggle button is prominently labeled `🛡️ SAFE ZONE` to toggle off anytime. |
| Position chips conflict with custom slider ranges on landscape/square videos | Med | Chips clamp safely within `stylePositionRange()`. |
| Existing JS test fixtures expect old 10%/25%/15% collision coordinates | Low | Updated test coordinates in `safe_zone_test.js` to match calibrated constants. |
