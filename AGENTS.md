# hinglish_subtitles

Local FastAPI + browser app for burned-in Hinglish subtitles. One user, one machine:
judge performance and concurrency against a single local user, not a server fleet.

## Ponytail triggers

- Run `/ponytail-review` after the change passes its tests, before moving on, when it
  touches: `karaoke_ass.py`, `preview_renderer.py`, overlay geometry in
  `static/app.js`, the caption clock, an API response shape, a new cache or
  invalidation, or anything that writes `launch_config.json`.
- Skip it for deletions, docs, `tasks/`, and single constants. A 40-line delete does
  not need a pass over every caller.
- Normal mode (no ponytail) for calibration work: preset geometry, typography,
  `_KINETIC_ASS_FONT_SCALE`, pill metrics, anchor offsets. The target there is
  "matches the reference within 3 px", not "smallest diff".

## Check the burn, not just the code

After touching `karaoke_ass.py`, `preview_renderer.py` or the caption overlay, render
one preview frame and burn one real clip. The defects this project actually shipped
(frozen overlay, `\k` chain running 340 ms early, preview and burn disagreeing) were
invisible in the source and in unit tests.

## Commands

- Python: `python -m pytest tests -q`
- Browser side: `node tests/js/caption_clock_test.js`, `node tests/js/caption_sync_test.js`,
  `node tests/js/recess_overlay_test.js <resolved-style.json>`; syntax check with
  `node --check static/app.js`
- Burn: this machine has no `libx264`; use `-c:v h264_mf -b:v 3M`
- PowerShell: a pipeline ending in `Select-Object -First N` reports exit code 1
  falsely. Redirect to a file and check `$LASTEXITCODE` instead.
- Timing evidence: `python tools/measure_timing.py` (read-only)
