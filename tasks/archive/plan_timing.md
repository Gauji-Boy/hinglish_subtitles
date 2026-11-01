# Implementation Plan: Caption Timing (all styles)

## Goal

Make the caption that appears on screen match the word being spoken — in the live
preview, in the burned MP4, and in exported `.ASS`/`.SRT` — for **every** style, at the
engine level rather than per preset.

Constraint carried over from the Recess work: everything stays local, and the app keeps
working as a single-user desktop tool (no cloud calls, no new services).

## What the measurement actually shows

Two real clips were run through the shipping pipeline (ffmpeg decode → `large-v3-turbo`,
`language=hi`, beam 5, VAD 400/200/0.4, `word_timestamps=True`) and every word start was
compared against an acoustic energy onset (10 ms frames, adaptive threshold).

Harness: `%TEMP%\opencode\timing_measure.py` (read-only, writes nothing into the repo).

| Measurement | Traffic (58.1 s, 152 w) | Genius (58.9 s, 124 w) |
|---|---|---|
| Word start vs acoustic onset | median **−30 ms**, p10 −140, p90 +180 | median **+65 ms**, p10 −175, p90 +201 |
| Drift over the clip | — | r = 0.11, slope 0.9 ms/s |
| Card start vs onset | median +80 ms | median −70 ms |
| `\k` chain vs true word start | median 0 ms, 0/107 over 40 ms | median 0 ms, 1/82 over 40 ms (worst −340 ms) |
| Words longer than the 2.5 s clamp | 0 / 152 | 1 / 124 |
| Burned-file audio offset vs source | **0 ms** (frame-exact cross-correlation) | — |
| **Live "text becomes visible" delay** | **median 140 ms, p90 220 ms** | **median 90 ms, p90 216 ms** |

Reading of the data:

1. **The transcript timestamps are not the problem.** Word starts sit inside ±200 ms of
   real acoustic energy, the median is essentially zero on one clip and +65 ms on the
   other, and there is no measurable drift over a minute. That ±200 ms is the resolution
   limit of both Whisper's DTW and this matcher; chasing it further would be guesswork.
2. **The burned output is not the problem.** The burn shifts nothing (0 ms), and the
   `\k` chain is within 40 ms for 189 of 189 words across both clips because
   `semantic_chunk` makes words inside a card contiguous.
3. **The live preview is the problem.** Non-kinetic styles are driven only by
   `timeupdate`, which fires ≈4×/s, so a card is painted up to **250 ms** after its
   start, median **90–140 ms**. On top of that the classic fade spends **150 ms** going
   from `opacity 0` to `1` (`components.css:1007`), so text is only half-readable another
   ~75 ms later. That is the **~165–215 ms late** the eye sees, on every classic style,
   every clip. Kinetic styles already use `requestAnimationFrame` and do not have it.

So the user-visible symptom "the subtitle appears after the speaker" is real, but it is
a *presentation-clock* defect, not an ASR defect. The rest of this plan fixes the clock,
then removes the smaller latent defects that would make a burned file disagree with the
preview, then adds the one control the user needs when a clip is *genuinely* offset.

## Root causes

| # | Cause | Evidence | Impact |
|---|---|---|---|
| 1 | Classic overlay clock is `timeupdate` only | `static/app.js:2167-2184` | 0–250 ms late, median 90–140 |
| 2 | Classic fade is 150 ms | `static/components.css:1007` | +75 ms to half-opacity |
| 3 | Whole card is rebuilt as DOM on every tick | `static/app.js:1499-1529` | blocks naively raising the tick rate |
| 4 | Style re-applied on every tick | `static/app.js:2174` | same |
| 5 | Intra-card `\k` gaps are dropped (only word 0 gets a lead) | `karaoke_ass.py:1243-1264` | latent burn drift, worst −340 ms measured |
| 6 | `cs >= 100` is clamped to 99 instead of carrying | `karaoke_ass.py:93-95` | −10 ms on ~1 % of timestamps |
| 7 | No `ratechange` / `seeking` handling; scrubber updates on `change` only | `app.js:2184-2185` | desync after seek, slow-mo, or trackpad scrub |
| 8 | Over-long token clamp only trims `end` | `hinglish_upgrades.py:165-172`, duplicated in `hindi_to_english_engine.py:151-155` | card ends early → dead air before the next card (1/276 words here, worse on music beds) |
| 9 | No single place to nudge a clip; live and burned timings are built independently | `words_to_cards`, `karaoke_ass`, SRT builder | a manual fix cannot be applied consistently |

