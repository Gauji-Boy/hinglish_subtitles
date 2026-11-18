"""Tests for the word-timeline, card-timeline and karaoke-chain audit fixes.

Written first (red): every test in this file fails against the pre-fix code.
"""

import numpy as np
import pytest

import hinglish_engine  # noqa: F401 - CUDA DLL load order: engine before upgrades
import hinglish_upgrades as hu


# --------------------------------------------------------------------------- helpers

def w(start, end, text, prob=0.9, **extra):
    return dict(start=start, end=end, text=text, prob=prob, **extra)


class StubWord:
    def __init__(self, start, end, word, probability=0.9):
        self.start = start
        self.end = end
        self.word = word
        self.probability = probability


class StubSegment:
    def __init__(self, words):
        self.words = words


class StubModel:
    """Records each slice length so the budget ranking test can see which gap ran."""

    def __init__(self, words_to_return=None):
        self.words_to_return = words_to_return or []
        self.calls = 0
        self.audio_lengths = []

    def transcribe(self, audio, initial_prompt=None, hotwords=None, **kwargs):
        self.calls += 1
        self.audio_lengths.append(len(audio))
        return [StubSegment(self.words_to_return)], None


# ------------------------------------------------------------------ timeline: 7 tests

def test_zero_span_run_is_distributed_into_the_gap():
    words = [
        w(0.0, 1.0, "a"),
        w(5.0, 5.0, "x", 0.8),
        w(5.0, 5.0, "y", 0.7),
        w(5.5, 6.0, "b"),
    ]
    out = hu.normalize_word_timeline(words, duration=6.0)
    assert [x["text"] for x in out] == ["a", "x", "y", "b"]
    assert all(x["end"] > x["start"] for x in out)
    assert all(a["end"] <= b["start"] for a, b in zip(out, out[1:]))
    x, y = out[1], out[2]
    assert x["start"] >= 1.0 and y["end"] <= 5.5


def test_zero_span_junk_is_dropped():
    words = [w(0.0, 1.0, "a"), w(2.0, 2.0, "parole", 0.0), w(2.0, 2.5, "b")]
    out = hu.normalize_word_timeline(words, duration=3.0)
    assert [x["text"] for x in out] == ["a", "b"]
    assert all(x["end"] > x["start"] for x in out)


def test_zero_span_run_is_capped():
    run = [w(9.0, 9.0, "w%d" % i, 0.5) for i in range(6)]
    words = [w(1.0, 2.0, "a")] + run + [w(17.0, 17.5, "z")]
    out = hu.normalize_word_timeline(words, duration=18.0)
    middle = out[1:-1]
    assert len(middle) == 6
    assert max(x["end"] for x in middle) - min(x["start"] for x in middle) <= 3.001


def test_overlap_trims_the_earlier_word():
    out = hu.normalize_word_timeline([w(0.0, 1.0, "a"), w(0.85, 1.2, "b")], duration=2.0)
    assert len(out) == 2
    assert out[0]["end"] == pytest.approx(0.85)
    assert out[1]["start"] == pytest.approx(0.85)
    assert out[1]["end"] == pytest.approx(1.2)


def test_overlap_drops_word_with_no_room_after_trim():
    out = hu.normalize_word_timeline([w(0.0, 1.0, "a"), w(0.01, 1.2, "b")], duration=2.0)
    assert [x["text"] for x in out] == ["b"]


def test_first_decode_output_has_no_zero_or_overlapping_words():
    model = StubModel([
        StubWord(5.74, 5.74, "एक"), StubWord(5.74, 5.74, "सहाँ"),
        StubWord(5.74, 5.78, "ने"), StubWord(35.06, 35.06, "to"),
        StubWord(35.06, 35.06, "shoot"), StubWord(35.06, 35.56, "BGMI"),
    ])
    audio = np.zeros(40 * 16000, dtype=np.float32)
    words = hu._decode_words(model, audio, "hi", "transcribe", "", "", 5)
    assert len(words) == 6
    assert all(x["end"] > x["start"] for x in words)
    assert all(a["end"] <= b["start"] for a, b in zip(words, words[1:]))


def test_timeline_is_stable_when_normalized_twice():
    words = [w(0.0, 1.0, "a"), w(1.0, 1.0, "x"), w(0.9, 1.4, "b"), w(2.0, 2.5, "c")]
    once = hu.normalize_word_timeline(words, duration=3.0)
    twice = hu.normalize_word_timeline(once, duration=3.0)
    assert twice == once


