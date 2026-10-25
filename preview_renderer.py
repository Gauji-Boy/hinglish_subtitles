"""
preview_renderer.py - Renders a short, true libass preview of a caption style.

The preview is a silent MP4 generated on a dark gradient at the same canvas as
the target video. It uses the exact same ASS generator and FFmpeg libass path as
the real burn, so fonts, colours, outline, box, and animation are representative.
Results are cached by style + canvas in the temp directory.
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from typing import Any, Optional

from caption_styles import aspect_profile, resolve_style
from karaoke_ass import generate_karaoke_ass
from video_burner import get_available_h264_encoder

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

PREVIEW_DIR = os.path.join(tempfile.gettempdir(), "hinglish_caption_previews")
PREVIEW_SECONDS = 2.6
PREVIEW_WIDTH = 540

SAMPLE_CARDS = [
    {
        "start": 0.20,
        "end": 1.20,
        "words": [
            {"start": 0.20, "end": 0.55, "hinglish": "Make"},
            {"start": 0.55, "end": 0.90, "hinglish": "every"},
            {"start": 0.90, "end": 1.20, "hinglish": "word"},
        ],
    },
    {
        "start": 1.45,
        "end": 2.45,
        "words": [
            {"start": 1.45, "end": 1.80, "hinglish": "land"},
            {"start": 1.80, "end": 2.15, "hinglish": "with"},
            {"start": 2.15, "end": 2.45, "hinglish": "impact"},
        ],
    },
]


def preview_cache_path(style: Optional[Any] = None, aspect: str = "9:16") -> str:
    """Return the deterministic cache path for a style and canvas."""
    resolved = resolve_style(style)
    profile = aspect_profile(aspect)
    key = hashlib.sha256(
        (json.dumps(resolved, sort_keys=True) + f"|{profile['play_res_x']}x{profile['play_res_y']}").encode("utf-8")
    ).hexdigest()[:20]
    return os.path.join(PREVIEW_DIR, f"preview_{key}.mp4")


def render_preview(style: Optional[Any] = None, aspect: str = "9:16") -> str:
    """Render (or return a cached) silent MP4 preview. Raises RuntimeError on failure."""
    resolved = resolve_style(style)
    profile = aspect_profile(aspect)
    os.makedirs(PREVIEW_DIR, exist_ok=True)

    output_path = preview_cache_path(resolved, aspect)
    if os.path.isfile(output_path) and os.path.getsize(output_path) > 1024:
        return output_path

    ass_text = generate_karaoke_ass(
        SAMPLE_CARDS,
        script_title="Caption Style Preview",
        style=resolved,
        aspect=aspect,
    )

    width = profile["play_res_x"]
    height = profile["play_res_y"]
    encoder_name, encoder_args = get_available_h264_encoder()
    if encoder_name == "h264_mf":
        encoder_args = ["-c:v", "h264_mf", "-b:v", "1500k"]

    with tempfile.TemporaryDirectory(prefix="hpreview_") as work_dir:
        ass_path = os.path.join(work_dir, "preview.ass")
        temp_out = os.path.join(work_dir, "preview.mp4")
        with open(ass_path, "w", encoding="utf-8") as handle:
            handle.write(ass_text)

        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"gradients=s={width}x{height}:c0=0x0F172A:c1=0x1E293B",
            "-vf", f"ass=preview.ass,scale={PREVIEW_WIDTH}:-2",
            "-t", str(PREVIEW_SECONDS),
            "-an",
            *encoder_args,
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "preview.mp4",
        ]

        try:
            proc = subprocess.run(
                cmd,
                cwd=work_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60,
                creationflags=_NO_WINDOW,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Preview render timed out after 60s.")

        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg preview failed: {proc.stderr[-400:]}")
        if not os.path.exists(temp_out) or os.path.getsize(temp_out) == 0:
            raise RuntimeError("FFmpeg produced an empty preview.")

        os.replace(temp_out, output_path)

    return output_path
