"""Motion modes: static, reveal and punch must be distinct emitters.

`word-pop` stays exactly as it was (it is what Honey Punch and Recess ship
today); the new modes are additive so no existing preset changes frame.
"""

import re

from karaoke_ass import generate_karaoke_ass


def _cards():
    return [{
        "start": 0.0,
        "end": 2.4,
        "original_text": "",
        "hinglish_text": "ek do teen chaar",
        "words": [
            {"start": 0.0, "end": 0.6, "word": "", "hinglish": "ek"},
            {"start": 0.6, "end": 1.2, "word": "", "hinglish": "do"},
            {"start": 1.2, "end": 1.8, "word": "", "hinglish": "teen"},
            {"start": 1.8, "end": 2.4, "word": "", "hinglish": "chaar"},
        ],
    }]


def _style(**extra):
    base = {
        "id": "probe",
        "name": "Probe",
        "font": "Impact",
        "font_size": 68,
        "uppercase": True,
        "base_color": "#FFFFFF",
        "highlight_color": "#FFC700",
        "outline_color": "#000000",
        "outline_width": 5,
        "shadow": 2,
        "margin_v": 240,
        "active_scale": 150,
        "accent_scale": 100,
        "accent_size_scale": 100,
    }
    base.update(extra)
    return base


def _dialogues(ass):
    return [l for l in ass.splitlines() if l.startswith("Dialogue:")]


def _sizes(line):
    return [int(m) for m in re.findall(r"\\fs(\d+)", line)]


def test_static_emits_one_event_with_no_karaoke_tags():
    ass = generate_karaoke_ass(_cards(), style=_style(motion="static"))
    dialogues = _dialogues(ass)
    assert len(dialogues) == 1
    assert r"\k" not in dialogues[0]
    for word in ("ek", "do", "teen", "chaar"):
        assert word.upper() in dialogues[0]


def test_reveal_keeps_every_word_the_same_size():
    ass = generate_karaoke_ass(_cards(), style=_style(motion="reveal", accent_scale=180))
    sizes = _sizes(_dialogues(ass)[0])
    assert len(sizes) == 4
    assert len(set(sizes)) == 1, sizes


def test_punch_scales_only_the_active_word():
    ass = generate_karaoke_ass(_cards(), style=_style(motion="punch", active_scale=150))
    sizes = _sizes(_dialogues(ass)[0])
    assert len(sizes) == 4
    assert sizes[0] > sizes[1], sizes
    assert len(set(sizes[1:])) == 1, sizes


def test_word_pop_still_drives_from_word_flags_not_the_active_word():
    """Honey Punch and Recess ship `word-pop`; its frames must not move."""
    ass = generate_karaoke_ass(_cards(), style=_style(motion="word-pop", accent_scale=180))
    dialogues = _dialogues(ass)
    first = _sizes(dialogues[0])
    later = _sizes(dialogues[40])
    assert len(set(first)) == 2, first
    # The big word is decided by content, so it must stay the same word as the
    # active index advances. Scaling the active word would move it.
    assert first.index(max(first)) == later.index(max(later))
