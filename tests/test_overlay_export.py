"""Tests for the transparent alpha overlay renderer.

The pure tests describe the geometry rules; the render tests prove the alpha
channel on a real 1 s file, because a qtrle .mov that is silently opaque looks
fine to every unit test that only checks the path exists.
"""

import json
import os
import shutil
import subprocess
import types

import pytest

import overlay_export as ov

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not on PATH")

NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

ASS_TEXT = """[Script Info]
ScriptType: v4.00+
PlayResX: 320
PlayResY: 240

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,40,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:00.40,Default,,0,0,0,,HELLO
"""


def _ffprobe_json(path):
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        creationflags=NO_WINDOW,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _alpha_frame(path, width, height, seek=0.0):
    """First alpha plane as raw gray bytes, so coverage can be measured exactly."""
    cmd = ["ffmpeg", "-v", "error", "-ss", str(seek), "-i", str(path),
           "-frames:v", "1", "-vf", "alphaextract", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=NO_WINDOW)
    assert proc.returncode == 0, proc.stderr[-300:]
    assert len(proc.stdout) == width * height
    return proc.stdout


@pytest.fixture(scope="module")
def source_clip(tmp_path_factory):
    """A 1 s 320x240 30 fps clip to probe and render against."""
    path = tmp_path_factory.mktemp("ovl") / "source.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
         "-i", "color=c=black:s=320x240:r=30:d=1", "-c:v", "mpeg4", str(path)],
        check=True, creationflags=NO_WINDOW,
    )
    return str(path)


@pytest.fixture(scope="module")
def subtitle_file(tmp_path_factory):
    path = tmp_path_factory.mktemp("ovl_sub") / "sub.ass"
    path.write_text(ASS_TEXT, encoding="utf-8")
    return str(path)


# --- geometry rules (no media file needed) ---------------------------------

def test_parse_frame_rate_reads_rationals():
    assert ov.parse_frame_rate("30000/1001")["value"] == pytest.approx(29.97, abs=0.005)
    assert ov.parse_frame_rate("25")["rational"] == "25"
    assert ov.parse_frame_rate("0/0") is None
    assert ov.parse_frame_rate("") is None
    assert ov.parse_frame_rate(None) is None


def test_aspect_matches_the_browser_thresholds():
    assert ov.aspect_for_size(1080, 1920) == "9:16"
    assert ov.aspect_for_size(1080, 1350) == "9:16"
    assert ov.aspect_for_size(1920, 1080) == "16:9"
    assert ov.aspect_for_size(1080, 1080) == "1:1"
    assert ov.aspect_for_size(1000, 1000) == "1:1"


@pytest.mark.parametrize("rotation", [90, -90, 270])
def test_quarter_turn_swaps_display_size(rotation):
    geo = ov.geometry_from_probe({
        "streams": [{
            "codec_type": "video", "width": 1920, "height": 1080,
            "avg_frame_rate": "30/1",
            "side_data_list": [{"rotation": rotation}],
        }],
        "format": {"duration": "2.0"},
    })
    assert geo["ok"] is True
    assert (geo["width"], geo["height"]) == (1080, 1920)
    assert geo["aspect"] == "9:16"


@pytest.mark.parametrize("rotation", [0, 180, -180])
def test_straight_rotation_keeps_size(rotation):
    geo = ov.geometry_from_probe({
        "streams": [{
            "codec_type": "video", "width": 1080, "height": 1920,
            "avg_frame_rate": "30/1",
            "side_data_list": [{"rotation": rotation}],
        }],
        "format": {"duration": "2.0"},
    })
    assert (geo["width"], geo["height"]) == (1080, 1920)


def test_rotate_tag_is_used_when_side_data_is_absent():
    geo = ov.geometry_from_probe({
        "streams": [{
            "codec_type": "video", "width": 1920, "height": 1080,
            "avg_frame_rate": "30/1", "tags": {"rotate": "90"},
        }],
        "format": {"duration": "2.0"},
    })
    assert (geo["width"], geo["height"]) == (1080, 1920)


def test_zero_avg_frame_rate_falls_back_to_r_frame_rate():
    geo = ov.geometry_from_probe({
        "streams": [{
            "codec_type": "video", "width": 320, "height": 240,
            "avg_frame_rate": "0/0", "r_frame_rate": "30000/1001",
        }],
        "format": {"duration": "2.0"},
    })
    assert geo["fps"] == pytest.approx(29.97, abs=0.005)
    assert geo["fps_rational"] == "30000/1001"


