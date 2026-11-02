"""Composable styles: a look and a motion, not sixteen flattened tiles.

The panel exposes three independent axes. This file pins the first two: eight
looks (type + paint) and five motions. Every pair must compose into a style the
emitter can burn, and a look paired with the motion it already shipped must
reproduce that preset exactly, so splitting the data moves no frame.
"""

import re

from caption_styles import (
    ALLOWED_FONTS,
    BUBBLE_MOTION,
    LOOKS,
    MOTION_KEYS,
    MOTIONS,
    PRESETS,
    compose_style,
    resolve_style,
)
from karaoke_ass import generate_karaoke_ass


LOOK_IDS = ("techwave", "hormozi", "vox", "cyber", "editorial", "buzz", "blackout", "neon")

# What each pickable motion resolves to in the schema. `karaoke` is the classic
# one-card path, which the schema spells `none`. `word-pop` is deliberately not
# here: it is the legacy emitter Honey Punch and Recess ship, not a choice.
MOTION_TO_SCHEMA = {
    "static": "static",
    "karaoke": "none",
    "reveal": "reveal",
    "punch": "punch",
    "bubble": "bubble",
}


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


def _dialogues(ass):
    return [line for line in ass.splitlines() if line.startswith("Dialogue:")]


def test_the_eight_looks_are_declared_in_panel_order():
    assert tuple(LOOKS) == LOOK_IDS


def test_a_look_carries_type_and_paint_but_no_motion():
    motion_keys = {"motion", "pill", "kinetic_grouping", "kinetic_layout", "reveal_fade_ms"}
    for look_id, look in LOOKS.items():
        assert not motion_keys & set(look), look_id
        assert look["font"] in ALLOWED_FONTS, look_id
        assert re.match(r"^#[0-9A-F]{6}$", look["base_color"]), look_id
        assert re.match(r"^#[0-9A-F]{6}$", look["highlight_color"]), look_id


def test_the_five_motions_are_the_only_pickable_ones():
    assert MOTION_KEYS == ("static", "karaoke", "reveal", "punch", "bubble")
    assert tuple(MOTIONS) == MOTION_KEYS
    assert "word-pop" not in MOTION_KEYS


def test_each_look_paired_with_its_shipped_motion_reproduces_the_preset():
    # Every one of the eight looks ships today as a karaoke preset. Composing
    # it must hand back the exact same resolved style, not a near miss.
    for look_id in LOOK_IDS:
        assert compose_style(look_id, "karaoke") == resolve_style(look_id), look_id


def test_every_look_and_motion_pair_composes_to_a_burnable_style():
    for look_id in LOOK_IDS:
        for motion_id in MOTION_KEYS:
            style = compose_style(look_id, motion_id)
            assert style["font"] in ALLOWED_FONTS, (look_id, motion_id)
            assert style["motion"] == MOTION_TO_SCHEMA[motion_id], (look_id, motion_id)
            ass = generate_karaoke_ass(_cards(), style=style)
            assert _dialogues(ass), (look_id, motion_id)


def test_composing_is_stable_through_a_second_resolve():
    # The API and the browser both round-trip a style through resolve_style.
    for motion_id in MOTION_KEYS:
        once = compose_style("neon", motion_id)
        assert resolve_style(once) == once, motion_id


def test_bubble_takes_its_pill_geometry_from_the_motion_and_its_colour_from_the_look():
    style = compose_style("cyber", "bubble")
    assert style["pill"] is True
    assert style["highlight_color"] == LOOKS["cyber"]["highlight_color"]
    assert style["pill_gradient_start"] == LOOKS["cyber"]["highlight_color"]
    assert style["pill_gradient_end"] == LOOKS["cyber"]["highlight_color"]
    for key, value in BUBBLE_MOTION.items():
        assert style[key] == value, key
    # The pill belongs to the motion: no other motion may turn it on.
    for motion_id in ("static", "karaoke", "reveal", "punch"):
        assert compose_style("cyber", motion_id)["pill"] is False, motion_id


def test_overrides_win_over_both_axes():
    style = compose_style("hormozi", "punch", font_size=90, highlight_color="#00FF00")
    assert style["font_size"] == 90
    assert style["highlight_color"] == "#00FF00"
    assert style["font"] == LOOKS["hormozi"]["font"]
    assert style["motion"] == "punch"


def test_unknown_ids_fall_back_to_the_default_look_and_karaoke():
    style = compose_style("no-such-look", "no-such-motion")
    assert style == compose_style("techwave", "karaoke")
    assert style["id"] == PRESETS["techwave"]["id"]
