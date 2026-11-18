"""
preview_renderer.py - Renders a true libass preview of a caption style.

The preview is a silent MP4 generated on a dark gradient at the same canvas as
the target video, plus a single PNG frame from that same render. It uses the
exact same ASS generator and FFmpeg libass path as the real burn, so fonts,
colours, outline, box, line breaks, and animation are the burned look - not a
CSS approximation. Results are cached by style + canvas in the temp directory.
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from typing import Any, List, Optional

from caption_styles import aspect_profile, resolve_style
from karaoke_ass import generate_karaoke_ass
from video_burner import get_available_h264_encoder

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

PREVIEW_DIR = os.path.join(tempfile.gettempdir(), "hinglish_caption_previews")
PREVIEW_WIDTH = 540
FRAME_AT_S = 0.95
# Classic presets set a small font near the bottom of the frame. The picker
# shows the same render with the caption centred and enlarged, so the whole
# line is readable in either canvas. Kinetic posters are already large.
PREVIEW_FONT_FACTOR = {"16:9": 2.0, "9:16": 1.8, "1:1": 1.9}

# The picker previews the sentence the user asked for. Short, timed phrases give
# classic styles a normal card and give kinetic styles enough words to show
# their real multi-line poster layout.
SAMPLE_SENTENCE = (
    "Yaar, Monday morning ki coffee aur ye weather... "
    "bas aur kya chahiye life mein! "
    "Chalo, kaam shuru karte hain."
)
SAMPLE_PHRASES = (
    "Yaar, Monday morning ki coffee aur ye weather...",
    "bas aur kya chahiye life mein!",
    "Chalo, kaam shuru karte hain.",
)


def build_preview_cards() -> List[dict]:
    """Build timed cards for the preview sentence, read by every ASS emitter."""
    cards: List[dict] = []
    cursor = 0.2
    for phrase in SAMPLE_PHRASES:
        words = []
        for token in phrase.split():
            end = round(cursor + 0.18, 3)
            words.append({
                "start": round(cursor, 3), "end": end,
                "word": token, "hinglish": token,
            })
            cursor = round(end + 0.02, 3)
        cards.append({
            "start": 0.2 if not cards else cards[-1]["end"] + 0.16,
            "end": words[-1]["end"],
            "text": phrase, "hinglish_text": phrase,
            "words": words,
        })
        cursor = round(cursor + 0.16, 3)
    return cards


# Cover the whole sample sentence, not just its first phrase. Defined after
# build_preview_cards so it follows any edit to the sentence or its pacing.
PREVIEW_SECONDS = round(build_preview_cards()[-1]["end"] + 0.3, 2)


def preview_style(style: Optional[Any] = None, aspect: str = "9:16") -> Any:
    """Style used by the picker: same look, centred and enlarged for classic."""
    resolved = resolve_style(style)
    if resolved.get("motion") in ("none", "static", "karaoke"):
        factor = PREVIEW_FONT_FACTOR.get(aspect, 1.9)
        resolved = dict(resolved, alignment=5, margin_v=0,
                        font_size=min(140, max(24, int(round(resolved["font_size"] * factor)))))
    return resolved


def preview_ass_text(style: Optional[Any] = None, aspect: str = "9:16") -> str:
    """The ASS the preview renders - the same text and generator as the burn."""
    return generate_karaoke_ass(
        build_preview_cards(),
        script_title="Caption Style Preview",
        style=preview_style(style, aspect),
        aspect=aspect,
    )


def preview_cache_path(style: Optional[Any] = None, aspect: str = "9:16",
                       fmt: str = "mp4") -> str:
    """Return the deterministic cache path for a style, canvas and format."""
    resolved = resolve_style(style)
    profile = aspect_profile(aspect)
    key = hashlib.sha256(
        (json.dumps(resolved, sort_keys=True)
         + f"|{profile['play_res_x']}x{profile['play_res_y']}|{fmt}|{SAMPLE_SENTENCE}"
         + f"|{PREVIEW_SECONDS}|{FRAME_AT_S}").encode("utf-8")
    ).hexdigest()[:20]
    ext = "png" if fmt.startswith("png") else "mp4"
    return os.path.join(PREVIEW_DIR, f"preview_{key}.{ext}")


def render_preview(style: Optional[Any] = None, aspect: str = "9:16",
                   fmt: str = "mp4") -> str:
    """Render (or return a cached) silent MP4 preview. Raises RuntimeError on failure."""
    if fmt == "png":
        return render_preview_frame(style, aspect)
    resolved = preview_style(style, aspect)
    profile = aspect_profile(aspect)
    os.makedirs(PREVIEW_DIR, exist_ok=True)

    output_path = preview_cache_path(resolved, aspect)
    if os.path.isfile(output_path) and os.path.getsize(output_path) > 1024:
        return output_path

    ass_text = generate_karaoke_ass(
        build_preview_cards(),
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


def render_preview_frame(style: Optional[Any] = None, aspect: str = "9:16",
                         at_s: float = FRAME_AT_S) -> str:
    """Return a cached PNG of the same libass preview, for picker thumbnails.

    The frame is taken from the rendered MP4, not drawn separately, so what the
    picker shows is literally a frame of the video the burner would produce.
    """
    resolved = preview_style(style, aspect)
    output_path = preview_cache_path(resolved, aspect, "png")
    if os.path.isfile(output_path) and os.path.getsize(output_path) > 1024:
        return output_path

    video_path = render_preview(style, aspect, "mp4")
    os.makedirs(PREVIEW_DIR, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="hframe_") as work_dir:
        temp_out = os.path.join(work_dir, "frame.png")
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-ss", str(at_s), "-i", video_path,
            "-frames:v", "1", temp_out,
        ]
        try:
            proc = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, timeout=30, creationflags=_NO_WINDOW,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Preview frame render timed out after 30s.")
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg frame failed: {proc.stderr[-400:]}")
        with open(temp_out, "rb") as handle:
            if handle.read(8) != b"\x89PNG\r\n\x1a\n":
                raise RuntimeError("FFmpeg produced an empty preview frame.")
        os.replace(temp_out, output_path)
    return output_path
