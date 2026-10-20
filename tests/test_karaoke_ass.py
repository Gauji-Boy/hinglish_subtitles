"""
test_karaoke_ass.py - Automated unit tests for Karaoke / Animated Word Subtitles (.ass) generator and API.
"""

import pytest
from karaoke_ass import format_ass_time, escape_ass_text, generate_karaoke_ass


def test_format_ass_time():
    assert format_ass_time(0.0) == "0:00:00.00"
    assert format_ass_time(1.234) == "0:00:01.23"
    assert format_ass_time(65.789) == "0:01:05.79"
    assert format_ass_time(3661.05) == "1:01:01.05"
    assert format_ass_time(-5.0) == "0:00:00.00"


def test_escape_ass_text():
    assert escape_ass_text("Hello {World}") == "Hello (World)"
    assert escape_ass_text("Simple text") == "Simple text"


def test_generate_karaoke_ass_basic():
    sample_cards = [
        {
            "start": 1.0,
            "end": 3.5,
            "original_text": "नमस्ते दोस्तों",
            "hinglish_text": "Namaste dosto",
            "words": [
                {"start": 1.0, "end": 2.0, "word": "नमस्ते", "hinglish": "Namaste"},
                {"start": 2.1, "end": 3.2, "word": "दोस्तों", "hinglish": "dosto"}
            ]
        }
    ]

    ass = generate_karaoke_ass(sample_cards, script_title="Test Reel")
    assert "[Script Info]" in ass
    assert "[V4+ Styles]" in ass
    assert "[Events]" in ass
    assert "Style: HormoziYellow" in ass
    assert "Dialogue: 0,0:00:01.00,0:00:03.50,HormoziYellow" in ass
    assert r"{\k100}Namaste" in ass
    assert r"{\k110}dosto" in ass


def test_generate_karaoke_ass_fallback_without_words():
    sample_cards = [
        {
            "start": 0.5,
            "end": 2.0,
            "original_text": "बिना शब्द टोकन",
            "hinglish_text": "Bina shabd token",
            "words": []
        }
    ]

    ass = generate_karaoke_ass(sample_cards)
    assert "Dialogue: 0,0:00:00.50,0:00:02.00,HormoziYellow,,0,0,0,,Bina shabd token" in ass


def test_server_export_ass_endpoint():
    from fastapi.testclient import TestClient
    from server import app

    client = TestClient(app)
    payload = {
        "title": "API Test Karaoke",
        "segments": [
            {
                "start": 0.0,
                "end": 2.5,
                "hinglish_text": "Quick test caption",
                "words": [
                    {"start": 0.0, "end": 0.8, "hinglish": "Quick"},
                    {"start": 0.9, "end": 1.5, "hinglish": "test"},
                    {"start": 1.6, "end": 2.3, "hinglish": "caption"}
                ]
            }
        ]
    }

    res = client.post("/api/export/ass", json=payload)
    assert res.status_code == 200
    assert "text/x-ssa" in res.headers["content-type"]
    assert "attachment; filename=\"karaoke_subtitles.ass\"" in res.headers["content-disposition"]
    body = res.text
    assert "[Script Info]" in body
    assert r"{\k80}Quick" in body
