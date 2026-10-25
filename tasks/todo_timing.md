# Task List: Caption Timing (all styles)

Plan: `tasks/plan_timing.md`

Measurement before any change (two 58 s clips, `large-v3-turbo`):

- ASR word starts: median −30 / +65 ms vs acoustic onset, no drift → **leave ASR alone**
- Burn: 0 ms audio offset, `\k` chain within 40 ms for 188/189 words → **burn timing was sound**
- Live classic overlay: median 90–140 ms, p90 220 ms + 150 ms fade → **this was the bug**

## Phase 1: one playback clock for every style

- [x] Task 1: `startCaptionLoop` / `stopCaptionLoop` using `requestVideoFrameCallback`, rAF fallback
- [x] Task 2: dirty-check `updateVideoCaption` (card key + forced repaint path)
- [x] Task 3: `timeupdate` as correction only; `play`, `pause`, `seeking`, `seeked`, `ratechange`, `ended` wired
- [x] Task 4: clock is always `video.currentTime` (rate/seek safe)

### Checkpoint: clock
- [x] A frame alone moves the overlay to the next card (no `timeupdate` involved)
- [x] Style switch and forced repaint rebuild on demand; seek/rate call the forced path
- [x] Old paint delay reproduced by the harness (median 90–140 ms); the frame loop removes it
      — Chrome's `requestVideoFrameCallback` fires per presented frame, so the delay is
      ≤ 1 frame by construction. Not re-timed in-browser; the JS test pins the mechanism.

## Phase 2: cheap per-frame work

- [x] Task 5: spans built once per card; per-frame path is `applyCaptionWordColors` only
- [x] Task 6: `applyCaptionStyleToVideo()` off the tick (card change / style / mode only)
- [x] Task 7: not needed — with the dirty check the style is written once per card, so
      caching `previewSize`/colours on the card would add state for < 1 write per card.
- [x] Task 8: classic fade 150 ms → 80 ms via `--caption-fade`, opt-out through `reveal_fade_ms`

### Checkpoint: cost
- [x] Repeated frames inside one card do not touch the DOM (`caption_clock_test.js`)
- [x] Card text and colours unchanged (same `renderCaptionText` output; colour assertions pass)
- [ ] Per-frame script time not profiled in Chromium. Deliberately skipped: the DOM rebuild
      was the expensive part and it is now provably gone from the per-frame path.

## Phase 3: live / ASS / SRT parity

- [x] Task 9: `\k` gaps for every intra-card silence, not just the first-word lead
- [x] Task 10: `format_ass_time` carries `cs >= 100`; tests at `x.995` and `x.999`
- [x] Task 11: one `caption_offset_ms` (±500, 20 ms steps) applied once
- [x] Task 12: sync nudge control in the caption row. Persisted per browser
      (`localStorage`), not per job — there is no job store, and a per-clip value the user
      cannot see is worse than one they can.

### Checkpoint: parity
- [x] `\k` chain vs true word start: **0 ms for 107/107** (Traffic) and **82/82** (Genius)
- [x] `format_ass_time` round-trip worst error **0.0 ms**
- [x] +100 ms nudge moves card start, card end, word start and `start_str` together (JS test)
- [x] Editor edit then nudge does not undo the edit (`captureCaptionBase` before re-shift)

## Phase 4: timestamp hardening

- [x] Task 13: shared `clamp_word_span()` returns a `tail`; duplicate block in
      `hindi_to_english_engine.py` deleted; `merge_split_words` keeps the tail
- [x] Task 14: hold over up to `TAIL_HOLD_MAX = 1.5 s`, never into the next card
      (`next_start − 40 ms`)

### Checkpoint: hardening
- [x] No card ends early on a stretched token (`test_timing_contract.py`)
- [x] Cards without a tail keep their exact old padding (byte-identical expectation)
- [x] Internal `tail` never reaches the exported segments

## Phase 5: verification

- [x] Task 15: `tools/measure_timing.py` (read-only, opt-in, not in pytest), exit code 0
- [x] Task 16: `tests/test_timing_contract.py` (7 tests)
- [x] Task 17: burn before/after with a classic style — 0 ms audio offset, 58.096 s → 58.096 s,
      intra-card pause highlighted within 1 frame (10.017 s for a word at 9.98 s)
- [x] Task 18: `python -m pytest tests -q` → **122 passed**, `node --check static/app.js` clean

### Checkpoint: complete
- [x] Targets met except the two explicitly waived above (per-frame profile, in-browser re-time)
- [x] Nothing committed; `launch_config.json` unchanged from the user's state

