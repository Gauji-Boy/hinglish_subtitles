"""
tests/test_speech_coverage.py - Pure-function tests for speech coverage and gap recovery.
"""

import numpy as np
import pytest
from hinglish_upgrades import (
    find_speech_gaps,
    merge_words,
    fill_speech_gaps,
    GAP_MIN_S,
    GAP_MIN_SPEECH_S,
)


class StubWord:
    def __init__(self, start: float, end: float, word: str, probability: float = 0.9):
        self.start = start
        self.end = end
        self.word = word
        self.probability = probability


class StubSegment:
    def __init__(self, words):
        self.words = words


class StubModel:
    def __init__(self, words_to_return=None, sequence=None):
        self.words_to_return = words_to_return or []
        self.sequence = sequence
        self.call_count = 0
        self.prompts = []

    def transcribe(self, audio, initial_prompt=None, **kwargs):
        self.call_count += 1
        self.prompts.append(initial_prompt)
        if self.sequence:
            idx = min(self.call_count - 1, len(self.sequence) - 1)
            return [StubSegment(self.sequence[idx])], None
        return [StubSegment(self.words_to_return)], None


def test_find_speech_gaps_empty_when_covered():
    # 1. find_speech_gaps returns [] when words already cover every VAD region.
    words = [
        {"start": 0.0, "end": 5.0, "text": "first"},
        {"start": 5.0, "end": 10.0, "text": "second"},
    ]
    regions = [(1.0, 4.0), (6.0, 9.0)]
    gaps = find_speech_gaps(words, regions, duration=10.0)
    assert gaps == []


def test_find_speech_gaps_detects_real_gap():
    # 2. Given words that stop at 15.4 and resume at 25.47 and one VAD region
    #    16.61–26.53, it returns [(15.4, 25.47)].
    words = [
        {"start": 0.0, "end": 15.4, "text": "intro"},
        {"start": 25.47, "end": 30.0, "text": "resume"},
    ]
    regions = [(16.61, 26.53)]
    gaps = find_speech_gaps(words, regions, duration=30.0)
    assert gaps == [(15.4, 25.47)]


def test_find_speech_gaps_ignores_small_gap():
    # 3. A gap of 0.3 s is ignored (GAP_MIN_S = 0.6).
    words = [
        {"start": 0.0, "end": 2.0, "text": "word1"},
        {"start": 2.3, "end": 5.0, "text": "word2"},
    ]
    regions = [(0.0, 5.0)]
    gaps = find_speech_gaps(words, regions, duration=5.0)
    assert gaps == []


def test_find_speech_gaps_ignores_music_bed_no_vad():
    # 4. A gap of 8 s with no VAD overlap (music bed) is ignored.
    words = [
        {"start": 0.0, "end": 2.0, "text": "word1"},
        {"start": 10.0, "end": 12.0, "text": "word2"},
    ]
    regions = [(0.0, 2.0), (10.0, 12.0)]
    gaps = find_speech_gaps(words, regions, duration=12.0)
    assert gaps == []


def test_find_speech_gaps_ignores_insufficient_speech():
    # 5. A gap of 8 s with 0.3 s of VAD speech is ignored (GAP_MIN_SPEECH_S = 0.4).
    words = [
        {"start": 0.0, "end": 2.0, "text": "word1"},
        {"start": 10.0, "end": 12.0, "text": "word2"},
    ]
    regions = [(3.0, 3.3)]  # 0.3 s of speech
    gaps = find_speech_gaps(words, regions, duration=12.0)
    assert gaps == []


def test_merge_words_drops_overlapping_retry():
    # 6. merge_words sorts by start and drops a retry word overlapping an existing word by >50%.
    existing = [
        {"start": 0.0, "end": 2.0, "text": "existing"},
        {"start": 8.0, "end": 10.0, "text": "tail"},
    ]
    # Retry word overlaps [1.0, 2.0] of "existing" (1.0s overlap / 1.5s shorter span = 66% > 50%)
    retry = [
        {"start": 1.0, "end": 2.5, "text": "overlap_drop"},
        {"start": 4.0, "end": 5.0, "text": "clean_keep"},
    ]
    merged = merge_words(existing, retry)
    texts = [w["text"] for w in merged]
    assert texts == ["existing", "clean_keep", "tail"]


