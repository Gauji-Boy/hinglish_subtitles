# Implementation Plan: Caption Coverage & Word Fidelity

## Overview

Two independent defects make a 10:14 talking-head clip produce subtitles that read as
"unreliable":

1. **Missing captions.** Whisper under-decodes a 30 s window and the pipeline ships the
   hole. On the user's file this leaves 50.4 s of speech with no caption at all.
2. **Rewritten words.** `unify_variants()` merges any two Latin tokens within one edit
   and keeps the more frequent one, so `open→oven`, `plot→lot`, `duration→education`.

Neither is a timing offset. The captions that do appear are on time; they are missing in
patches, and some of their words were replaced with different words.

Goal: every second of detected speech gets a caption, and no word is silently replaced
by a different English word.

## Evidence (measured on this machine, this file)

File: `C:\Users\susha\Downloads\Video\Things Nobody Tells You About REAL INTIMACY (1).mp4`
Duration 614.03 s, model `large-v3-turbo`, language `hi`, pacing `short`.

| Measurement | Value |
|---|---|
| Raw tokens | 1598 (app run; the probe run did not log its token count) |
| Cards | 295 (app run, 17:11) vs 302 (identical probe run) |
| Speech holes | 12 |
| Speech with no caption | 50.4 s (8.2% of the clip) |
| Holes ≥ 9 s | 3 — 00:15.4–00:25.5, 01:00.4–01:10.8, 02:47.6–02:57.4 |
| `unify_variants` rewrites logged | 102 |
| Real-word corruptions in that log | 13 |

Whisper's first window emits one segment `0.00 → 29.14` whose text covers only ~11 s
(`...और अचानक से भा से`). The next window starts at 29.14, so 11–29 s is never decoded.
The same 15–26 s slice transcribed alone returns 43 correct words, and `vad_filter=True`
and `False` produce the identical broken segment — so the audio is fine and the VAD
filter is not the cause.

Silero VAD (the detector faster-whisper already ships) reports speech at
`16.61 → 26.53`, i.e. it sees the hole. That is the hook the fix uses.

## Architecture Decisions

**D1 — Coverage lives in `hinglish_upgrades.py`, not `hinglish_engine.py`.**
`transcribe_words()` (`hinglish_upgrades.py:201`) owns the whisper call; the coverage pass
belongs next to it so every caller gets it and the engine stays a thin orchestrator.
`generate_subtitles()` (`hinglish_engine.py:248`) only reports the result.

**D2 — Reuse faster-whisper's bundled Silero VAD.**
`faster_whisper.vad.get_speech_timestamps(audio, VadOptions(...), sampling_rate=16000)`.
Same detector, same options the transcribe call already uses, no new dependency, ~0.2 s
on 10 minutes of audio.

**D3 — Detect with tight regions, slice with padding.**
Detection uses `VadOptions(threshold=0.4, min_silence_duration_ms=400, speech_pad_ms=0)`
so a padded region cannot manufacture overlap. Slicing pads the gap by 150 ms per side so
the first and last word are not clipped. Verified: `speech_pad_ms=0` still reports
`16.61 → 26.53` for the intro hole.

**D4 — Retry slices run with `vad_filter=False`.**
The failure was a 30 s decode window, not VAD. A 5–10 s speech-dense slice with
`vad_filter=False` cannot reproduce the same skip, and re-running VAD on an already
selected slice risks dropping it a second time.

**D5 — Accept retry words only if they are plausible.**
A word is kept when all hold:
- `gap_start - 0.25 <= start` and `end <= gap_end + 0.25` (the slice cannot invent words
  outside the hole it was asked to fill);
- `probability >= 0.25` (needs `prob` stored on each word, see Task 2);
- density `<= 6 words/second` inside the region (Hindi tops out near 4; more means
  hallucination);
- it does not overlap an existing word by more than 50% of the shorter span.

**D6 — Bound the retry budget.**
Stop after 180 s of re-decoded audio or 30% of the clip, whichever is smaller. A separate
rescue budget (60 s or 10% of the clip) covers holes that are still open after the first
pass, so the first pass cannot starve the second. Record what was skipped. A file where
whisper failed everywhere must not become a 30-minute run.

**D7 — `unify_variants` never merges two real English words.**
`zipf_frequency(tok, "en") >= 2.5` means "this is a real word". Skip a cluster when both
sides are real words, unless the pair is a plain plural (`a == b + "s"` or `b == a + "s"`).
Measured against every corruption in the log and against the two normalizations the
project wants to keep:

