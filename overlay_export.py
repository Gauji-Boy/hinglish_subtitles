"""
overlay_export.py - Transparent alpha overlay renderer (qtrle .mov).

Renders the same karaoke ASS as the MP4 burn onto an invisible canvas at the
source video's display size, frame rate and duration, so an editor can drop the
result in an NLE track above the original footage.

libass writes the captions into the alpha channel (``alpha=1``) and QuickTime
Animation stores them losslessly (``qtrle`` + ``argb``). There is deliberately no
lossy fallback: an overlay that silently loses its alpha is worse than an error.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Dict, Optional

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

FFPROBE_TIMEOUT_SEC = 30


def parse_frame_rate(raw: Any) -> Optional[Dict[str, Any]]:
    """Turn an ffprobe frame-rate string into ``{rational, value}``, or None."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip()
    num, _, den = text.partition("/")
    try:
        numerator = float(num)
        denominator = float(den) if den else 1.0
    except (TypeError, ValueError):
        return None
    if numerator <= 0 or denominator <= 0:
        return None
    return {"rational": text, "value": numerator / denominator}


def aspect_for_size(width: int, height: int) -> str:
    """Pick the supported caption aspect for a canvas, matching the browser side."""
    ratio = width / height
    if ratio > 1.2:
        return "16:9"
    if ratio < 0.85:
        return "9:16"
    return "1:1"


def _rotation_degrees(stream: Dict[str, Any]) -> int:
    for entry in stream.get("side_data_list") or []:
        if isinstance(entry, dict) and "rotation" in entry:
            try:
                return int(round(float(entry["rotation"])))
            except (TypeError, ValueError):
                continue
    tags = stream.get("tags") or {}
    try:
        return int(round(float(tags.get("rotate"))))
    except (TypeError, ValueError):
        return 0


def _duration_seconds(stream: Dict[str, Any], container: Dict[str, Any]) -> float:
    for raw in (container.get("duration"), stream.get("duration")):
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value
    return 0.0


def geometry_from_probe(probe: Dict[str, Any]) -> Dict[str, Any]:
    """Derive overlay geometry from an ``ffprobe -show_streams`` document.

    Separate from the subprocess call so rotation, frame-rate fallback and
    duration rules can be tested without a media file.
    """
    streams = probe.get("streams") or []
    stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    if stream is None:
        return {"ok": False, "error": "No video stream found in the file."}

    try:
        width = int(stream.get("width") or 0)
        height = int(stream.get("height") or 0)
    except (TypeError, ValueError):
        width = height = 0
    if width <= 0 or height <= 0:
        return {"ok": False, "error": "Video stream has no usable width and height."}

    rotation = _rotation_degrees(stream)
    if abs(rotation) % 180 == 90:
        width, height = height, width

    fps = parse_frame_rate(stream.get("avg_frame_rate")) or parse_frame_rate(stream.get("r_frame_rate"))
    if fps is None:
        return {"ok": False, "error": "Could not read the video frame rate."}

    duration = _duration_seconds(stream, probe.get("format") or {})
    if duration <= 0:
        return {"ok": False, "error": "Could not read the video duration."}

    return {
        "ok": True,
        "width": width,
        "height": height,
        "rotation": rotation,
        "fps": round(fps["value"], 6),
        "fps_rational": fps["rational"],
        "duration": round(duration, 6),
        "aspect": aspect_for_size(width, height),
    }


def probe_overlay_geometry(video_path: str) -> Dict[str, Any]:
    """Read the overlay canvas (display size, fps, duration) from a video file."""
    if not os.path.isfile(video_path):
        return {"ok": False, "error": f"Input video not found: {video_path}"}

    cmd = [
        "ffprobe", "-v", "error",
        "-show_streams", "-show_format",
        "-of", "json",
        video_path,
    ]
    try:
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=FFPROBE_TIMEOUT_SEC, creationflags=_NO_WINDOW
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"ffprobe timed out after {FFPROBE_TIMEOUT_SEC}s."}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    if proc.returncode != 0:
        return {"ok": False, "error": f"ffprobe error: {proc.stderr[-300:]}"}
    try:
        probe = json.loads(proc.stdout or "{}")
    except ValueError:
        return {"ok": False, "error": "ffprobe returned unreadable JSON."}
    return geometry_from_probe(probe)