def test_merge_words_keeps_adjacent_retry():
    # 7. merge_words keeps a retry word that starts exactly where the previous one ends.
    existing = [
        {"start": 0.0, "end": 1.0, "text": "first"},
        {"start": 3.0, "end": 4.0, "text": "third"},
    ]
    retry = [
        {"start": 1.0, "end": 3.0, "text": "second"},
    ]
    merged = merge_words(existing, retry)
    texts = [w["text"] for w in merged]
    assert texts == ["first", "second", "third"]
    assert merged[1]["start"] == 1.0
    assert merged[1]["end"] == 3.0


def test_fill_speech_gaps_success_report():
    # 8. fill_speech_gaps with a stub model returns the merged list and a report
    #    {"gaps_found": 1, "gaps_filled": 1, ...}.
    words = [
        {"start": 0.0, "end": 2.0, "text": "start"},
        {"start": 8.0, "end": 10.0, "text": "end"},
    ]
    regions = [(3.0, 7.0)]
    # Audio of length 10 s (160000 samples)
    audio = np.zeros(160000, dtype=np.float32)
    # Stub covers the hole (slice coords) so the gap is closed by measurement.
    # Gap is 2.0 to 8.0 (length 6.0). With pad 0.15, slice is [1.85, 8.15].
    stub = StubModel([
        StubWord(0.5, 1.5, "recovered", probability=0.9),
        StubWord(1.5, 2.5, "words", probability=0.9),
        StubWord(2.5, 3.5, "cover", probability=0.9),
        StubWord(3.5, 4.5, "the", probability=0.9),
        StubWord(4.5, 5.5, "whole", probability=0.9),
        StubWord(5.5, 6.1, "gap", probability=0.9),
    ])

    merged, report = fill_speech_gaps(
        stub, audio, words, language="hi", task="transcribe", prompt="",
        regions=regions
    )
    assert report["gaps_found"] == 1
    assert report["gaps_filled"] == 1
    assert any(w["text"] == "recovered" for w in merged)


def test_fill_speech_gaps_respects_cap():
    # 9. fill_speech_gaps stops calling the model once the cap is reached and reports gaps_skipped >= 1.
    words = [
        {"start": 0.0, "end": 1.0, "text": "w0"},
        {"start": 5.0, "end": 6.0, "text": "w1"},
        {"start": 10.0, "end": 11.0, "text": "w2"},
        {"start": 15.0, "end": 16.0, "text": "w3"},
    ]
    # 3 gaps: [1.0, 5.0] (4s), [6.0, 10.0] (4s), [11.0, 15.0] (4s)
    regions = [(1.5, 4.5), (6.5, 9.5), (11.5, 14.5)]
    audio = np.zeros(16000 * 20, dtype=np.float32)
    stub = StubModel([StubWord(1.0, 2.0, "rec", probability=0.9)])

    # Cap at 4.0 seconds -> gap 1 takes 4.3s, reaching the cap. The rescue pass only
    # spends what the cap left over (nothing), so the model is called exactly once.
    merged, report = fill_speech_gaps(
        stub, audio, words, language="hi", task="transcribe", prompt="",
        cap_s=4.0, regions=regions
    )
    assert report["gaps_found"] == 3
    assert report["gaps_filled"] == 0
    assert report["gaps_skipped"] == 3
    assert report["skipped_seconds"] > 0
    assert stub.call_count == 1


def test_fill_speech_gaps_rejects_hallucinated_density():
    # 10. fill_speech_gaps rejects a region whose stub returns 40 words for 2 s of audio
    #     (density guard) and reports it skipped.
    words = [
        {"start": 0.0, "end": 2.0, "text": "start"},
        {"start": 4.0, "end": 6.0, "text": "end"},
    ]
    # Gap is [2.0, 4.0] (2 s)
    regions = [(2.2, 3.8)]
    audio = np.zeros(16000 * 10, dtype=np.float32)

    # 40 words inside 2 s slice -> density = 20 words/s > 6.0 words/s
    dense_words = [StubWord(i * 0.05, (i + 1) * 0.05, f"w{i}", probability=0.9) for i in range(40)]
    stub = StubModel(dense_words)

    merged, report = fill_speech_gaps(
        stub, audio, words, language="hi", task="transcribe", prompt="",
        regions=regions
    )
    assert report["gaps_found"] == 1
    assert report["gaps_filled"] == 0
    assert report["gaps_skipped"] == 1
    # None of the hallucinated words should be in merged
    assert len(merged) == 2