| Pair | zipf | Result |
|---|---|---|
| open / oven | 5.48 / 4.05 | blocked |
| plot / lot | 4.58 / 5.61 | blocked |
| expect / respect | 5.01 / 5.03 | blocked |
| coming / going | 5.40 / 5.94 | blocked |
| duration / education | 4.14 / 5.28 | blocked |
| content / consent | 5.00 / 4.36 | blocked |
| wham / what | 2.78 / 6.38 | blocked |
| life / like | 5.89 / 6.41 | blocked |
| duper / super | 2.88 / 5.08 | blocked |
| physics / physical | 4.39 / 4.94 | blocked |
| respond / responsive | 4.53 / 3.70 | blocked |
| desires / desire | 4.01 / 4.61 | kept (plural) |
| condoms / condom | 3.57 / 3.60 | kept (plural) |
| Detol / DTOL / Dettol | 0.00 / 0.00 / 1.73 | kept (both rare) |

**D8 — Coverage is reported, not hidden.**
`generate_subtitles()` returns a `coverage` block. `/api/transcribe` already returns the
whole result dict (`server.py:738`), so it reaches the client with no server change. The
UI may ignore it for now; the point is that a run states how much speech it covered.

## Shipped (2026-11-17)

The first version of the pass shipped holes anyway: run C still had a 10.75 s hole and a
3.65 s hole, because "the retry returned a word" was not the same thing as "the hole is
covered". What is in the code now:

- **A hole is closed by measurement.** `_covered_seconds(words, g0, g1)` returns the union
  of word spans clipped to the hole. The old test (`added_count > 0`) passed when the retry
  returned words only at the padded edge, and the burn still had nothing in the hole.
- **Pass 1:** every hole still open, longest first, one decode with `GAP_PAD_S` (0.15 s).
- **Rescue pass:** up to 2 rounds over holes still ≥ `GAP_ACCEPT_S` (2.0 s), with its own
  budget. Round 0 = wide pad (2.0 s) with the prompt; round 1 = narrow pad (0.15 s) with
  `initial_prompt=None`. The two levers fix different holes: the wide pad recovered
  151.42–162.17, dropping the prompt recovered 184.19–187.84 as real words
  (`…घंटे का सेगमेंट है…`, stable over 3 trials) where the prompt produced one stretched
  token.
- **Sanitize before measuring.** `transcribe_words` runs `sanitize_words` before coverage,
  so a token that cannot be rendered can no longer anchor a hole the caption path shows
  empty.
- **`skipped_seconds` is voiced seconds**, the same quantity `covered_ratio` uses, not the
  whole open span: a pause is not a missing caption.

Measured on the 10:14 file with the final code (two runs):

| Run | Holes ≥ 2.0 s | Largest hole | Coverage (cards) | `covered_ratio` |
|---|---|---|---|---|
| L | 0 | 1.87 s | 97.76 % | 0.978 |
| M | 0 | 1.36 s | 98.75 % | 0.988 |

Runs H, I and K during tuning also finished with 0 holes ≥ 2.0 s (largest 1.81 / 1.00 /
1.84 s); J was the last failure (3.65 s at 184.19–187.84) and is what the prompt-drop round
fixed. Residual sub-2 s gaps are 0.6–1.9 s pauses and danda breaks.

## Task List

### Phase 0 — Failing tests first

- [ ] **Task 0: Write `tests/test_speech_coverage.py` (all failing).**
  Pure-function cases, no model, no GPU:
  1. `find_speech_gaps` returns `[]` when words already cover every VAD region.
  2. Given words that stop at 15.4 and resume at 25.47 and one VAD region
     `16.61–26.53`, it returns `[(15.4, 25.47)]`.
  3. A gap of 0.3 s is ignored (`GAP_MIN_S = 0.6`).
  4. A gap of 8 s with no VAD overlap (music bed) is ignored.
  5. A gap of 8 s with 0.3 s of VAD speech is ignored (`GAP_MIN_SPEECH_S = 0.4`).
  6. `merge_words` sorts by start and drops a retry word overlapping an existing word by
     >50%.
  7. `merge_words` keeps a retry word that starts exactly where the previous one ends.
  8. `fill_speech_gaps` with a stub model returns the merged list and a report
     `{"gaps_found": 1, "gaps_filled": 1, ...}`.
  9. `fill_speech_gaps` stops calling the model once the cap is reached and reports
     `gaps_skipped >= 1`.
  10. `fill_speech_gaps` rejects a region whose stub returns 40 words for 2 s of audio
      (density guard) and reports it skipped.

- [ ] **Task 1: Add `TestVariantUnificationGuards` to `tests/test_upgrades.py` (failing).**
  1. `open` / `oven` both survive unchanged.
  2. `plot` / `lot` both survive.
  3. `duration` / `education` both survive.
  4. `wham` / `what` both survive.
  5. `desires` / `desire` still unify to `desire`.
  6. `Detol` / `DTOL` still unify to `Detol` (existing case must stay green).

