"""Tests for caption style schema, presets, colour conversion, and aspects."""

import pytest

from caption_styles import (
    ALLOWED_FONTS,
    PRESETS,
    aspect_profile,
    hex_to_ass,
    list_presets,
    resolve_style,
)


def test_hex_to_ass_rgb_and_alpha():
    assert hex_to_ass("#FFC700") == "&H0000C7FF"
    assert hex_to_ass("#FFFFFF") == "&H00FFFFFF"
    assert hex_to_ass("#00000080") == "&H7F000000"
    assert hex_to_ass("#38BDF8") == "&H00F8BD38"


def test_hex_to_ass_falls_back_on_garbage():
    assert hex_to_ass("yellow", "&H00FFFFFF") == "&H00FFFFFF"
    assert hex_to_ass("", "&H00112233") == "&H00112233"


def test_every_preset_normalizes():
    presets = list_presets()
    assert len(presets) == 16
    assert [p["id"] for p in presets] == [
        "hormozi", "vox", "cyber", "blackout", "editorial",
        "buzz", "medusa", "cartwheel", "heat", "neon", "magazine",
        "techwave", "minima", "honeypunch", "recess", "blank",
    ]
    assert {p["id"] for p in presets} == set(PRESETS)
    for preset in presets:
        assert preset["font"] in ALLOWED_FONTS
        assert 24 <= preset["font_size"] <= 140
        assert preset["base_color"].startswith("#")
        assert preset["highlight_color"].startswith("#")
        assert preset["alignment"] in (2, 5, 8)


def test_template_lookalike_presets_have_expected_looks():
    buzz = resolve_style("buzz")
    assert buzz["highlight_color"] == "#C0B0F0"
    assert buzz["outline_width"] == 0

    medusa = resolve_style("medusa")
    assert medusa["box"] is True
    assert medusa["highlight_color"] == "#3BE80D"

    cartwheel = resolve_style("cartwheel")
    assert cartwheel["box"] is True
    assert cartwheel["highlight_color"] == "#8A16F0"

    heat = resolve_style("heat")
    assert heat["uppercase"] is False
    assert heat["base_color"] == "#FF1A1A"

    assert resolve_style("neon")["highlight_color"] == "#F08AB5"
    assert resolve_style("magazine")["highlight_color"] == "#F5E63D"
    assert resolve_style("techwave")["outline_width"] == 6
    assert resolve_style("minima")["shadow"] == 0


def test_resolve_style_by_id_uses_preset_values():
    style = resolve_style("vox")
    assert style["id"] == "vox"
    assert style["font"] == "Segoe UI"
    assert style["uppercase"] is False


def test_custom_style_overlays_and_keeps_id():
    style = resolve_style({"id": "custom", "name": "Mine", "font_size": 999, "highlight_color": "not-a-colour"})
    assert style["id"] == "custom"
    assert style["name"] == "Mine"
    assert style["font_size"] == 140
    assert style["highlight_color"] == "#FFC700"


def test_unknown_id_and_font_fall_back():
    style = resolve_style({"id": "nope", "font": "Comic Sans"})
    assert style["id"] == "hormozi"
    assert style["font"] == "Segoe UI"


def test_numeric_and_boolean_coercion():
    style = resolve_style({"id": "custom", "font_size": "71.6", "uppercase": "true", "box": "yes", "margin_v": -50})
    assert style["font_size"] == 72
    assert style["uppercase"] is True
    assert style["box"] is True
    assert style["margin_v"] == 0


def test_alignment_is_restricted_to_supported_positions():
    assert resolve_style({"id": "custom", "alignment": 7})["alignment"] == 2
    assert resolve_style({"id": "custom", "alignment": 8})["alignment"] == 8
    assert resolve_style({"id": "custom", "alignment": 5})["alignment"] == 5


def test_aspect_profiles_and_aliases():
    portrait = aspect_profile("9:16")
    landscape = aspect_profile("landscape")
    square = aspect_profile("square")
    assert (portrait["play_res_x"], portrait["play_res_y"]) == (1080, 1920)
    assert (landscape["play_res_x"], landscape["play_res_y"]) == (1920, 1080)
    assert (square["play_res_x"], square["play_res_y"]) == (1080, 1080)
    assert aspect_profile("nonsense")["play_res_x"] == 1080

def test_honeypunch_is_a_real_kinetic_word_pop_style():
    style = resolve_style("honeypunch")
    assert style["motion"] == "word-pop"
    assert style["font"] == "Arial"
    assert style["font_size"] == 128
    assert style["active_scale"] == 150
    assert style["accent_scale"] == 150
    assert style["anchor_y"] == 22
    assert style["max_width"] == 55
    assert style["phrase_gap_ms"] == 650
    assert style["pop_ms"] == 0
    assert style["settle_ms"] == 0
    assert style["accent_mode"] == "content"
    assert style["kinetic_layout"] == "alternate"
    assert style["max_words_per_phrase"] == 10


