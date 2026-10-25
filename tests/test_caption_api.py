"""API tests for caption presets, style passthrough, and preference persistence."""

import json

from fastapi.testclient import TestClient

import server
from caption_styles import resolve_style

client = TestClient(server.app)

CARDS = [
    {
        "start": 0.0,
        "end": 2.0,
        "hinglish_text": "API style test",
        "words": [
            {"start": 0.0, "end": 1.0, "hinglish": "API"},
            {"start": 1.0, "end": 2.0, "hinglish": "style"},
        ],
    }
]


def test_caption_styles_endpoint_lists_presets():
    res = client.get("/api/caption-styles")
    assert res.status_code == 200
    data = res.json()
    assert data["default"] == "hormozi"
    assert [p["id"] for p in data["presets"]] == [
        "hormozi", "vox", "cyber", "blackout", "editorial",
        "buzz", "medusa", "cartwheel", "heat", "neon", "magazine",
        "techwave", "minima", "honeypunch", "recess", "blank",
    ]
    assert "custom" in data
    assert "Impact" in data["fonts"]


def test_export_ass_accepts_style_and_aspect():
    res = client.post("/api/export/ass", json={
        "segments": CARDS,
        "title": "Styled",
        "style": "vox",
        "aspect": "16:9",
    })
    assert res.status_code == 200
    assert "PlayResX: 1920" in res.text
    assert "PlayResY: 1080" in res.text
    assert "Segoe UI" in res.text


def test_export_ass_unknown_style_falls_back():
    res = client.post("/api/export/ass", json={
        "segments": CARDS,
        "style": "does-not-exist",
    })
    assert res.status_code == 200
    assert "Style: HormoziYellow" in res.text


def test_export_ass_uses_template_lookalike_style():
    res = client.post("/api/export/ass", json={
        "segments": CARDS,
        "style": "medusa",
    })
    assert res.status_code == 200
    assert "Arial Black" in res.text
    assert "&H000DE83B" in res.text
    style_line = next(line for line in res.text.splitlines() if line.startswith("Style: CaptionStyle"))
    fields = style_line.split(",")
    assert fields[15] == "3"  # BorderStyle: opaque box


def test_preferences_round_trip_custom_style(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "CONFIG_PATH", str(tmp_path / "launch_config.json"))
    style = resolve_style({"id": "custom", "name": "Mine", "highlight_color": "#00FF00"})

    saved = client.post("/api/config/preferences", data={"caption_style": json.dumps(style)})
    assert saved.status_code == 200
    assert saved.json()["preferences"]["caption_style"]["id"] == "custom"

    fetched = client.get("/api/config/preferences")
    assert fetched.status_code == 200
    caption_style = fetched.json()["caption_style"]
    assert caption_style["id"] == "custom"
    assert caption_style["name"] == "Mine"
    assert caption_style["highlight_color"] == "#00FF00"


def test_preferences_accepts_style_id_string(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "CONFIG_PATH", str(tmp_path / "launch_config.json"))
    saved = client.post("/api/config/preferences", data={"caption_style": "cyber"})
    assert saved.status_code == 200
    assert saved.json()["preferences"]["caption_style"]["id"] == "cyber"


def test_custom_style_survives_switching_to_a_preset(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "CONFIG_PATH", str(tmp_path / "launch_config.json"))
    style = resolve_style({"id": "custom", "name": "Mine", "font": "Georgia"})
    client.post("/api/config/preferences", data={"caption_style": json.dumps(style)})
    client.post("/api/config/preferences", data={"caption_style": "vox"})

    prefs = client.get("/api/config/preferences").json()
    assert prefs["caption_style"]["id"] == "vox"

    styles = client.get("/api/caption-styles").json()
    assert styles["custom"]["id"] == "custom"
    assert styles["custom"]["font"] == "Georgia"


def test_preferences_preserve_other_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "CONFIG_PATH", str(tmp_path / "launch_config.json"))
    client.post("/api/config/preferences", data={"selected_pacing": "long"})
    client.post("/api/config/preferences", data={"caption_style": "vox"})
    prefs = client.get("/api/config/preferences").json()
    assert prefs["selected_pacing"] == "long"
    assert prefs["caption_style"]["id"] == "vox"

def test_caption_styles_endpoint_exposes_kinetic_honeypunch():
    data = client.get("/api/caption-styles").json()
    style = next(p for p in data["presets"] if p["id"] == "honeypunch")
    assert style["motion"] == "word-pop"
    assert style["font"] == "Arial"
    assert style["active_scale"] == 150
    assert style["accent_scale"] == 150
    assert style["anchor_y"] == 22
    assert style["kinetic_layout"] == "alternate"


def test_export_ass_uses_kinetic_word_pop():
    segments = [{
        "start": 0.0,
        "end": 3.0,
        "hinglish_text": "Hey did you hear about the bakery",
        "words": [
            {"start": 0.1, "end": 0.5, "hinglish": "Hey,"},
            {"start": 0.9, "end": 1.1, "hinglish": "did"},
            {"start": 1.1, "end": 1.3, "hinglish": "you"},
            {"start": 1.3, "end": 1.7, "hinglish": "hear"},
            {"start": 1.7, "end": 2.0, "hinglish": "about"},
            {"start": 2.0, "end": 2.3, "hinglish": "the"},
            {"start": 2.3, "end": 2.9, "hinglish": "bakery"},
        ],
    }]
    res = client.post("/api/export/ass", json={
        "segments": segments,
        "title": "Kinetic",
        "style": "honeypunch",
        "aspect": "16:9",
    })
    assert res.status_code == 200
    assert "HoneyPunchKinetic" in res.text
    assert r"\an9" in res.text
    assert r"\fs" in res.text
    assert r"\k" not in res.text
    assert r"Hey,\N" in res.text