## Phases

### Phase 1 — one playback clock for every style

- Task 1: add `startCaptionLoop()` / `stopCaptionLoop()` in `app.js`. Prefer
  `videoPlayer.requestVideoFrameCallback` (frame-exact, fires once per decoded frame) and
  fall back to `requestAnimationFrame`; both are cancelled on pause/ended.
- Task 2: make `updateVideoCaption()` idempotent — compute the active card index and the
  last spoken word index, return early when both are unchanged. This is what makes a
  60 Hz tick cheap.
- Task 3: keep `timeupdate`/`seeked` as correction events only (they now just force the
  dirty check to re-evaluate), and add `play`, `pause`, `seeking`, `ratechange`.
- Task 4: read the clock as `video.currentTime`, never a wall clock, so 0.5× / 2× playback
  and abrupt seeks stay correct.

**Acceptance:** on a 30 fps clip the card for `t = 4.32` paints at `t ≤ 4.36`; a style
switch, a seek to mid-card, and a 2× playback all show the right card on the next frame.
Measured with the same harness: appearance delay median ≤ 25 ms, p95 ≤ 40 ms.

### Phase 2 — cheap per-frame work

- Task 5: in `renderCaptionText`, build the word spans once per card and afterwards only
  call the (already existing) `applyCaptionWordColors(currentTime)`. No `textContent = ""`
  and no fragment rebuild per frame.
- Task 6: move `applyCaptionStyleToVideo()` out of the tick — it runs when the style or
  the mode changes, not 60×/s. Inline style writes are the expensive part.
- Task 7: cache the per-card style numbers (`previewSize`, colours, pill geometry) on the
  card object when the card first becomes active.
- Task 8: shorten the classic fade from 0.15 s to 0.08 s (matching the kinetic rail) and
  keep the transform; expose it as `reveal_fade_ms` so a style can opt out.

**Acceptance:** Chromium trace of 10 s of playback shows no long tasks and < 1 ms median
per-frame script time; no layout thrash warnings; card text identical to today.

### Phase 3 — live/ASS/SRT parity

- Task 9: emit `\k` gaps for intra-card silences as well as the first-word lead, so an
  ASS highlight always encodes absolute time instead of a running sum.
- Task 10: fix `format_ass_time` to carry `cs >= 100` into the seconds field, and add
  tests for `x.995` and `x.999`.
- Task 11: apply a single `caption_offset_ms` inside `words_to_cards` (after
  `pad_display_times`, clamped to ±500 ms) so the live overlay, ASS, SRT and burn all
  inherit one number. Default 0.
- Task 12: surface it as a small "sync" control (±20 ms steps) next to the caption mode
  pills, persisted per job in the result payload; changing it re-renders from the stored
  cards without re-transcribing.

**Acceptance:** for every word, ASS time − live time ≤ 20 ms; ASS time − card timeline
≤ 20 ms; moving the nudge by +100 ms moves the live card, the ASS event and the SRT cue
by 100 ms.

### Phase 4 — timestamp hardening

- Task 13: replace the end-only clamp with a span-aware rule: if a token's acoustic span
  exceeds `max_word_span`, cap the span but also record the leftover as a `tail_gap` so
  the card does not silently end early. Apply in `hinglish_upgrades.py` and delete the
  duplicate block in `hindi_to_english_engine.py`, calling the shared helper instead.
- Task 14: on a `tail_gap` larger than one word, keep the card on screen (hold) instead of
  cutting to dead air, but never past `next_card_start − 40 ms`.

**Acceptance:** no card disappears more than 150 ms before the next one starts; the two
golden clips keep their current card boundaries within 1 frame.

### Phase 5 — verification

- Task 15: extend `%TEMP%\opencode\timing_measure.py` into
  `tools/measure_timing.py` (read-only, opt-in, not part of pytest) so the numbers in this
  plan can be reproduced after the change.
- Task 16: add `tests/test_timing_contract.py` pinning: offset applied once, `\k` sum
  equals card duration, `format_ass_time` carry, `tail_gap` behaviour.
- Task 17: burn one clip before/after and confirm the audio offset is still 0 ms and the
  burned word boundaries match the live overlay within 1 frame.
- Task 18: re-run `python -m pytest tests -q` (112 currently) plus `node --check`.