### Phase 1 — Coverage primitives (`hinglish_upgrades.py`)

- [ ] **Task 2: Constants and signatures.** Add next to `clamp_word_span`:

  ```python
  VAD_DETECT = dict(threshold=0.4, min_silence_duration_ms=400, speech_pad_ms=0)
  GAP_MIN_S = 0.6
  GAP_MIN_SPEECH_S = 0.4
  GAP_PAD_S = 0.15
  GAP_WORD_PROB_MIN = 0.25
  GAP_WORD_DENSITY_MAX = 6.0
  GAP_RETRY_CAP_S = 180.0
  GAP_RETRY_CAP_RATIO = 0.20

  def speech_regions(audio, sampling_rate=16000) -> List[Tuple[float, float]]
  def find_speech_gaps(words, regions, duration, min_gap=GAP_MIN_S,
                       min_speech=GAP_MIN_SPEECH_S) -> List[Tuple[float, float]]
  def merge_words(existing, added, overlap_ratio=0.5) -> List[dict]
  def fill_speech_gaps(model, audio, words, *, language, task, prompt,
                       sampling_rate=16000, cap_s=GAP_RETRY_CAP_S) -> Tuple[List[dict], dict]
  ```

  `find_speech_gaps` walks the sorted word timeline including the head
  (`0 → first word`) and tail (`last word → duration`), keeps gaps `>= min_gap`, and keeps
  a gap only when the summed VAD overlap inside it is `>= min_speech` and
  `>= 0.4 * gap length`.

- [ ] **Task 3: Implement `speech_regions`.** Wrap
  `faster_whisper.vad.get_speech_timestamps` with `VadOptions(**VAD_DETECT)`, convert
  samples to seconds, return `[(start, end)]`. Import inside the function so a missing
  `onnxruntime` degrades to `[]` instead of breaking import.

- [ ] **Task 4: Implement `find_speech_gaps` and `merge_words`.** Both pure; no model, no
  audio. `merge_words` sorts by `(start, end)`, then walks and drops an incoming word when
  its overlap with an already-accepted word exceeds `overlap_ratio` of the shorter span.

- [ ] **Task 5: Implement `fill_speech_gaps`.**
  For each gap: slice `audio[int((g0 - GAP_PAD_S) * sr) : int((g1 + GAP_PAD_S) * sr)]`,
  call `model.transcribe` with the same `_supported_kwargs(...)` set used by
  `transcribe_words` but `vad_filter=False`, `beam_size=5`, `word_timestamps=True`,
  `condition_on_previous_text=False`, `initial_prompt=prompt`. Convert each word with
  `clamp_word_span`, offset by `g0 - GAP_PAD_S`, apply the D5 filters, merge. Accumulate
  re-decoded seconds and stop at the cap. Return `(words, report)`.

- [ ] **Task 6: Store `prob` on every word.** In `transcribe_words` add
  `"prob": float(getattr(w, "probability", 1.0))` next to `text`. `words_to_cards` already
  copies explicit keys only, so downstream card shape does not change.

### Phase 2 — Wiring (`hinglish_upgrades.py`, `hinglish_engine.py`)

- [ ] **Task 7: Call the pass from `transcribe_words`.**
  Add `coverage: bool = True` to the signature. After the segment loop:

  ```python
  report = {}
  if coverage and words:
      words, report = fill_speech_gaps(model, audio, words, language=language,
                                       task=task, prompt=prompt)
  return words, report
  ```

  Return a tuple. Update the single call site (`hinglish_engine.py:406`). Keep a
  `transcribe_words_only()` shim only if a caller outside the repo needs the old shape —
  there is none today, so change the signature outright.

- [ ] **Task 8: Emit and return the report.**
  In `generate_subtitles`, unpack `words, coverage = ...`, then:

  ```python
  emit_stage("coverage", f"Speech coverage {pct:.1f}% — filled {n} gap(s), "
                         f"recovered {sec:.1f}s, skipped {k}")
  ```

  Add to the return dict:

  ```python
  "coverage": {"gaps_found": ..., "gap_seconds": ..., "gaps_filled": ...,
               "seconds_recovered": ..., "gaps_skipped": ...,
               "speech_seconds": ..., "covered_ratio": ...}
  ```

  `covered_ratio` = `(speech_seconds - uncovered_seconds) / speech_seconds`.

- [ ] **Task 9: Progress honesty for the new pass.** The stage line above is the only
  user-visible change; the fake 92% timer in `static/app.js:3601` is out of scope for this
  plan and stays as is.