def test_filter_music_regions_drops_quiet_flat_frames():
    sr = 16000
    t = np.arange(sr) / sr
    speech = (0.1 * np.sin(2 * np.pi * 200 * t)).astype(np.float32)
    noise = np.random.RandomState(0).normal(0, 0.01, sr).astype(np.float32)
    audio = np.concatenate([speech, noise])
    regions = hu.filter_music_regions(audio, [(0.0, 2.0)], sr)
    assert len(regions) == 1
    assert regions[0][0] < 0.2
    assert regions[0][1] <= 1.2


def test_find_speech_gaps_visible_hole_needs_density_zero():
    # Real case: 3.8 s between words, 1.51 s voiced in two short regions.
    # 1.51 < 0.4 * 3.8 (1.52), so the density rule hides it. The separate
    # visible-hole pass calls with density=0; the main pass keeps the rule.
    words = [w(16.91, 18.41, "before"), w(22.21, 23.0, "after")]
    regions = [(18.944, 19.392), (21.152, 23.84)]
    assert (18.41, 22.21) not in hu.find_speech_gaps(words, regions, duration=30.0)
    assert (18.41, 22.21) in hu.find_speech_gaps(words, regions, duration=30.0,
                                                  density=0.0)


def test_large_gap_is_decoded_as_separate_vad_regions():
    audio = np.zeros(30 * 16000, dtype=np.float32)
    words = [w(0.0, 2.0, "before"), w(28.0, 30.0, "after")]
    regions = [(4.0, 6.0), (10.0, 12.0), (20.0, 22.0)]
    model = StubModel([StubWord(0.1, 0.5, "recovered")])
    out, spent = hu.retry_gap_by_regions(
        model, audio, words, 2.0, 28.0, regions, sampling_rate=16000,
        language="hi", task="transcribe", prompt="", hotwords=None)
    assert model.calls == 3
    assert spent > 0
    assert sum(1 for x in out if x["text"] == "recovered") == 3


def test_visible_gap_pass_runs_on_its_own_budget():
    audio = np.zeros(600 * 16000, dtype=np.float32)
    words = [w(0.0, 4.0, "before"), w(22.21, 23.0, "after")]
    regions = [(18.944, 19.392), (21.152, 23.84)]
    model = StubModel([StubWord(15.15, 17.15, "recovered")])
    _, report = hu.fill_speech_gaps(model, audio, words, regions=regions,
                                    cap_s=100.0, sampling_rate=16000)
    assert report["visible_gaps_found"] >= 1
    assert report["visible_seconds_spent"] > 0
    # The visible pass is bounded by min(120 s, 15% of the clip).
    assert report["visible_seconds_spent"] <= 120.0 + 0.5


# --------------------------------------------------------------- card display: 5 tests

def test_pad_display_never_ends_before_last_word():
    card = {"start": 10.0, "end": 14.0, "text": "long word",
            "words": [w(10.0, 14.0, "long")]}
    out = hu.pad_display_times([card], pacing="short")
    assert out[0]["end"] >= 14.0


def test_pad_display_still_caps_the_hold():
    card = {"start": 1.0, "end": 2.0, "text": "a", "words": [w(1.0, 2.0, "a")]}
    nxt = {"start": 3.0, "end": 3.8, "text": "b", "words": [w(3.0, 3.8, "b")]}
    out = hu.pad_display_times([card, nxt], pacing="short")
    assert out[0]["end"] == pytest.approx(2.3)


def test_pad_display_does_not_overlap_next_card():
    first = {"start": 1.0, "end": 2.0, "text": "a", "words": [w(1.0, 2.0, "a")]}
    second = {"start": 2.02, "end": 3.0, "text": "b", "words": [w(2.02, 3.0, "b")]}
    out = hu.pad_display_times([first, second], pacing="short")
    assert out[0]["end"] <= out[1]["start"] + 0.041


def test_repair_card_timeline_adds_orphan_tail():
    words = [w(0.0, 1.0, "a"), w(5.0, 6.0, "b")]
    cards = [{"start": 0.0, "end": 1.0, "text": "a", "words": [words[0]]}]
    out = hu.repair_card_timeline(words, cards)
    assert len(out) == 2
    assert out[1]["start"] == pytest.approx(5.0)
    assert out[1]["end"] == pytest.approx(6.0)
    assert [x["text"] for x in out[1]["words"]] == ["b"]


def test_repair_card_timeline_is_idempotent():
    words = [w(0.0, 1.0, "a"), w(5.0, 6.0, "b")]
    once = hu.repair_card_timeline(words, [])
    twice = hu.repair_card_timeline(words, once)
    assert twice == once


# ----------------------------------------------------------------- coverage: 3 tests

