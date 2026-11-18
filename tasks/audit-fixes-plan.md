# Implementation Plan: Audit Fixes (Word Timeline, Karaoke Chain, Card Cutoffs, Tail Holes)

Status: implemented and verified on real clips. Structural acceptance passes;
the "0 visible holes in every run" gate does not pass on the Samay clip.
Scope: the defects found in the four-clip audit (2026-11-18). The hotword guard is
already implemented and uncommitted; it is not part of this plan.

## Overview

The audit found four independent defects. None of them is a transcript-timing offset:
word starts match acoustic onsets (median 0 to +20 ms, drift ~0 ms/s). The failures are
in the data hygiene between decode and burn, and in what the coverage pass measures.

1. **Zero-length words survive the first decode.** 99 of 1593 words on the Samay clip
   have `start == end`, 31 duplicate spans. The retry path filters spans < 0.05 s; the
   first decode does not. These tokens carry real text ("to shoot for", "mein samay ke
   vlog mein") but no time.
2. **Overlapping words bend the karaoke clock.** 75 highlights land > 20 ms late, up to
   1850 ms. Every one traces to a word whose predecessor ends after it starts (the 150 ms
   retry pad). `\k` is a running sum and `cur_t` moves backwards, so the error is added to
   every later word in the card.
3. **`pad_display_times` cuts speech.** The `max_dur` cap is applied after the card's own
   word span, so a card can end before its last word does. 235 of 365 cards do; 16 by
   > 100 ms, worst 1210 ms.
4. **The visible tail can vanish.** Samay run one ended its cards at 855.06 s while the
   word timeline reported no hole there; the last 8.95 s of the clip had speech and no
   card. The coverage pass measures words, the viewer sees cards.

Plus one unproven observation (VAD over-detection in music) and one fact of life
(Whisper on this GPU is not deterministic: 90.62% vs 96.98% on the same file).

Goal: every word has a positive span, every highlight lands on its word, no card ends
before its last word, every word appears in some card, and acceptance is measured on the
card timeline across repeat runs.

## Evidence (measured on this machine, 2026-11-18)

| Measurement | Run 1 | Run 2 |
|---|---|---|
| Samay coverage | 90.62% | 96.98% |
| Samay words / cards | 1383 / 328 | 1593 / 365 |
| Samay word holes >= 2 s | 9 (max 3.96 s) | 0 |
| Samay card holes >= 2 s | 3 (max 8.95 s) | 0 |
| Samay zero-span words | not saved | 99 / 1593 (median prob 0.36) |
| Samay duplicate spans | not saved | 31 |
| Samay `\k` outliers > 20 ms | 31 | 75 (max 1850 ms) |
| Samay cards ending before last word | not saved | 235 (16 > 100 ms, max 1210 ms) |
| AUKAAT coverage / holes | 99.85% / 0 | 99.85% / 0 |
| DualSense coverage / holes | 100% / 0 | 98.32% / 0 |
| Announcement coverage / holes | 98.17% / 1 word hole, 0 card holes | 99.30% / 0 |

Repeat runs move coverage 1.7-2.3 points on clean clips without creating visible holes.
The useful gate is card holes, not the ratio.

## Architecture Decisions

**D1 - Normalize the word timeline once, at the source.**
New `normalize_word_timeline(words, duration=None)` in `hinglish_upgrades.py`, called at
the end of `_decode_words`, at the end of `fill_speech_gaps`, and at the top of
`words_to_cards`. Every later stage gets sorted, positive-span, non-overlapping words.
One function, three call sites, one contract.

**D2 - Repair zero-span runs, do not drop them.**
The text is usually real: `to shoot for`, `mein samay ke vlog mein`. For each maximal run
of zero-span words at time `t`, distribute `[max(prev_end, t - 2.0), next_start or t + 1.0]`
across the run, proportional to text length, minimum 0.02 s each. Cap the total stretch at
1.5 s so a hallucinated cluster cannot paint a long pause. Drop a zero-span token only
when `prob <= 0.05` (e.g. `parole` at 0.00) or its text is punctuation-only.

**D3 - Trim the earlier word on overlap.**
The later start is the trusted onset; the 150 ms overlap is the retry pad on the earlier
word's end. `resolve_word_overlaps` sets `a.end = b.start` when `a.end > b.start` and
`b.start - a.start >= 0.02`; if the remainder is shorter, drop `a` and keep its text in
the card text only if it was not already covered. No later word start moves.

**D4 - Emit `\k` from absolute centisecond offsets.**
In `karaoke_ass.generate_karaoke_ass`, compute each word's offset from `card_start` once,
then emit `gap_cs = max(0, start_cs - elapsed_cs)` and `dur_cs = max(1, end_cs - start_cs)`,
tracking `elapsed_cs` from the emitted tags. Clamp `w_start = max(w_start, cur_t)` so the
clock never moves backwards. Rounding error no longer accumulates across a card.

**D5 - `pad_display_times` caps the hold, never the word span.**
`end = max(c["end"], min(end, c["start"] + max_dur))`. A card whose words run 4 s stays
4 s rather than hiding the last 1.2 s. 16 of 365 cards are affected; a separate long-card
splitter is out of scope unless the visual check says pacing is worse than the cutoff.

**D6 - Verify the card timeline, not the word timeline.**
New `repair_card_timeline(words, cards)` inserts a card for any word span not covered by
a card (group consecutive orphans, respect `max_chars`/`max_dur`). This is the guarantee
that closes the 8.95 s tail hole regardless of which stage lost the card. The engine calls
it after `words_to_cards`; the audit calls it too. It is pure and cheap, no decode.

**D7 - Spend the retry budget on voiced seconds, and say where it went.**
Rank gaps by the VAD speech overlap inside the gap (the same sum `find_speech_gaps` uses),
not raw gap length, so a music-heavy gap cannot outrank a speech gap. Keep the agreed budgets
(`min(180, 0.30 x duration)` and `min(60, 0.10 x duration)`). Add per-gap outcomes to the
report: `attempted`, `filled`, `still_open_s`, `spent_s`. The report gains keys; no
existing key changes meaning.

**D8 - Nondeterminism is handled by acceptance, not denial.**
Three runs per clip on the gate clip; acceptance is "0 card holes >= 2 s in every run".
Coverage is reported as min/median/max, never as a single number. No attempt to seed or
freeze cuDNN.

**D9 - Music over-detection is measured before it is fixed.**
Add `card_voiced_fraction` to the audit output. Act only if cards with < 20% voiced
fraction are common *and* their words are low-probability. No suppression code in this
plan.

## Shipped (2026-11-18)

All of Phases 0-4 are in the code. 427 tests pass (408 before, 19 new/updated).

- `normalize_word_timeline()` repairs zero-span clusters into the surrounding
  silence, trims overlaps at the later onset, and is called after the first
  decode, after gap fill, and before card building.
- The `\k` chain is emitted from absolute centisecond offsets with a clamped,
  monotonic clock; `tools/measure_timing._ass_chain_starts` mirrors it.
- `pad_display_times` caps the hold, never the spoken span.
- `repair_card_timeline` adds a card for any word a card does not cover.
- Main-pass gap ordering: visible holes (>= 2 s) first, shortest of those
  first, sub-2 s pauses last. Ranking by voiced seconds and relaxing the density
  rule for every gap were both tried and **reverted** (coverage fell to 79-89%,
  19-21 visible holes). Voiced seconds are reported per gap, not used for
  ranking. The audible
  hole the density rule hides is handled by a separate visible-hole pass with
  its own `min(120 s, 15% of clip)` budget inside any caller cap; it never
  re-decodes a gap the main or rescue pass already tried. The pass tries three
  combinations per hole - 0.15 s with prompt, 6 s with prompt, 20 s without -
  because a probe on two real holes showed one needed 20 s/no prompt while the
  other needed 6 s/with prompt. Runtime on the Samay clip is 374 s versus
  298-326 s before the coverage work.
- A bounded tail decode covers speech after the last word.
- **Second-pass ensemble for unstable decodes.** When the visible holes contain
  more than `max(2 s, 1% of voiced time)`, `transcribe_words` makes one more
  full decode with the same settings and `merge_alt_words_into_gaps` takes only
  the second pass's words that land in the first pass's open holes. This uses
  the clip's nondeterminism instead of fighting it. Clean clips do not pay for
  it (measured: 0 s of visible voiced holes on AUKAAT and DualSense, 3.0 s vs
  a 4.8 s threshold on Announcement). Test:
  `test_weak_first_decode_borrows_words_from_a_second_pass`.
- **Large holes split by VAD region.** `retry_gap_by_regions` decodes a hole
  longer than 8 s as its individual speech regions with 0.15 s padding. A 26 s
  hole of eight regions decoded to zero words as one slice, but the same audio
  decoded region by region gave 18 words in a 4 s sub-slice. Test:
  `test_large_gap_is_decoded_as_separate_vad_regions`.
- **VAD music filter.** `filter_music_regions` drops 100 ms frames that are
  both quiet (< 35% of the clip's median VAD RMS) and spectrally flat
  (flatness > 0.55) before any gap is measured. The audit's "music over-detection"
  note is now proven: the stubborn 19.6-21.1 s hole measured RMS 0.015 versus
  0.055 for speech and flatness 0.58 versus 0.27-0.39. Test:
  `test_filter_music_regions_drops_quiet_flat_frames`.
- `tools/audit_fixed.py` saves intermediates and checks every invariant;
  `tools/visual_burn_saved.py` burns a window from a saved full-clip run.

One defect was found during the real-clip smoke test and fixed beyond the
original plan (**D10**): the 40% speech-density rule rejected a visible 3.8 s
hole with 1.51 s of VAD speech in two regions (1.51 < 1.52 by a hair). It is
now handled by the separately budgeted visible-hole pass
(`find_speech_gaps(..., density=0.0)`), not by weakening the main detector.
Tests: `test_find_speech_gaps_visible_hole_needs_density_zero`,
`test_visible_gap_pass_runs_on_its_own_budget`. The first attempt at D10,
plus voiced-seconds ranking, was measured on the full clip and reverted; the
longest-first test `test_gap_budget_ranks_longest_gap_first` locks that in.

Test placement differs slightly from the written plan: the new timeline,
card and coverage tests live in `tests/test_word_timeline.py` (one new file)
so the user's uncommitted `wav_path` edit in `tests/test_upgrades.py` is not
touched. One old `pad_display_times` test in that file was updated to the new
"hold is capped, span is not" contract; the user's edit is untouched.

## Real-clip results (final code)

Structural invariants, every run, every clip: 0 zero-span words, 0 word
overlaps > 20 ms, 0 cards ending before their last word, 0 orphan word spans,
0 `\k` outliers > 20 ms. 432 unit tests pass.

| Clip (run) | Coverage | Card holes >= 2 s | Gate |
|---|---|---|---|
| AUKAAT | 99.53% | 0 | pass |
| DualSense | 98.98% | 0 | pass |
| Announcement | 99.05% | 0 (1 word hole, bridged) | pass |
| Samay 1 | 96.65% | 0 | pass |
| Samay 2 | 92.98% | 0 | pass |
| Samay 3 | 97.22% | 0 | pass |

These three runs use the final code: VAD music filter, visible-first shortest
gap ordering, region-by-region decoding of holes over 8 s, the three-context
retry ladder, second-pass ensemble, and the wide tail decode. Earlier tables
in this file record the failed attempts that led to each change. Runtime is
295-365 s on the Samay clip versus 298-326 s before the coverage work.

Diagnosis that led to the final design: (1) the 19.6-21.1 s "hole" was
background music, not speech - RMS 0.015 versus 0.055 for speech, flatness 0.58
versus 0.27-0.39 - so the VAD filter, not more decoding, was the fix; (2) a 26 s
hole of eight VAD regions decoded to zero words as one slice but yielded 18
words from a 4 s sub-slice, so large holes are split at region boundaries;
(3) longest-first budget ordering left short visible holes unattempted, so
visible holes now come first, shortest first. The second-pass ensemble and
three-context ladder handle the cases those two changes do not.

Visual burn from a saved final full-clip run: 155-185 s frames at 160.2 s
("DOING KAAM AAP") and 166.7 s show correct captions with no early cutoff in
the formerly overlapping-word window. The 834-864 s window now has cards all
the way to 864.29 s, including "YE BHI GHAJLON KA DORO THA" at 859 s; a frame
at 847.7 s renders "MUJHE KYO PAHNA HAI BHRAAI PHIR VRAAN" correctly. The
former 9 s uncaptioned tail is gone.

## Task List

### Phase 0 - Failing tests first

- [ ] **Task 0: `tests/test_word_timeline.py` (new, all failing).**
  1. `test_zero_span_run_is_distributed_into_the_gap`: words `0-1.0`, `5.0-5.0` x2,
     `5.5-6.0` -> both middle words get spans inside `[1.0, 5.5]`, sorted, text preserved.
  2. `test_zero_span_junk_is_dropped`: a zero-span token with `prob=0.0` disappears.
  3. `test_zero_span_run_is_capped`: a 6-word run at `t` with the next word at `t+8`
     stretches at most `ZERO_SPAN_MAX_STRETCH` (1.5 s), not 8 s.
  4. `test_overlap_trims_the_earlier_word`: `0-1.0`, `0.85-1.2` -> first end `0.85`,
     second start unchanged.
  5. `test_overlap_shorter_than_20ms_is_merged_or_dropped`: `0-1.0`, `0.99-1.2` leaves
     no overlap and no zero span.
  6. `test_first_decode_output_has_no_zero_or_overlapping_words`: stub model returns the
     real 5.74 / 35.06 / 467.46 patterns; assert the invariants after `_decode_words`.
  7. `test_timeline_is_stable_when_normalized_twice`: idempotent.

- [ ] **Task 1: `tests/test_karaoke_ass.py` additions (failing).**
  1. `test_chain_matches_word_starts_with_overlapping_words`: a card with a 150 ms
     overlap; replay the `\k` chain and assert every start is within 10 ms of the clamped
     word start.
  2. `test_chain_never_moves_backwards`: cumulative cs is monotonic for zero-span and
     overlapping inputs.
  3. `test_chain_uses_absolute_offsets`: five words with 0.004 s fractional parts; the
     accumulated error at the last word is <= 10 ms, not 5 x rounding.

- [ ] **Task 2: `tests/test_upgrades.py` additions (failing).**
  1. `test_pad_display_never_ends_before_last_word`: card `start=10`, last word ends
     `14.0`, `max_dur=2.8` -> `end >= 14.0`.
  2. `test_pad_display_still_caps_the_hold`: a 1 s card with no tail -> unchanged.
  3. `test_pad_display_does_not_overlap_next_card`: consecutive cards 20 ms apart ->
     overlap <= 0.04 s.
  4. `test_repair_card_timeline_adds_orphan_tail`: words `0-1`, `5-6`; cards `0-1` ->
     a second card covers `5-6`.
  5. `test_repair_card_timeline_is_idempotent`.

- [ ] **Task 3: `tests/test_speech_coverage.py` additions (failing).**
  1. `test_gap_budget_ranks_by_voiced_seconds`: gap A 6 s with 1 s voiced, gap B 4 s
     with 4 s voiced, cap 4.5 s -> B is attempted, A is not.
  2. `test_report_records_per_gap_outcomes`: `attempted`, `filled`, `still_open_s`,
     `spent_s` present and consistent with the stub model.
  3. `test_repair_card_timeline_after_fill_is_covered`: fill a gap, rebuild, assert no
     card hole remains.

Run the three files; every new test must fail for the stated reason before Phase 1.

### Phase 1 - Word timeline (`hinglish_upgrades.py`)

- [ ] **Task 4: Constants.**
  ```python
  ZERO_SPAN_MAX_STRETCH = 1.5
  ZERO_SPAN_MIN = 0.02
  ZERO_SPAN_PROB_DROP = 0.05
  OVERLAP_MIN_REMAINDER = 0.02
  ```

- [ ] **Task 5: `resolve_word_overlaps(words)`.**
  Sort by `(start, end)`, walk once, trim `a.end` to `b.start` per D3. Pure.

- [ ] **Task 6: `repair_zero_spans(words, duration=None)`.**
  Group maximal runs at one timestamp, distribute per D2, use `prev_end` and `next_start`
  as bounds, cap at `ZERO_SPAN_MAX_STRETCH`, drop `prob <= 0.05` and punctuation-only
  tokens. Pure.

- [ ] **Task 7: `normalize_word_timeline(words, duration=None)`.**
  `sanitize_words` -> `resolve_word_overlaps` -> `repair_zero_spans` -> `resolve_word_overlaps`
  again (repair can create a touch, not an overlap). Idempotent.

- [ ] **Task 8: Wire it.**
  - `_decode_words`: `return normalize_word_timeline(words)` before coverage.
  - `fill_speech_gaps`: normalize `current_words` before the report is computed.
  - `words_to_cards`: normalize at the top, before `snap_to_terms`.
  No signature changes.

### Phase 2 - Karaoke chain (`karaoke_ass.py`)

- [ ] **Task 9: Rewrite the `\k` loop per D4.**
  Compute `start_cs`/`end_cs` from `card_start`, clamp to `elapsed_cs`, emit deltas,
  track `elapsed_cs` exactly. Keep the `static` path untouched.

- [ ] **Task 10: Regression check.**
  Existing `tests/test_karaoke_ass.py` and `tests/test_caption_clock.py` stay green;
  add a fixture with a 150 ms overlap and a zero-span word.

### Phase 3 - Card display and card repair (`hinglish_upgrades.py`)

- [ ] **Task 11: `pad_display_times` per D5.**
  Cap the hold only; guarantee `end >= c["end"]`; keep the next-card clamp but allow at
  most a 40 ms touch when the words are adjacent.

- [ ] **Task 12: `repair_card_timeline(words, cards, *, max_chars=42, max_dur=2.8)`.**
  Find word spans with no card coverage (`_covered_seconds` per word is 0). Group
  consecutive orphans (break on a > 1.0 s silence or `max_chars`). Build cards with the
  same `{"start","end","text","words"}` shape, sorted into the list. Pure.

- [ ] **Task 13: Wire it.**
  In `words_to_cards`, after `pad_display_times`, call `repair_card_timeline` before the
  final export. The engine gets the guarantee without a new call site.

### Phase 4 - Coverage report and budget (`hinglish_upgrades.py`)

- [ ] **Task 14: Rank by voiced seconds.**
  In `fill_speech_gaps`, sort gaps by VAD speech overlap inside the gap (sum of
  `min(g1, r1) - max(g0, r0)` over regions), descending. Keep longest-first as the
  tie-break.

- [ ] **Task 15: Per-gap outcomes.**
  Track `{"g0","g1","voiced_s","attempted","filled","still_open_s","spent_s"}` for every
  gap in `gaps`; add `"gap_details": [...]` to the report. Do not remove or rename keys.

- [ ] **Task 16: Tail/orphan safety net.**
  After the rescue pass, if `duration - last_word_end >= GAP_ACCEPT_S` and any VAD speech
  exists after `last_word_end`, decode `[max(0, last_word_end - 1.0), duration]` once
  (`pad=0`, `prompt=None`, `hotwords=None`) and merge. Record it as `tail_attempted` /
  `tail_recovered_s`. This is the one case the density rule can reject and a person sees.

### Phase 5 - Audit harness and real-clip verification

- [ ] **Task 17: Update `%TEMP%\audit_videos.py` (keep a copy in `tools/`).**
  Save `words`, `cards`, `regions`, `coverage`, and the new report to
  `video_audit/<clip>.json` on every run. Add `zero_span_words`, `word_overlaps`,
  `cards_ending_early`, `orphan_word_spans`, `card_voiced_fraction`. Add `--repeat N`.

- [ ] **Task 18: Gate clip x3.**
  `I GOT ROASTED BY SAMAY RAINA.mp4`, empty hint, three runs. For each run require:
  - 0 card holes >= 2 s;
  - 0 zero-span words;
  - 0 word overlaps > 20 ms;
  - 0 cards ending before their last word;
  - 0 orphan word spans;
  - `ass_chain_over_20ms == 0`;
  - report min/median/max coverage.
  If a run fails, save its intermediates before touching code.

- [ ] **Task 19: Other three clips x1.**
  Same invariants. AUKAAT and DualSense are the regression guard for the timeline repair;
  Announcement is the guard for the single-word-hole case.

- [ ] **Task 20: Visual burn check.**
  Samay last 30 s (the former tail hole) and one mid-clip window containing a formerly
  overlapping word (e.g. 161.18 or 540.92). Inspect 6 frames each. No caption may end
  while the mouth is still moving on that word.

### Phase 6 - Review and gate

- [ ] **Task 21: Full suite.** `python -m pytest tests -q`; 408 existing tests plus the
  new ones. Fix regressions, not tests.
- [ ] **Task 22: `/ponytail-review`.** The coverage report gains keys and `words_to_cards`
  gains a repair stage; treat it as an API-shape change.
- [ ] **Task 23: Report the numbers.** Before/after table per clip: zero-span words,
  overlaps, early card ends, card holes, `\k` outliers, coverage min/median/max, runtime.
- [ ] **Task 24: Commit gate.** Ask first. Never stage `launch_config.json` or the
  `wav_path` change in `tests/test_upgrades.py`. The hotword guard is a separate commit.

## Acceptance

- Unit suite green, including the 18 new tests.
- Samay x3: every invariant above passes in every run.
- Other three x1: every invariant passes.
- No visible hole >= 2 s in any run; coverage is reported, not gated.
- Runtime does not grow by more than ~10% on the Samay clip (298 s baseline run one,
  326 s baseline run two).
- The burn check shows no early card cutoff and no late highlight in the sampled windows.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Redistribution stretches junk tokens into visible text | prob floor, 1.5 s cap, punctuation drop, visual check |
| Trimming earlier word ends shortens a real long word | later onset is the trusted one; measure coverage and word count before/after |
| Cards > 2.8 s hurt pacing (16 cases) | visual check; a splitter is a follow-up, not part of this plan |
| Timeline repair changes card grouping on clean clips | AUKAAT/DualSense regression runs; compare cards and coverage |
| Budget ranking changes which gaps get filled | per-gap report makes the change auditable; budgets unchanged |
| The 8.95 s tail mechanism is not fully proven | `repair_card_timeline` guarantees coverage; the saved intermediates name the stage if it recurs |
| New report keys break a consumer | keys are additive; `/ponytail-review` before commit |

## Out of Scope

- Making Whisper deterministic, seeding cuDNN, or parallel chunk decoding.
- Changing the retry budgets or the hotword rescue thresholds.
- Music suppression / VAD tuning (measure first, decide after Task 17).
- Splitting cards longer than `max_dur` (only if the visual check demands it).
- Committing or pushing anything without the user's word.

## Estimate

Implementation and unit tests: 2.5-3.5 h. Real-clip verification (Samay x3 plus three
clips): ~25 min. Review and report: ~20 min. Total ~4 h.