def test_kinetic_fields_are_normalized_and_clamped():
    style = resolve_style({
        "id": "custom",
        "motion": "WORD-POP",
        "active_scale": 999,
        "accent_scale": 1,
        "anchor_y": -20,
        "max_width": 5,
        "phrase_gap_ms": 9000,
        "pop_ms": -5,
        "settle_ms": 5000,
        "accent_mode": "everything",
        "kinetic_layout": "diagonal",
    })
    assert style["motion"] == "word-pop"
    assert style["active_scale"] == 220
    assert style["accent_scale"] == 100
    assert style["anchor_y"] == 0
    assert style["max_width"] == 35
    assert style["phrase_gap_ms"] == 3000
    assert style["pop_ms"] == 0
    assert style["settle_ms"] == 1000
    assert style["accent_mode"] == "content"
    assert style["kinetic_layout"] == "center"


def test_recess_preset_encodes_the_measured_reference():
    style = resolve_style("recess")
    assert style["motion"] == "word-pop"
    assert style["font"] == "Arial Black"
    assert style["uppercase"] is True
    assert style["font_size"] == 136
    assert style["kinetic_size_scale"] == pytest.approx(2.14)
    assert style["kinetic_layout"] == "middle"
    assert style["kinetic_grouping"] == "punch"
    assert style["anchor_y"] == 50
    assert style["max_width"] == 82
    assert style["active_scale"] == 100
    assert style["accent_scale"] == 203
    assert style["outline_width"] == 0
    assert style["shadow"] == 0
    assert style["pill"] is True
    assert style["pill_gradient_start"] == "#D2E860"
    assert style["pill_gradient_end"] == "#A793FF"
    assert style["pill_pad_x"] == pytest.approx(0.16)
    assert style["pill_pad_y"] == pytest.approx(0.32)
    assert style["pill_radius"] == pytest.approx(0.26)
    assert style["pill_alpha"] == pytest.approx(0.58)
    assert style["pill_fade_ms"] == 65
    assert style["pill_slide_ms"] == 130
    assert style["reveal_fade_ms"] == 65
    assert style["reveal_spring_ms"] == 130
    assert style["reveal_spring_scale"] == pytest.approx(1.10)


def test_recess_fields_are_normalized_and_clamped():
    style = resolve_style({
        "id": "recess",
        "pill": "yes",
        "pill_gradient_start": "lime",
        "pill_gradient_end": "#123456",
        "pill_pad_x": -1,
        "pill_pad_y": 9,
        "pill_radius": 2,
        "pill_alpha": -3,
        "pill_fade_ms": 9999,
        "pill_slide_ms": -5,
        "reveal_fade_ms": 9999,
        "reveal_spring_ms": -5,
        "reveal_spring_scale": 5,
        "kinetic_size_scale": 99,
        "kinetic_grouping": "diagonal",
    })
    assert style["pill"] is True
    assert style["pill_gradient_start"] == "#FFFFFF"  # invalid hex falls back
    assert style["pill_gradient_end"] == "#123456"
    assert style["pill_pad_x"] == 0.0
    assert style["pill_pad_y"] == 1.0
    assert style["pill_radius"] == 1.0
    assert style["pill_alpha"] == 0.0
    assert style["pill_fade_ms"] == 2000
    assert style["pill_slide_ms"] == 0
    assert style["reveal_fade_ms"] == 2000
    assert style["reveal_spring_ms"] == 0
    assert style["reveal_spring_scale"] == 2.0
    assert style["kinetic_size_scale"] == 2.5
    assert style["kinetic_grouping"] == "flow"


def test_accent_scale_clamp_now_reaches_203():
    assert resolve_style({"id": "custom", "accent_scale": 203})["accent_scale"] == 203
    assert resolve_style({"id": "custom", "accent_scale": 999})["accent_scale"] == 210


def test_existing_presets_keep_pill_and_reveal_off():
    for preset in list_presets():
        if preset["id"] == "recess":
            continue
        assert preset["pill"] is False
        # Honey Punch is the only preset that holds a whole sentence as one
        # poster; every other style keeps the per-card flow it shipped with.
        expected_grouping = "poster" if preset["id"] == "honeypunch" else "flow"
        assert preset["kinetic_grouping"] == expected_grouping
        assert preset["reveal_fade_ms"] == 0
        assert preset["reveal_spring_ms"] == 0
        assert preset["kinetic_size_scale"] == 1.0