def test_stream_duration_is_used_when_container_has_none():
    geo = ov.geometry_from_probe({
        "streams": [{
            "codec_type": "video", "width": 320, "height": 240,
            "avg_frame_rate": "25", "duration": "7.5",
        }],
        "format": {},
    })
    assert geo["duration"] == 7.5


@pytest.mark.parametrize("probe, fragment", [
    ({"streams": [], "format": {"duration": "2"}}, "No video stream"),
    ({"streams": [{"codec_type": "video", "width": 0, "height": 0,
                   "avg_frame_rate": "30"}], "format": {"duration": "2"}}, "width and height"),
    ({"streams": [{"codec_type": "video", "width": 320, "height": 240,
                   "avg_frame_rate": "0/0", "r_frame_rate": "0/0"}],
      "format": {"duration": "2"}}, "frame rate"),
    ({"streams": [{"codec_type": "video", "width": 320, "height": 240,
                   "avg_frame_rate": "30"}], "format": {}}, "duration"),
])
def test_geometry_errors_are_specific(probe, fragment):
    geo = ov.geometry_from_probe(probe)
    assert geo["ok"] is False
    assert fragment in geo["error"]


def test_ffmpeg_args_contract():
    args = ov.overlay_ffmpeg_args(
        {"width": 1080, "height": 1920, "duration": 2.5, "fps_rational": "30000/1001"},
        sub_name="sub.ass",
        out_path="overlay.mov",
    )
    joined = " ".join(args)
    assert args[0] == "ffmpeg"
    assert "color=c=black@0.0:s=1080x1920:r=30000/1001:d=2.500" in joined
    assert "format=argb" in joined
    assert "ass=filename='sub.ass':alpha=1" in joined
    assert "-c:v qtrle" in joined
    assert "-pix_fmt argb" in joined
    assert "-an" in args
    assert args[-3:] == ["-t", "2.500", "overlay.mov"]


@pytest.mark.parametrize("geometry", [
    {"width": 0, "height": 240, "duration": 1, "fps_rational": "30"},
    {"width": 320, "height": 240, "duration": 0, "fps_rational": "30"},
    {"width": 320, "height": 240, "duration": 1, "fps_rational": "0/0"},
])
def test_ffmpeg_args_reject_unusable_geometry(geometry):
    with pytest.raises(ValueError):
        ov.overlay_ffmpeg_args(geometry)


# --- real render ------------------------------------------------------------

def test_export_produces_transparent_qtrle_mov(source_clip, subtitle_file, tmp_path):
    out = tmp_path / "overlay.mov"
    res = ov.export_alpha_overlay(source_clip, subtitle_file, str(out), timeout_sec=120)

    assert res["success"] is True, res.get("error")
    assert (res["width"], res["height"]) == (320, 240)
    assert res["fps"] == pytest.approx(30.0, abs=0.01)
    assert res["aspect"] == "16:9"  # 320x240 is 4:3, nearest supported landscape

    probe = _ffprobe_json(out)
    stream = probe["streams"][0]
    assert stream["codec_name"] == "qtrle"
    assert stream["pix_fmt"] == "argb"
    assert (stream["width"], stream["height"]) == (320, 240)
    assert int(stream["nb_frames"]) == pytest.approx(30, abs=1)
    assert res["file_size"] == os.path.getsize(out)

    # Alpha proof: ink while the caption is on screen, nothing after it.
    during = _alpha_frame(out, 320, 240, seek=0.1)
    after = _alpha_frame(out, 320, 240, seek=0.8)
    assert max(during) > 0, "caption rendered into the alpha channel"
    assert during[0] == 0, "background corner is transparent"
    assert max(after) == 0, "gap frame is fully transparent"


def test_rotated_source_renders_a_display_sized_overlay(tmp_path, subtitle_file):
    """A display matrix of 90° must give a portrait canvas, not a sideways one."""
    flat = tmp_path / "flat.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
         "-i", "color=c=gray:s=320x240:r=25:d=1", "-c:v", "mpeg4", str(flat)],
        check=True, creationflags=NO_WINDOW,
    )
    rotated = tmp_path / "rotated.mov"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(flat), "-c", "copy",
         "-metadata:s:v:0", "rotate=90", str(rotated)],
        check=True, creationflags=NO_WINDOW,
    )

    geo = ov.probe_overlay_geometry(str(rotated))
    if geo.get("rotation") != 90:
        pytest.skip("this ffmpeg build does not write a display matrix")

    assert (geo["width"], geo["height"]) == (240, 320)
    res = ov.export_alpha_overlay(str(rotated), subtitle_file, str(tmp_path / "rot.mov"), timeout_sec=120)
    assert res["success"] is True, res.get("error")
    assert (res["width"], res["height"]) == (240, 320)


