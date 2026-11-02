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


def test_bubble_puts_a_pill_behind_the_spoken_word():
    """`bubble` is the recess emitter: one pill per word, flat type."""
    ass = generate_karaoke_ass(_cards(), style=_style(motion="bubble"))
    dialogues = _dialogues(ass)
    pills = [d for d in dialogues if r"\p1" in d]
    words = [d for d in dialogues if "RecessKinetic" in d]
    # A gradient pill is drawn in slices, so count the words it starts on
    # rather than the drawings.
    assert len({d.split(",")[1] for d in pills}) == 4
    assert len(words) == 4, len(words)
    sizes = _sizes(words[0])
    assert len(set(sizes)) == 1, sizes


def test_bubble_does_not_need_the_pill_flag_in_the_style():
    """A style that only says `motion: bubble` must still get its pill."""
    ass = generate_karaoke_ass(_cards(), style=_style(motion="bubble", pill=False))
    assert r"\p1" in ass


def test_bubble_draws_at_the_kinetic_em():
    """Bubble is a motion, so switching to it must not resize the type.

    The recess emitter halves portrait em for its own preset; bubble carries
    the kinetic em the other motion modes draw at.
    """
    from karaoke_ass import _KINETIC_ASS_FONT_SCALE, _kinetic_base_size

    ass = generate_karaoke_ass(
        _cards(), style=_style(motion="bubble"), play_res_x=1080, play_res_y=1920
    )
    words = [d for d in _dialogues(ass) if "RecessKinetic" in d]
    assert words, "no bubble word events"
    size = _sizes(words[0])[0]
    expected = _kinetic_base_size(1920, 68, 1080) * _KINETIC_ASS_FONT_SCALE
    assert abs(size - expected) <= 1.0, (size, expected)


# Rendered/Pillow size ratio measured by burning "EK" at \fs 108 in 1080x1920
# and comparing the white ink box with Pillow's at the same size. libass fits
# the face's ascent+descent into \fs, so the ratio is a property of the font.
MEASURED_FONT_SCALES = {
    "Impact": 0.800,
    "Arial Black": 0.702,
    "Segoe UI": 0.725,
    "Arial": 0.882,
    "Verdana": 0.811,
    "Trebuchet MS": 0.842,
    "Georgia": 0.869,
    "Consolas": 0.829,
}


def test_bubble_measures_the_looks_own_face():
    """A look's font renders at its own scale, not Recess's Arial Black one.

    Bubble has to place words for whatever face the look carries, so it reads
    the font's metrics. Without this a narrow face overlaps its own words.
    """
    from karaoke_ass import _rendered_font_scale

    for font, measured in MEASURED_FONT_SCALES.items():
        scale = _rendered_font_scale(font)
        assert abs(scale - measured) <= measured * 0.04, (font, scale, measured)


def test_bubble_layout_ink_matches_the_burn():
    """The layout's ink estimate must land on the burned ink, within 3 px.

    Burned "EK" in Impact at \fs 108 measured 72.4 px wide once the style's
    90.5% condensation is applied.
    """
    from karaoke_ass import _recess_layout, _recess_metrics

    phrase = [{"text": "EK", "start": 0.0, "end": 0.5}]
    placed = _recess_layout(
        phrase,
        [1.0],
        108.0,
        993.6,
        "Impact",
        540.0,
        806.0,
        _recess_metrics("Impact"),
    )
    assert abs(placed[0]["ink"] - 72.4) <= 3.0, placed[0]["ink"]