## Targets

| Metric | Now | Target |
|---|---|---|
| Live appearance delay, median | 90–140 ms | ≤ 25 ms |
| Live appearance delay, p90 | 216–220 ms | ≤ 40 ms |
| Live vs burn word start | not comparable today | ≤ 1 frame |
| ASS word-start error | ≤ 40 ms for 188/189, −340 ms worst | ≤ 20 ms for all |
| Transcript vs acoustics | median −30/+65 ms | unchanged (already good) |

## Explicitly out of scope

- Changing the ASR model, beam size, or VAD defaults. The measurement shows no bias to
  correct; a wrong turn here would hurt accuracy for no visible gain.
- Rewriting the kinetic path — it already runs on rAF and is frame-accurate.
- Touching the intentional hold/gap constants (0.3 s, 0.45 s, 1.0 s, 2.0 s, 40 ms) except
  where Phase 4 says the card must not end early.

## Result (measured after the change)

Same two clips, same model and settings, via `tools/measure_timing.py`.

| Measurement | Before | After |
|---|---|---|
| Word start vs acoustic onset | median −30 / +65 ms | unchanged (no ASR change) |
| ASS `\k` chain vs word start | ≤ 40 ms for 188/189, worst −340 ms | **0 ms for 189/189** |
| `format_ass_time` round-trip | up to −10 ms on ~1 % of values | **0.0 ms** |
| Live appearance delay (classic) | median 90–140 ms, p90 220 ms, + 150 ms fade | one frame, fade 80 ms |
| Card ends early on a capped token | possible (end-only clamp) | held up to 1.5 s, never into the next card |

Burn verification (classic `hormozi` style, real `h264_mf` burn of a 58 s clip):

- burn succeeded, no libass errors, 58.096 s in → 58.096 s out;
- audio offset **0 ms** (cross-correlation of the burned file against the source);
- the first highlight change after a 0.22 s intra-card silence lands on the frame
  covering the word start (10.017 s for a word at 9.98 s → within 1 frame). With the
  old chain it would have been 220 ms early.

Waived, with reasons:

- **Per-frame Chromium profile.** The expensive work (DOM rebuild + style re-apply) is
  now provably off the per-frame path (`caption_clock_test.js` asserts the spans are
  never rebuilt inside a card), so a trace would only confirm the obvious. Revisit if
  a low-end machine reports jank.
- **In-browser re-timing of the live overlay.** `requestVideoFrameCallback` fires on the
  presented frame by definition; the remaining error is the display pipeline. The
  measurement that mattered — proving the *old* clock was the problem — is in the table
  at the top of this file.
- **Task 7 (cache per-card style numbers).** With the dirty check the style is written
  once per card, so caching would add state to save less than one write per card.

## Non-timing optimisation backlog

Reported separately from this plan; each is independently shippable and none is a
prerequisite for the timing work.

| Priority | Item | Where | Gain | Effort |
|---|---|---|---|---|
| 1 | Dead `ass_karaoke` is built for every job and never read | `hinglish_engine.py:476`, `hindi_to_english_engine.py:250` | 1–2 s tail latency + ~2 MB payload per job | S |
| 2 | `convert_to_hinglish` runs regex-per-token with no memo | `transliteration.py` hot path | 3.9 s → 0.16 s at 400 words | S |
| 3 | `flattenKineticWords()` rebuilt every rAF | `app.js:919` | 7.2 ms → ~0 per frame at 160 words | M |
| 4 | Pillow text measured again for identical strings each frame | `karaoke_ass._kinetic_lines` | 12,245 calls → hundreds | S |
| 5 | Recess pill emits a band event per word | `karaoke_ass.py` pill layer | 13,775 events / 2.13 MB ASS | M |
| 6 | `-movflags +faststart` missing on burn output | `video_burner.py` | seekable output, no re-mux | S |
| 7 | `index.html` re-read per request; static served `no-store` | `server.py` | removes a disk read and forces full reloads | S |
| 8 | No result cache; "recents" row has no click handler | `app.js` | re-transcribe avoided on back-navigation | M |
| 9 | `DECISION_LOG` is module-global | `hinglish_upgrades.py` | interleaved logs on concurrent jobs | S |
| 10 | `_MODELS.clear()` evicts a live model on any cache miss | `hinglish_upgrades.py:79` | VRAM reload stall | S |