def test_missing_input_reports_error(tmp_path, subtitle_file):
    res = ov.export_alpha_overlay(str(tmp_path / "nope.mp4"), subtitle_file)
    assert res["success"] is False
    assert "not found" in res["error"].lower()


def test_missing_subtitle_reports_error(source_clip, tmp_path):
    res = ov.export_alpha_overlay(source_clip, str(tmp_path / "nope.ass"), str(tmp_path / "o.mov"))
    assert res["success"] is False
    assert "Subtitle file not found" in res["error"]


def test_timeout_reports_error_without_leaving_a_file(source_clip, subtitle_file, tmp_path, monkeypatch):
    out = tmp_path / "timed_out.mov"
    real_run = subprocess.run

    def fake_run(cmd, *args, **kwargs):
        if cmd and str(cmd[0]).endswith("ffmpeg"):
            out.write_bytes(b"partial")
            raise subprocess.TimeoutExpired(cmd="ffmpeg", timeout=1)
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(ov.subprocess, "run", fake_run)

    res = ov.export_alpha_overlay(source_clip, subtitle_file, str(out), timeout_sec=1)
    assert res["success"] is False
    assert "timed out" in res["error"].lower()
    assert not out.exists(), "a half-written overlay must not survive a timeout"


def test_work_dir_is_removed(source_clip, subtitle_file, tmp_path, monkeypatch):

    created = []
    real = ov.tempfile.TemporaryDirectory

    class Recording:
        def __init__(self, *args, **kwargs):
            self._real = real(*args, **kwargs)

        def __enter__(self):
            name = self._real.__enter__()
            created.append(name)
            return name

        def __exit__(self, *exc):
            return self._real.__exit__(*exc)

    monkeypatch.setattr(ov, "tempfile", types.SimpleNamespace(TemporaryDirectory=Recording))

    res = ov.export_alpha_overlay(source_clip, subtitle_file, str(tmp_path / "o.mov"), timeout_sec=120)
    assert res["success"] is True, res.get("error")
    assert created and not os.path.exists(created[0])


# --- export endpoint --------------------------------------------------------

def test_endpoint_returns_a_mov_download(source_clip):
    from fastapi.testclient import TestClient
    from server import app

    client = TestClient(app)
    with open(source_clip, "rb") as handle:
        res = client.post(
            "/api/export/overlay-video",
            files={"video": ("clip.mp4", handle, "video/mp4")},
            data={"subtitles": ASS_TEXT},
        )

    assert res.status_code == 200, res.text
    assert "video/quicktime" in res.headers["content-type"]
    assert "clip_overlay.mov" in res.headers["content-disposition"]
    assert res.content[4:8] == b"ftyp"
    assert len(res.content) > 1024


def test_ui_wires_the_overlay_button():
    """The button, the JS call and the route must all name the same thing."""
    from fastapi.testclient import TestClient
    from server import app

    client = TestClient(app)
    html = client.get("/").text
    assert 'id="overlayVideoBtn"' in html

    js = client.get("/app.js")
    assert js.status_code == 200, js.status_code
    assert "/api/export/overlay-video" in js.text
    assert "overlayVideoBtn" in js.text
    assert "_overlay.mov" in js.text

    assert "/api/export/overlay-video" in {getattr(r, "path", "") for r in app.routes}


def test_endpoint_reports_unreadable_media(tmp_path):
    from fastapi.testclient import TestClient
    from server import app

    broken = tmp_path / "broken.mp4"
    broken.write_bytes(b"definitely not a video")

    client = TestClient(app)
    with open(broken, "rb") as handle:
        res = client.post(
            "/api/export/overlay-video",
            files={"video": ("broken.mp4", handle, "video/mp4")},
            data={"subtitles": ASS_TEXT},
        )

    assert res.status_code == 500
    assert "Traceback" not in res.text
    assert res.json()["detail"]