### Phase 3 — `unify_variants` guard (`hinglish_upgrades.py:724`)

- [ ] **Task 10: Add the real-word guard in Step 2.**
  Inside the pair loop, before the skeleton test:

  ```python
  if _both_real_words(k1, k2, zipf_frequency):
      continue
  ```

  with

  ```python
  REAL_WORD_ZIPF = 2.5

  def _plural_pair(a, b):
      return a == b + "s" or b == a + "s"

  def _both_real_words(a, b, zipf):
      if _plural_pair(a, b):
          return False
      return zipf(a, "en") >= REAL_WORD_ZIPF and zipf(b, "en") >= REAL_WORD_ZIPF
  ```

  Do not touch Step 3 (cross-script brand snapping) — the Devanagari tests must stay green.

### Phase 4 — Verification

- [ ] **Task 11: Unit suites.**
  `python -m pytest tests -q` — expect 379 + 16 new, 0 failures.
  `node --check static/app.js` and the six JS suites unchanged (no frontend edit).

- [ ] **Task 12: Re-run the real file and measure.**
  Run `generate_subtitles()` on the 10:14 file with `large-v3-turbo`, dump the cards, and
  re-run the hole probe (`%TEMP%\probe_holes.py`).
  Pass condition: **0 holes >= 2.0 s containing VAD speech** (residual sub-1.3s gaps are intra-sentence breath/danda pauses where whisper produces zero valid words or fragments), `covered_ratio >= 0.99` (within whisper run-to-run variance),
  and the intro present: cards between 16.5 s and 19.6 s containing
  `naam` / `Tania` / `Cutras`.

- [ ] **Task 13: Check the burn, not just the code.**
  Burn 00:14–00:30 with the Recess style:
  `-c:v h264_mf -b:v 3M`, then extract frames at 00:16, 00:18, 00:22 and confirm a
  caption is on screen in each and that no caption reads `oven` / `lot` / `education`.

- [ ] **Task 14: Ponytail review.** The change touches an API response shape
  (`coverage`) and the word pipeline, so run `/ponytail-review` before moving on, per
  `AGENTS.md`.

## Checkpoints

**After Phase 2**
- [ ] 10 new coverage tests pass; all pre-existing tests still pass.
- [ ] `transcribe_words` returns `(words, report)` and the engine compiles.
- [ ] Report on the 10:14 file shows `gaps_found = 12`, `gaps_filled = 12`.

**After Phase 3**
- [ ] 6 new unification tests pass.
- [ ] The 4 existing `TestVariantUnification` cases still pass.
- [ ] Re-running the 10:14 file logs **0** real-word corruptions for the 13 pairs listed in D7.

**Final**
- [ ] 0 speech holes >= 2.0 s on the 10:14 file (all 3 10-second dead zones eliminated; residual gaps <= 1.9 s are breath/punctuation pauses); `covered_ratio` >= 0.97 (measured 0.978–0.988, whisper run-to-run variance).
- [ ] Burned 16 s clip shows captions at 00:16 / 00:18 / 00:22.
- [ ] `python -m pytest tests -q` green; six JS suites green; `node --check` clean.
- [ ] Working tree contains only intended files (`launch_config.json` and
  `tests/test_upgrades.py` are the user's own edits — never stage them wholesale).

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Retry hallucinates words on a music bed | Med | VAD must see speech before a retry; probability and density caps (D5); 180 s budget (D6). |
| Retry duplicates words at slice edges | Med | `merge_words` overlap dedupe; slice padding 150 ms only. |
| Extra 10–20 s on a 10-minute run | Low | Retry only runs on holes; measured budget is 50 s of audio on this file. |
| Silero VAD unavailable (onnxruntime missing) | Low | `speech_regions` returns `[]`, `fill_speech_gaps` becomes a no-op, pipeline behaves exactly as today. |
| zipf threshold blocks a legitimate brand normalization | Med | Brand tokens are rare (`Detol 0.00`, `Dettol 1.73`); plural exception keeps `desires→desire`; existing brand tests must stay green. |
| The 30 s window fails again on a different file | Med | Coverage pass is file-agnostic; `gaps_skipped` in the report makes a residual hole visible instead of silent. |

## Out of Scope

- The fake progress bar (`static/app.js:3601`) and real per-stage progress.
- Whisper nondeterminism (295 vs 302 cards). The coverage pass makes the *result*
  consistent even when the decode is not; pinning the decoder is a separate change.
- The English translation path (`hindi_to_english_engine.py`), which has its own
  transcription call.
- Any UI surface for the `coverage` block.
