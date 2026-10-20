"""
test_video_burner.py - Automated tests for FFmpeg video burning engine and server endpoints.
"""

import os
import pytest
from video_burner import get_available_h264_encoder, burn_subtitles_to_video
from karaoke_ass import generate_karaoke_ass


def test_get_available_h264_encoder():
    enc, args = get_available_h264_encoder()
    assert enc in ("h264_mf", "libx264")
    assert isinstance(args, list)
    assert len(args) >= 2


def test_burn_subtitles_to_video_traffic_sample():
    sample_video = "static/samples/traffic.mp4"
    if not os.path.exists(sample_video):
        pytest.skip("Sample video traffic.mp4 not found")

    # Generate small ASS test file
    sample_cards = [
        {
            "start": 0.0,
            "end": 2.0,
            "original_text": "Traffic test",
            "hinglish_text": "Traffic test",
            "words": [
                {"start": 0.0, "end": 1.0, "hinglish": "Traffic"},
                {"start": 1.0, "end": 2.0, "hinglish": "test"}
            ]
        }
    ]
    ass_text = generate_karaoke_ass(sample_cards)
    temp_ass = "test_pytest_burn.ass"
    out_mp4 = "test_pytest_burned.mp4"

    try:
        with open(temp_ass, "w", encoding="utf-8") as f:
            f.write(ass_text)

        res = burn_subtitles_to_video(sample_video, temp_ass, out_mp4, timeout_sec=60)
        assert res["success"] is True
        assert os.path.exists(out_mp4)
        assert res["file_size"] > 100000

    finally:
        for p in [temp_ass, out_mp4]:
            if os.path.exists(p):
                os.remove(p)


def test_server_burn_video_endpoint():
    from fastapi.testclient import TestClient
    from server import app

    sample_video = "static/samples/traffic.mp4"
    if not os.path.exists(sample_video):
        pytest.skip("Sample video traffic.mp4 not found")

    client = TestClient(app)

    # Subtitle ASS string
    ass_text = """[Script Info]
Title: Pytest
ScriptType: v4.00+
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,36,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,2,20,20,40,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,{\\k50}Hello {\\k50}World
"""

    with open(sample_video, "rb") as vf:
        files = {"video": ("traffic.mp4", vf, "video/mp4")}
        data = {"subtitles": ass_text, "format_type": "ass"}

        res = client.post("/api/export/burn-video", files=files, data=data)

    assert res.status_code == 200
    assert "video/mp4" in res.headers["content-type"]
    assert "traffic_subtitled.mp4" in res.headers["content-disposition"]
    assert len(res.content) > 100000