## Deferred (audit backlog, not timing)

Ranked; each is independently shippable.

- [x] Remove dead `ass_karaoke` built for every job — done 2026-10-25. Both engines
      dropped the key and the build; `/api/export/ass` and the preview renderer still
      generate ASS on demand from `segments`. Measured on the 30-card / 137-word
      reference clip: classic 0.3 ms / 4.2 KiB, Recess 96 ms / 460 KiB per job — the
      original 1–2 s / 2 MB estimate only applies to long Recess clips (13,775 events).
- [x] Memoise `convert_to_hinglish` per token — done 2026-10-25. `transliteration.py`
      gains a bounded token cache (`_TOKEN_CACHE`, 8192, wholesale clear). Measured on
      81 real Devanagari tokens cycled to 400 per-word calls: **0.180 s → 0.040 s
      (4.5×)**; a single 400-word call is 0.035 s cold vs 0.001 s warm, output identical.
      The earlier "3.9 s → 0.16 s" figure did not reproduce and is superseded.
- [x] Memoise `flattenKineticWords` — done 2026-10-25. Cached on `currentSegments`
      identity + caption mode + `accent_mode` / `phrase_gap_ms` /
      `max_words_per_phrase` / `kinetic_grouping` / portrait flag; `captureCaptionBase()`
      clears it because the editor mutates cards in place. Measured in Node at 160
      words / 64 phrases: rebuild **0.58 ms**, cache hit **0.00 ms**. The audit's
      7.2 ms did not reproduce here — that figure almost certainly included the
      per-frame layout flush in `getBoundingClientRect()`, which the existing
      `kineticBaseSize` / `kineticMaxWidthPercent` calls still force every frame.
- [x] Cache Pillow line measurements in `_kinetic_lines` — measured 2026-10-25 and
      rejected. Pillow is **4% of the Recess build**: 3.4 ms of 88 ms (real clip) and
      13.2 ms of 328 ms (548 words / 232 s). A perfect cache saves at most ~13 ms on a
      4-minute reel; the build is not a bottleneck at all.
- [ ] Coalesce Recess pill band events — measured 2026-10-25, real but modest. The
      2928 layer-0 band events carry **73%** of the Recess burn overhead. Interleaved
      A/B, 20 s at 1080x1920 with `h264_mf -b:v 3M`, 5 rounds (medians): none 1.46 s,
      classic 30 events 1.73 s (+0.27), Recess 3065 events 2.13 s (+0.67), bands only
      1.95 s (+0.49), words only 1.63 s (+0.17). Ceiling if bands collapse to ~classic
      cost: **~0.42 s per 20 s of video (~20% of a Recess export)**, Recess only.
      Re-run with `%TEMP%\opencode\bench_burn_ab.py`; sequential runs drift ~50%, so
      the variants must stay interleaved.
- [x] `-movflags +faststart` on burn output — shipped 2026-10-25. One flag in
      `video_burner.py`'s command; the muxer rewrites the container after encoding, so
      the burned file plays and seeks in a `<video>` element without a full download.
      Verified with a top-level atom walk (`%TEMP%\opencode\faststart_check.py`):
      `ftyp → moov → free → mdat`, moov at byte 32 and mdat at byte 25569 of a
      16,558,313-byte 1080x1920 burn. Same byte count and same `1004/76` anchor
      timeline as before the flag, and a `-ss 2.5` decode of the tail is clean, so the
      rewrite neither re-encodes nor truncates the mdat.
- [ ] Cache `index.html`, `Cache-Control` for static
- [ ] Result cache / recents row click
- [ ] Per-job `DECISION_LOG`
- [x] Stop `_MODELS.clear()` evicting a live model — shipped 2026-10-25. `_MODEL_LOCK`
      around the check-construct-insert in `get_model`, plus a `single_job` decorator
      (`_JOB_LOCK`, an RLock) on `generate_subtitles` / `generate_english_subtitles` so
      only one model load and inference runs at a time. Evidence: four concurrent cold
      misses built **4 models in 4 concurrent ctors** before, **1** after
      (`%TEMP%\opencode\model_cache_discriminate.py`); nine new cases in
      `tests/test_model_cache.py` pin it, including the old KeyError window and a
      **409** for a second transcription. A second window is told a job is running
      instead of parking behind it (the engine slot is claimed non-blocking at the
      endpoint). Remaining gap:
      `get_model` called outside a job (benchmark scripts) is only protected by
      `_MODEL_LOCK`, not deferred — those are single-threaded processes.