def test_merge_words_drops_zero_and_sub_005_span():
    # Zero-length or sub-0.05s retry words must be dropped
    existing = [
        {"start": 0.0, "end": 1.0, "text": "start"},
        {"start": 5.0, "end": 6.0, "text": "end"},
    ]
    retry = [
        {"start": 2.0, "end": 2.0, "text": "zero_len"},
        {"start": 2.5, "end": 2.53, "text": "tiny_003"},
        {"start": 3.0, "end": 3.2, "text": "valid_span"},
    ]
    merged = merge_words(existing, retry)
    texts = [w["text"] for w in merged]
    assert texts == ["start", "valid_span", "end"]


def test_merge_words_drops_exact_duplicate_span():
    # Identical span duplicate retry words must be dropped
    existing = [
        {"start": 0.0, "end": 1.0, "text": "first"},
        {"start": 2.0, "end": 2.5, "text": "second"},
    ]
    retry = [
        {"start": 2.0, "end": 2.5, "text": "duplicate_second"},
        {"start": 3.0, "end": 3.5, "text": "third"},
    ]
    merged = merge_words(existing, retry)
    texts = [w["text"] for w in merged]
    assert texts == ["first", "second", "third"]


def test_fill_speech_gaps_drops_zero_length_and_duplicate_spans():
    # Gap fill with multiple copies of zero-span words (e.g. 16.38->16.38) must not accept them
    words = [
        {"start": 0.0, "end": 2.0, "text": "start"},
        {"start": 5.0, "end": 7.0, "text": "end"},
    ]
    regions = [(2.5, 4.5)]
    audio = np.zeros(16000 * 10, dtype=np.float32)

    # Slice start is 2.0 - 0.15 = 1.85. Stub words at 1.0 -> 1.85 + 1.0 = 2.85
    zero_span_words = [
        StubWord(1.0, 1.0, "ghost1", probability=0.8),
        StubWord(1.0, 1.0, "ghost2", probability=0.8),
        StubWord(1.0, 1.0, "ghost3", probability=0.8),
    ]
    stub = StubModel(zero_span_words)

    merged, report = fill_speech_gaps(
        stub, audio, words, language="hi", task="transcribe", prompt="",
        regions=regions
    )
    assert report["gaps_found"] == 1
    assert report["gaps_filled"] == 0
    assert report["gaps_skipped"] == 1
    assert len(merged) == 2


def test_fill_speech_gaps_spends_budget_on_largest_gap_first():
    # Three 1 s gaps come before one 6 s gap. With a 3 s budget, chronological
    # order fills the three small ones and leaves the 6 s hole empty. The
    # largest gap must win instead: a 6 s hole is the defect, a 1 s pause is not.
    words = [
        {"start": 0.0, "end": 1.0, "text": "w0"},
        {"start": 2.0, "end": 3.0, "text": "w1"},
        {"start": 4.0, "end": 5.0, "text": "w2"},
        {"start": 6.0, "end": 7.0, "text": "w3"},
        {"start": 13.0, "end": 14.0, "text": "w4"},
    ]
    regions = [(1.2, 1.9), (3.2, 3.9), (5.2, 5.9), (7.5, 12.5)]
    audio = np.zeros(16000 * 15, dtype=np.float32)
    # Slice-relative (0.3, 0.6): lands inside the first small gap and inside the
    # big gap, so one stub word is valid for whichever gap is retried.
    stub = StubModel([StubWord(0.3, 0.6, "rec", probability=0.9)])

    merged, report = fill_speech_gaps(
        stub, audio, words, language="hi", task="transcribe", prompt="",
        cap_s=3.0, regions=regions
    )
    assert report["gaps_found"] == 4
    assert report["gaps_filled"] == 0
    recovered = [w for w in merged if w["text"] == "rec"]
    assert len(recovered) == 1
    assert 7.0 <= recovered[0]["start"] <= 13.0, "budget went to a small gap, not the 6 s one"
    # Only the 6 s hole was attempted, and 0.3 s of it came back, so 5.7 s stays
    # reported as uncaptioned instead of being counted as recovered.
    assert report["skipped_seconds"] >= 5.5