def overlay_ffmpeg_args(
    geometry: Dict[str, Any],
    sub_name: str = "sub.ass",
    out_path: str = "overlay.mov",
) -> list:
    """Build the transparent-render command. No process is started here."""
    try:
        width = int(geometry.get("width") or 0)
        height = int(geometry.get("height") or 0)
        duration = float(geometry.get("duration") or 0)
    except (TypeError, ValueError):
        raise ValueError("overlay geometry needs numeric width, height and duration")
    if width <= 0 or height <= 0:
        raise ValueError("overlay geometry needs a positive width and height")
    if duration <= 0:
        raise ValueError("overlay geometry needs a positive duration")

    rate = geometry.get("fps_rational") or geometry.get("fps")
    parsed = parse_frame_rate(str(rate))
    if parsed is None:
        raise ValueError("overlay geometry needs a usable frame rate")

    # A transparent colour source with a real alpha channel, then libass drawing
    # into that alpha channel instead of blending over pixels.
    source = (
        f"color=c=black@0.0:s={width}x{height}:r={parsed['rational']}"
        f":d={duration:.3f},format=argb"
    )
    return [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", source,
        "-vf", f"ass=filename='{sub_name}':alpha=1",
        "-c:v", "qtrle",
        "-pix_fmt", "argb",
        "-an",
        "-t", f"{duration:.3f}",
        out_path,
    ]


def export_alpha_overlay(
    video_path: str,
    subtitle_path: str,
    output_path: Optional[str] = None,
    timeout_sec: int = 600,
) -> Dict[str, Any]:
    """Render a transparent .mov of the given ASS at the source video's geometry.

    Returns ``{success, output_path, width, height, fps, duration, aspect,
    rotation, file_size, error}``. Never raises for media problems.
    """
    if not os.path.isfile(video_path):
        return {"success": False, "error": f"Input video not found: {video_path}"}
    if not os.path.isfile(subtitle_path):
        return {"success": False, "error": f"Subtitle file not found: {subtitle_path}"}

    geometry = probe_overlay_geometry(video_path)
    if not geometry.get("ok"):
        return {"success": False, "error": geometry.get("error", "Could not read the video.")}

    abs_out = os.path.abspath(output_path or f"{os.path.splitext(os.path.abspath(video_path))[0]}_overlay.mov")
    existed_before = os.path.exists(abs_out)

    with tempfile.TemporaryDirectory() as work_dir:
        # Bare relative subtitle name: libass never sees a Windows colon path.
        shutil.copyfile(os.path.abspath(subtitle_path), os.path.join(work_dir, "sub.ass"))
        args = overlay_ffmpeg_args(geometry, "sub.ass", abs_out)

        try:
            proc = subprocess.run(
                args, cwd=work_dir,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, timeout=timeout_sec, creationflags=_NO_WINDOW
            )
        except subprocess.TimeoutExpired:
            _discard_partial(abs_out, existed_before)
            return {"success": False, "error": f"Alpha overlay render timed out after {timeout_sec}s."}
        except Exception as exc:
            _discard_partial(abs_out, existed_before)
            return {"success": False, "error": str(exc)}

        if proc.returncode != 0:
            _discard_partial(abs_out, existed_before)
            return {"success": False, "error": f"FFmpeg error: {proc.stderr[-500:]}"}
        if not os.path.exists(abs_out) or os.path.getsize(abs_out) == 0:
            _discard_partial(abs_out, existed_before)
            return {"success": False, "error": "Alpha overlay file was not generated or is empty."}

        return {
            "success": True,
            "output_path": abs_out,
            "width": geometry["width"],
            "height": geometry["height"],
            "fps": geometry["fps"],
            "duration": geometry["duration"],
            "aspect": geometry["aspect"],
            "rotation": geometry["rotation"],
            "file_size": os.path.getsize(abs_out),
        }


def _discard_partial(path: str, existed_before: bool) -> None:
    """Remove a half-written overlay, but never a file the call did not create."""
    if not existed_before:
        try:
            os.remove(path)
        except OSError:
            pass