def test_gap_budget_ranks_shortest_gap_first():
    audio = np.zeros(25 * 16000, dtype=np.float32)
    words = [w(10.0, 20.0, "mid")]
    regions = [(0.0, 4.0), (20.0, 24.9)]
    model = StubModel()
    hu.fill_speech_gaps(model, audio, words, regions=regions, cap_s=5.5,
                        sampling_rate=16000)
    assert model.calls >= 1
    # With a fixed budget, attempting the short 5 s tail gap first reaches
    # more holes than spending the budget on the 10 s head gap.
    assert model.audio_lengths[0] < 100000


def test_report_records_per_gap_outcomes():
    audio = np.zeros(10 * 16000, dtype=np.float32)
    words = [w(4.0, 6.0, "mid")]
    regions = [(1.0, 3.0)]
    model = StubModel()
    _, report = hu.fill_speech_gaps(model, audio, words, regions=regions,
                                    cap_s=10.0, sampling_rate=16000)
    assert report["gap_details"]
    detail = report["gap_details"][0]
    for key in ("g0", "g1", "voiced_s", "attempted", "filled", "still_open_s", "spent_s"):
        assert key in detail
    assert detail["attempted"] is True


def test_tail_safety_net_decodes_speech_after_last_word():
    audio = np.zeros(30 * 16000, dtype=np.float32)
    words = [w(0.0, 4.0, "before")]
    regions = [(20.0, 24.0)]

    class TailModel:
        calls = 0

        def transcribe(self, slice_audio, initial_prompt=None, hotwords=None, **kwargs):
            type(self).calls += 1
            # The tail slice is ~7 s with the wide pad; the full-gap retry is
            # ~26 s. Only the tail decode returns words. Its slice starts at
            # 19.85 - 2.0 = 17.85 s, so relative 2.15 lands at 20 s.
            if len(slice_audio) > 200000:
                return [StubSegment([])], None
            return [StubSegment([
                StubWord(2.15, 4.15, "tail"), StubWord(4.15, 6.15, "words"),
            ])], None

    filled, report = hu.fill_speech_gaps(TailModel(), audio, words,
                                         regions=regions, cap_s=100.0,
                                         sampling_rate=16000)
    # The wide tail decode or the region-split visible pass may get there
    # first; either way the speech after 19 s must end up in the word list.
    assert any(x["start"] >= 19.0 for x in filled)
    assert report["covered_ratio"] > 0.9


def test_weak_first_decode_borrows_words_from_a_second_pass(monkeypatch):
    # A silent numpy array has no VAD regions; give the clip one voiced span
    # that the first decode misses.
    monkeypatch.setattr(hu, "speech_regions", lambda *a, **k: [(10.0, 14.0)])
    bad = [StubWord(0.0, 4.0, "before")]
    good = [StubWord(0.0, 4.0, "before"), StubWord(10.0, 14.0, "after")]

    class TwoPassModel:
        full_calls = 0

        def transcribe(self, audio, initial_prompt=None, hotwords=None, **kwargs):
            # Only the two full-file decodes see 30 s of audio; gap retries see
            # short slices and return nothing.
            if len(audio) >= 30 * 16000:
                type(self).full_calls += 1
                words = bad if type(self).full_calls == 1 else good
            else:
                words = []
            return [StubSegment(words)], None

    words, report = hu.transcribe_words(TwoPassModel(),
                                        np.zeros(30 * 16000, dtype=np.float32),
                                        language="hi", topic_hint="", task="transcribe")
    assert report["ensemble_attempted"] is True
    assert report["ensemble_words_added"] >= 1
    assert report["covered_ratio"] == 1.0
    assert any(w["text"] == "after" for w in words)


def test_repair_card_timeline_after_fill_is_covered(monkeypatch):
    monkeypatch.setattr(hu, "export_decisions", lambda *a, **k: None)
    audio = np.zeros(30 * 16000, dtype=np.float32)
    words = [w(0.0, 4.0, "before")]
    regions = [(10.0, 14.0)]
    # Stub word times are relative to the slice: the first slice starts at
    # 4.0 - 0.15 = 3.85 s, so 6.15-10.15 lands at 10-14 s in clip time.
    model = StubModel([StubWord(6.15, 8.15, "after"), StubWord(8.15, 10.15, "that")])
    filled, _ = hu.fill_speech_gaps(model, audio, words, regions=regions,
                                    cap_s=10.0, sampling_rate=16000)
    cards = hu.words_to_cards(filled, lambda s: s, pacing="short")
    holes = hu.find_speech_gaps(cards, regions, duration=30.0, min_gap=2.0)
    assert holes == []