def test_fill_speech_gaps_reports_skipped_seconds():
    # A skipped hole must be measurable, not just counted: coverage is reported,
    # so the seconds that were dropped have to be visible too.
    words = [
        {"start": 0.0, "end": 1.0, "text": "w0"},
        {"start": 5.0, "end": 6.0, "text": "w1"},
        {"start": 10.0, "end": 11.0, "text": "w2"},
    ]
    regions = [(1.5, 4.5), (6.5, 9.5)]
    audio = np.zeros(16000 * 12, dtype=np.float32)
    stub = StubModel([StubWord(0.3, 0.6, "rec", probability=0.9)])

    merged, report = fill_speech_gaps(
        stub, audio, words, language="hi", task="transcribe", prompt="",
        cap_s=4.0, regions=regions
    )
    assert report["gaps_skipped"] >= 1
    assert report["skipped_seconds"] >= 3.5


def test_fill_speech_gaps_edge_words_do_not_count_as_filled():
    # The real-file defect: a retry came back with words only at the padded edge of
    # the hole, the counter said "filled", and the burned caption still had 4.46 s
    # with nothing. A gap is closed by measuring the hole, and one failed attempt
    # gets a second, wider-slice attempt before it is written off.
    words = [
        {"start": 0.0, "end": 2.0, "text": "before"},
        {"start": 10.0, "end": 12.0, "text": "after"},
    ]
    regions = [(2.0, 10.0)]
    audio = np.zeros(16000 * 12, dtype=np.float32)
    edge_only = [StubWord(0.05, 0.30, "edge", probability=0.9)]
    covers_gap = [StubWord(2.2 + i, 3.2 + i, f"w{i}", probability=0.9) for i in range(7)]
    covers_gap.append(StubWord(9.2, 10.0, "end", probability=0.9))
    stub = StubModel(sequence=[edge_only, covers_gap])

    merged, report = fill_speech_gaps(
        stub, audio, words, language="hi", task="transcribe", prompt="",
        cap_s=30.0, regions=regions
    )
    assert stub.call_count == 2, "a hole left open by the first attempt must be retried"
    assert report["gaps_filled"] == 1
    assert report["seconds_recovered"] == 8.0
    assert report["skipped_seconds"] == 0.0


def test_fill_speech_gaps_rescue_drops_the_prompt():
    # On the real clip a 3.65 s stretch came back as one stretched token with the
    # prompt in place and decoded as real words without it. The rescue pass has to
    # try the unprompted decode before writing the hole off.
    words = [
        {"start": 0.0, "end": 2.0, "text": "before"},
        {"start": 10.0, "end": 12.0, "text": "after"},
    ]
    regions = [(2.0, 10.0)]
    audio = np.zeros(16000 * 200, dtype=np.float32)
    # Slice coords for the narrow rescue slice (1.85 .. 10.15).
    cover = [StubWord(0.3 + i, 1.3 + i, f"w{i}", probability=0.9) for i in range(7)]
    cover.append(StubWord(7.3, 8.2, "end", probability=0.9))
    stub = StubModel(sequence=[[], [], cover])

    merged, report = fill_speech_gaps(
        stub, audio, words, language="hi", task="transcribe", prompt="PROMPT",
        cap_s=30.0, regions=regions
    )
    assert report["gaps_filled"] == 1
    assert stub.prompts[-1] is None, "the second rescue round must drop the prompt"
    assert stub.prompts[0] == "PROMPT", "the first pass keeps the prompt"


def test_transcribe_words_measures_holes_after_sanitizing(monkeypatch):
    # A token whisper could not render is stripped when cards are built. If the gap
    # detector still sees it, it anchors a stretch that ends up with no caption and
    # the hole is never retried. Measured on the real clip: one such token inside a
    # 4.46 s hole was enough to ship it empty.
    import hinglish_upgrades as hu

    base = [
        StubWord(0.0, 1.0, "start"),
        StubWord(3.0, 3.1, "\ufffd"),
        StubWord(5.0, 6.0, "end"),
    ]
    model = StubModel(sequence=[base, [StubWord(2.0, 3.0, "recovered")]])
    monkeypatch.setattr(hu, "speech_regions", lambda audio, sampling_rate=16000: [(0.0, 10.0)])

    words, report = hu.transcribe_words(
        model, np.zeros(16000 * 10, dtype=np.float32), language="hi", topic_hint=""
    )
    texts = [w["text"] for w in words]
    assert "\ufffd" not in texts
    assert "recovered" in texts, "the junk token hid a real hole from the retry pass"
    assert report["gaps_found"] >= 1
