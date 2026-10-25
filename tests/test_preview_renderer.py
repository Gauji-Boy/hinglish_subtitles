"""Tests for the true libass style preview renderer."""

import os
import shutil

import pytest

from preview_renderer import render_preview

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


def test_different_styles_use_different_previews():
    first = render_preview({"id": "custom", "name": "A", "font": "Georgia"}, "1:1")
    second = render_preview({"id": "custom", "name": "B", "font": "Consolas"}, "1:1")
    assert first != second
    assert _is_mp4(first) and _is_mp4(second)
