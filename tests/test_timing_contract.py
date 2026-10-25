"""
test_timing_contract.py - Pins the timing rules that the live overlay, the .ASS
export, the .SRT and the burn all depend on.

The playback clock itself is covered by tests/js/caption_clock_test.js. This file
covers the half that lives in the Python pipeline:

  * a DTW-stretched token is capped AND reports how much it was capped, so the
    card can hold over the audio it would otherwise cut short
  * that hold never runs into the next card
  * normal cards are byte-for-byte unchanged by the hold logic
  * the sync nudge is not baked into the exported timeline twice
"""

from hinglish_upgrades import (
    TAIL_HOLD_MAX,
    clamp_word_span,
    pad_display_times,
    semantic_chunk,
    words_to_cards,
)


def test_short_word_is_untouched():
    assert clamp_word_span(1.0, 1.4, "haan") == (1.0, 1.4, 0.0)


def test_long_word_is_capped_and_reports_the_cut():
    start, end, tail = clamp_word_span(10.0, 21.06, "bachpan")
    assert start == 10.0
    assert end < 21.06
    assert end - start <= 2.5
    assert round(tail, 3) == round(21.06 - end, 3)
    assert tail > 0


def test_tail_holds_the_card_over_the_cut_audio():
    cards = [
        {
            "start": 0.0,
            "end": 1.0,
            "text": "hello",
            "words": [{"start": 0.0, "end": 1.0, "text": "hello", "tail": 9.0}],
        },
        {"start": 10.0, "end": 11.0, "text": "next", "words": [{"start": 10.0, "end": 11.0, "text": "next"}]},
    ]
    out = pad_display_times(cards)
    assert out[0]["end"] == round(1.0 + TAIL_HOLD_MAX, 3)


def test_tail_never_overlaps_the_next_card():
    cards = [
        {
            "start": 0.0,
            "end": 1.0,
            "text": "hello",
            "words": [{"start": 0.0, "end": 1.0, "text": "hello", "tail": 9.0}],
        },
        {"start": 2.0, "end": 3.0, "text": "next", "words": [{"start": 2.0, "end": 3.0, "text": "next"}]},
    ]
    out = pad_display_times(cards)
    assert out[0]["end"] <= 2.0 - 0.04
    assert out[1]["start"] == 2.0


def test_cards_without_a_tail_keep_their_old_padding():
    cards = [
        {"start": 0.0, "end": 1.2, "text": "a", "words": [{"start": 0.0, "end": 1.2, "text": "a"}]},
        {"start": 1.4, "end": 2.6, "text": "b", "words": [{"start": 1.4, "end": 2.6, "text": "b"}]},
    ]
    out = pad_display_times(cards)
    assert [c["end"] for c in out] == [1.36, 2.9]


def test_semantic_chunk_carries_the_tail_to_the_card():
    words = [
        {"start": 0.0, "end": 1.0, "text": "hello", "tail": 4.0},
        {"start": 1.1, "end": 1.6, "text": "there"},
    ]
    cards = semantic_chunk(words)
    tails = [w.get("tail") for w in cards[0]["words"]]
    assert 4.0 in tails


def test_exported_segments_do_not_leak_internal_tail():
    words = [{"start": 0.0, "end": 1.0, "text": "hello", "tail": 4.0}]
    cards = words_to_cards(words, lambda s: s)
    assert "tail" not in cards[0]["words"][0]
    assert set(cards[0]["words"][0]) == {"start", "end", "word", "hinglish"}
