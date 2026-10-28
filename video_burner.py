"""
video_burner.py - High-speed local FFmpeg subtitle burner with hardware acceleration (h264_mf).
Renders and burns either standard (.srt) or animated karaoke (.ass) subtitles directly onto MP4 videos.
"""

import os
import sys
import subprocess
import tempfile
import shutil
from typing import Optional, Dict, Any, Tuple

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
_CACHED_ENCODER: Optional[Tuple[str, list]] = None


def get_available_h264_encoder() -> Tuple[str, list]:
    """
    Finds the best operational H.264 encoder in FFmpeg on Windows.
    Prefers Windows MediaFoundation hardware encoder (h264_mf), then fallback.
    Probes once per process: encoders do not change while the app is open.
    """
    global _CACHED_ENCODER
    if _CACHED_ENCODER is not None:
        return _CACHED_ENCODER

    candidates = [
        ("h264_mf", ["-c:v", "h264_mf", "-b:v", "3M"]),
        ("libx264", ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "22"])
    ]
    for enc, args in candidates:
        try:
            cmd = [
                "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=64x64:d=0.05",
                "-c:v", enc, "-f", "null", "-"
            ]
            res = subprocess.run(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=3, creationflags=_NO_WINDOW
            )
            if res.returncode == 0:
                _CACHED_ENCODER = (enc, args)
                return _CACHED_ENCODER
        except Exception:
            pass
    _CACHED_ENCODER = ("libx264", ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "22"])
    return _CACHED_ENCODER


def burn_subtitles_to_video(
    video_path: str,
    subtitle_path: str,
    output_path: Optional[str] = None,
    timeout_sec: int = 600
) -> Dict[str, Any]:
    """
    Executes FFmpeg to burn subtitles into a video file.
    Uses relative path isolation to guarantee 100% Windows path safety with libass.
    Returns dict with {success, output_path, encoder, file_size, error}.
    """
    if not os.path.exists(video_path):
        return {"success": False, "error": f"Input video not found: {video_path}"}
    if not os.path.exists(subtitle_path):
        return {"success": False, "error": f"Subtitle file not found: {subtitle_path}"}

    abs_video = os.path.abspath(video_path)
    abs_sub = os.path.abspath(subtitle_path)

    if not output_path:
        base, _ = os.path.splitext(abs_video)
        output_path = f"{base}_burned.mp4"
    abs_out = os.path.abspath(output_path)

    encoder_name, encoder_args = get_available_h264_encoder()

    # Use a temporary directory as the working directory to bypass all Windows colon path escaping issues
    with tempfile.TemporaryDirectory() as work_dir:
        sub_ext = os.path.splitext(abs_sub)[1].lower()
        work_sub = os.path.join(work_dir, f"sub{sub_ext}")
        shutil.copyfile(abs_sub, work_sub)

        is_ass = (sub_ext == ".ass")
        filter_str = f"ass=filename='sub{sub_ext}'" if is_ass else f"subtitles=filename='sub{sub_ext}'"

        cmd = [
            "ffmpeg", "-y",
            "-i", abs_video,
            "-vf", filter_str,
            *encoder_args,
            "-c:a", "copy",
            # Put the moov atom first so the burned file plays and seeks in a
            # browser <video> without waiting for the whole download.
            "-movflags", "+faststart",
            abs_out
        ]

        try:
            proc = subprocess.run(
                cmd,
                cwd=work_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout_sec,
                creationflags=_NO_WINDOW
            )

            if proc.returncode != 0:
                return {"success": False, "error": f"FFmpeg error: {proc.stderr[-500:]}"}

            if not os.path.exists(abs_out) or os.path.getsize(abs_out) == 0:
                return {"success": False, "error": "Output burned video file was not generated or is empty."}

            return {
                "success": True,
                "output_path": abs_out,
                "encoder": encoder_name,
                "file_size": os.path.getsize(abs_out)
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Video encoding timed out after {timeout_sec}s."}
        except Exception as e:
            return {"success": False, "error": str(e)}
