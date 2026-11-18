"""Tests for the true libass style preview renderer."""

import os
import shutil

import pytest

from preview_renderer import (PREVIEW_SECONDS, build_preview_cards,
                              preview_ass_text, render_preview, render_preview_frame)

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not on PATH")


def _is_mp4(path: str) -> bool:
    with open(path, "rb") as handle:
        header = handle.read(12)
    return len(header) == 12 and header[4:8] == b"ftyp"


def test_preview_renders_real_mp4():
    path = render_preview("hormozi", "9:16")
    assert os.path.isfile(path)
    assert os.path.getsize(path) > 1024
    assert _is_mp4(path)


def test_preview_is_cached_by_style_and_aspect():
    first = render_preview("vox", "16:9")
    mtime = os.path.getmtime(first)
    second = render_preview("vox", "16:9")
    assert first == second
    assert os.path.getmtime(second) == mtime


def test_preview_duration_covers_the_whole_sentence():
    assert PREVIEW_SECONDS >= build_preview_cards()[-1]["end"] + 0.2


def test_preview_uses_the_sample_sentence():
    ass = preview_ass_text("hormozi", "16:9").lower()
    assert "monday" in ass
    assert "coffee" in ass
    assert "chalo" in ass
    assert "make every word" not in ass


def test_preview_respects_each_styles_line_layout():
    # Honey Punch is a multi-line kinetic poster; Hormozi is a single classic
    # line. The preview must show that difference, not flatten both to a chip.
    honey = preview_ass_text("honeypunch", "16:9")
    hormozi = preview_ass_text("hormozi", "16:9")
    assert "\\N" in honey
    assert "\\N" not in hormozi


def _is_png(path: str) -> bool:
    with open(path, "rb") as handle:
        return handle.read(8) == b"\x89PNG\r\n\x1a\n"


def test_preview_frame_is_a_cached_png():
    path = render_preview_frame("hormozi", "16:9")
    assert path.endswith(".png")
    assert _is_png(path)
    mtime = os.path.getmtime(path)
    assert render_preview_frame("hormozi", "16:9") == path
    assert os.path.getmtime(path) == mtime


def test_classic_preview_is_centred_and_enlarged():
    # A classic preset is a small bottom caption. The picker's ASS keeps the
    # same style but centres it and enlarges it so the whole line is readable
    # in either canvas, without cropping words away.
    ass = preview_ass_text("hormozi", "16:9")
    fields = next(l for l in ass.splitlines() if l.startswith("Style:")).split(",")
    assert fields[18] == "5"          # alignment: centre
    assert int(fields[2]) >= 90       # enlarged from the export's 51 px
    assert "coffee" in ass.lower()


def test_kinetic_preview_keeps_its_own_geometry():
    ass = preview_ass_text("honeypunch", "16:9")
    assert "\\N" in ass
    assert "coffee" in ass.lower()


def test_different_styles_use_different_previews():
    first = render_preview({"id": "custom", "name": "A", "font": "Georgia"}, "1:1")
    second = render_preview({"id": "custom", "name": "B", "font": "Consolas"}, "1:1")
    assert first != second
    assert _is_mp4(first) and _is_mp4(second)
