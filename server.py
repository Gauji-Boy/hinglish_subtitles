"""
server.py - High-speed FastAPI server for Hinglish Subtitle Generator.
Serves the Neo-Brutalist Hybrid Pro static web frontend and provides streaming
video upload and GPU-accelerated transcription endpoints.
"""

import os
import sys

# Ensure model cache lives on D: drive to protect C: drive disk space
DEFAULT_MODELS_DIR = r"D:\Hinglish_subtitles\models\huggingface"
if not os.environ.get("HF_HOME"):
    os.environ["HF_HOME"] = DEFAULT_MODELS_DIR

# Ensure pythonw.exe has standard stream fallbacks on Windows
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

# Initialize and install in-app console log interceptors
try:
    from console_bus import install_interceptors, bus
    install_interceptors()
except Exception:
    pass

# Ensure NVIDIA CUDA runtime DLLs (cublas64_12.dll, cudnn, etc.) are registered on Windows
if sys.platform == "win32":
    for pkg_name in ["nvidia.cublas", "nvidia.cudnn", "nvidia.cuda_nvrtc"]:
        try:
            pkg = __import__(pkg_name, fromlist=["bin"])
            for p in getattr(pkg, "__path__", []):
                for root, dirs, files in os.walk(p):
                    if any(f.endswith(".dll") for f in files):
                        os.add_dll_directory(root)
                        os.environ["PATH"] = root + os.pathsep + os.environ["PATH"]
        except Exception:
            pass

from typing import Optional, Dict, Any
import functools
import json
import time
import shutil
import tempfile
import threading
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.background import BackgroundTask
from hinglish_engine import generate_subtitles, get_hardware_info, get_models_status, is_model_cached
from hinglish_upgrades import claim_job_slot, release_job_slot
from faster_whisper.utils import download_model
from caption_styles import ALLOWED_FONTS, DEFAULT_STYLE_ID, list_presets, resolve_style

app = FastAPI(title="Hinglish Subtitle Generator API", version="2.5.0")

# Enable CORS restricted to localhost and 127.0.0.1 ports (no wildcard '*')
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8501", "http://localhost:8501",
        "http://127.0.0.1:8502", "http://localhost:8502",
        "http://127.0.0.1:8503", "http://localhost:8503",
    ],
    allow_origin_regex=r"^https?://(127\.0\.0\.1|localhost)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.endswith((".js", ".css", ".html")):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


@app.get("/api/hardware")
def api_hardware():
    """Returns detected GPU/CPU hardware capabilities."""
    return get_hardware_info()


CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "launch_config.json")
_CONFIG_LOCK = threading.Lock()


def _write_config(data: Dict[str, Any]) -> None:
    """Write config atomically: a crash cannot leave a half-written JSON file."""
    tmp = f"{CONFIG_PATH}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, CONFIG_PATH)


@app.get("/api/config/launch_mode")
def api_get_launch_mode():
    """Returns current launch configuration (silent vs console)."""
    silent = True
    if os.path.isfile(CONFIG_PATH):
        try:
            import json
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                silent = data.get("silent_launch", True)
        except Exception:
            pass
    return {"silent_launch": silent}


@app.post("/api/config/launch_mode")
def api_set_launch_mode(silent_launch: bool = Form(...)):
    """Saves launch configuration (silent vs console)."""
    try:
        with _CONFIG_LOCK:
            data = {}
            if os.path.exists(CONFIG_PATH):
                try:
                    with open(CONFIG_PATH, "r", encoding="utf-8") as rf:
                        data = json.load(rf)
                except Exception:
                    pass
            data["silent_launch"] = silent_launch
            _write_config(data)
        return {"status": "success", "silent_launch": silent_launch}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/console/history")
def api_console_history(limit: int = 1000):
    """Returns buffered console entries for initial frontend hydration."""
    try:
        from console_bus import bus
        return {"lines": bus.get_history(limit=limit)}
    except Exception as e:
        return {"lines": [], "error": str(e)}


@app.post("/api/console/clear")
def api_console_clear():
    """Clears the console ring buffer."""
    try:
        from console_bus import bus
        bus.clear()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/console/stream")
async def api_console_stream(request: Request):
    """Server-Sent Events (SSE) endpoint providing real-time streaming console logs."""
    from fastapi.responses import StreamingResponse
    import asyncio
    from console_bus import bus

    # Ensure event loop reference is bound
    bus.set_event_loop(asyncio.get_running_loop())
    queue = asyncio.Queue(maxsize=1000)
    bus.add_listener(queue)

    async def event_generator():
        try:
            # Send initial keepalive
            yield f"data: {json.dumps({'type': 'connected', 'message': 'Console bus connected'})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    entry = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {json.dumps(entry)}\n\n"
                except asyncio.TimeoutError:
                    # Keep-alive heartbeat ping
                    yield ": ping\n\n"
        finally:
            bus.remove_listener(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/console/download")
def api_console_download():
    """Exports all stored logs as a plain text downloadable file."""
    from console_bus import LOG_FILE_PATH, bus
    if os.path.exists(LOG_FILE_PATH):
        return FileResponse(
            LOG_FILE_PATH,
            media_type="text/plain",
            filename=f"hinglish_console_{int(time.time())}.log"
        )
    # Fallback to buffer text
    entries = bus.get_history(limit=5000)
    text = "\n".join(f"[{e['time']}] [{e['level']}] {e['message']}" for e in entries)
    return HTMLResponse(content=text, media_type="text/plain")


class SubtitleDownloadRequest(BaseModel):
    filename: str
    content: str


@app.post("/api/download/file")
def api_download_file(req: SubtitleDownloadRequest):
    """Securely streams subtitle or plain text content as a downloadable file attachment."""
    safe_name = os.path.basename(req.filename) if req.filename else "subtitles.srt"
    ext = os.path.splitext(safe_name)[1].lower()
    media_type = "application/x-subrip" if ext == ".srt" else "text/plain"
    return Response(
        content=req.content.encode("utf-8"),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )


TEMP_MEDIA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_media")
os.makedirs(TEMP_MEDIA_DIR, exist_ok=True)


def cleanup_old_temp_media(max_age_days: int = 7) -> None:
    """Delete URL-imported clips older than max_age_days; they are preview-only."""
    cutoff = time.time() - max_age_days * 86400
    for name in os.listdir(TEMP_MEDIA_DIR):
        path = os.path.join(TEMP_MEDIA_DIR, name)
        try:
            if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                os.remove(path)
        except OSError:
            pass


def cleanup_orphan_burn_dirs(max_age_days: int = 1) -> None:
    """Remove burn work dirs left behind by a crash or a closed window."""
    tmp = tempfile.gettempdir()
    cutoff = time.time() - max_age_days * 86400
    for name in os.listdir(tmp):
        if not name.startswith("hburn_"):
            continue
        path = os.path.join(tmp, name)
        try:
            if os.path.isdir(path) and os.path.getmtime(path) < cutoff:
                shutil.rmtree(path, ignore_errors=True)
        except OSError:
            pass


cleanup_old_temp_media()
cleanup_orphan_burn_dirs()


class UrlImportRequest(BaseModel):
    url: str
    media_type: str = "video"  # "video" or "audio"
    quality: str = "720p"  # "best", "1080p", "720p", "480p", "128k", "64k"


@app.post("/api/import-url")
def api_import_url(req: UrlImportRequest):
    """Downloads media from YouTube, Instagram Reels, TikTok or video links using yt-dlp."""
    import uuid
    import glob
    url = (req.url or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="Please enter a valid video or reel URL")

    if not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(status_code=400, detail="Invalid URL protocol. Must start with http:// or https://")

    try:
        import yt_dlp

        uid = f"dl_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        outtmpl = os.path.join(TEMP_MEDIA_DIR, f"{uid}.%(ext)s")

        media_type = (req.media_type or "video").lower()
        quality = (req.quality or "720p").lower()

        if media_type == "audio":
            if quality == "64k":
                fmt = 'bestaudio[abr<=96]/bestaudio[ext=m4a]/bestaudio/best'
            elif quality == "128k":
                fmt = 'bestaudio[abr<=160]/bestaudio[ext=m4a]/bestaudio/best'
            else:
                fmt = 'bestaudio[ext=m4a]/bestaudio/best'
            max_size = 100 * 1024 * 1024  # 100 MB max for audio
        else:
            if quality == "480p":
                fmt = 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]/best'
            elif quality == "720p":
                fmt = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]/best'
            elif quality == "1080p":
                fmt = 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best'
            else:
                fmt = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best'
            max_size = 350 * 1024 * 1024  # 350 MB max for video

        ydl_opts = {
            'format': fmt,
            'outtmpl': outtmpl,
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'max_filesize': max_size,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        matches = glob.glob(os.path.join(TEMP_MEDIA_DIR, f"{uid}.*"))
        if not matches:
            raise Exception("Downloaded media file not found on disk")

        downloaded_path = matches[0]
        actual_filename = os.path.basename(downloaded_path)
        downloaded_ext = os.path.splitext(downloaded_path)[1].lower()
        is_audio = media_type == "audio" or downloaded_ext in [".m4a", ".mp3", ".wav", ".aac", ".ogg", ".opus"]

        title = info.get("title") or "Imported Reel"
        safe_title = "".join(c for c in title if c.isalnum() or c in " ._-")[:40].strip() or ("audio" if is_audio else "video")
        duration = float(info.get("duration") or 0.0)

        return {
            "status": "success",
            "filename": f"{safe_title}{downloaded_ext}",
            "media_url": f"/api/media/{actual_filename}",
            "title": title,
            "duration": duration,
            "media_type": "audio" if is_audio else "video"
        }
    except Exception as e:
        err_msg = str(e)
        if "Unsupported URL" in err_msg:
            detail = "Unsupported video URL. Please provide a supported link (YouTube, Instagram, TikTok, etc.)."
        elif "Private video" in err_msg or "Sign in" in err_msg:
            detail = "This video is private, geo-blocked, or requires user login."
        else:
            detail = f"Failed to download video: {err_msg[:120]}"
        raise HTTPException(status_code=400, detail=detail)


@app.get("/api/media/{filename}")
def api_serve_media(filename: str):
    """Serves temporarily staged imported media for video/audio player preview."""
    safe_name = os.path.basename(filename)
    file_path = os.path.join(TEMP_MEDIA_DIR, safe_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Media file not found")

    ext = os.path.splitext(safe_name)[1].lower()
    mime_map = {
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".m4a": "audio/mp4",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".aac": "audio/aac",
        ".opus": "audio/opus",
    }
    media_type = mime_map.get(ext, "application/octet-stream")
    return FileResponse(file_path, media_type=media_type)


class DesktopAPI:
    """Desktop JS bridge for pywebview to handle native Windows OS dialogs and export operations."""

    def __init__(self):
        self._window = None

    def set_window(self, win):
        self._window = win

    def save_subtitle_file(self, filename: str, content: str) -> Dict[str, Any]:
        """Opens native Windows Save File dialog and writes content directly."""
        try:
            if not self._window:
                return {"success": False, "error": "No active window"}

            import webview

            ext = os.path.splitext(filename)[1].lower() if filename else ".srt"
            if ext == ".srt":
                file_types = ("SubRip Subtitles (*.srt)", "All files (*.*)")
            elif ext == ".txt":
                file_types = ("Text Documents (*.txt)", "All files (*.*)")
            else:
                file_types = ("All files (*.*)",)

            chosen = self._window.create_file_dialog(
                dialog_type=webview.FileDialog.SAVE,
                save_filename=filename,
                file_types=file_types
            )
            if chosen:
                save_path = chosen if isinstance(chosen, str) else chosen[0]
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return {"success": True, "path": save_path}
            return {"success": False, "cancelled": True}
        except Exception as e:
            return {"success": False, "error": str(e)}


def save_preferences_dict(prefs: Dict[str, Any]) -> Dict[str, Any]:
    """Safely updates launch_config.json with user preferences."""
    with _CONFIG_LOCK:
        data = {
            "selected_model": "large-v3-turbo",
            "selected_language": "mixed",
            "selected_device": "auto",
            "selected_pacing": "short",
            "caption_style": resolve_style(DEFAULT_STYLE_ID)
        }
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as rf:
                    loaded = json.load(rf)
                    data.update(loaded)
            except Exception:
                pass
        for k, v in prefs.items():
            if v is not None:
                data[k] = v
        _write_config(data)
    return data


@app.get("/api/config/preferences")
def api_get_preferences():
    """Returns saved user preferences (model, language, device, pacing, caption style)."""
    prefs = {
        "selected_model": "large-v3-turbo",
        "selected_language": "mixed",
        "selected_device": "auto",
        "selected_pacing": "short",
        "caption_style": resolve_style(DEFAULT_STYLE_ID)
    }
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k in prefs.keys():
                    if k in data:
                        prefs[k] = data[k]
        except Exception:
            pass
    prefs["caption_style"] = resolve_style(prefs.get("caption_style"))
    return prefs


@app.post("/api/config/preferences")
def api_set_preferences(
    selected_model: Optional[str] = Form(None),
    selected_language: Optional[str] = Form(None),
    selected_device: Optional[str] = Form(None),
    selected_pacing: Optional[str] = Form(None),
    caption_style: Optional[str] = Form(None)
):
    """Saves user preferences into launch_config.json."""
    try:
        parsed_style = None
        if caption_style is not None:
            try:
                parsed_style = resolve_style(json.loads(caption_style))
            except (TypeError, ValueError):
                parsed_style = resolve_style(caption_style)
        data = save_preferences_dict({
            "selected_model": selected_model,
            "selected_language": selected_language,
            "selected_device": selected_device,
            "selected_pacing": selected_pacing,
            "caption_style": parsed_style,
            "caption_custom_style": parsed_style if parsed_style and parsed_style.get("id") == "custom" else None
        })
        return {"status": "success", "preferences": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/caption-styles")
def api_caption_styles():
    """Returns built-in caption presets plus the saved custom style, if any."""
    saved_custom = None
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
            saved_custom = config.get("caption_custom_style")
            active = config.get("caption_style")
            if not saved_custom and isinstance(active, dict) and active.get("id") == "custom":
                saved_custom = active
        except Exception:
            saved_custom = None
    return {
        "default": DEFAULT_STYLE_ID,
        "presets": list_presets(),
        "custom": resolve_style(saved_custom) if saved_custom else None,
        "fonts": list(ALLOWED_FONTS)
    }


@app.post("/api/preview-style")
def api_preview_style(payload: Dict[str, Any]):
    """Renders a short true libass preview MP4 for a caption style."""
    from preview_renderer import render_preview
    try:
        path = render_preview(payload.get("style"), payload.get("aspect", "9:16"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview render failed: {e}")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename="caption-preview.mp4",
        headers={"Cache-Control": "no-store"}
    )


@app.post("/api/export/ass")
def api_export_ass(payload: Dict[str, Any]):
    """Generates an Advanced SubStation Alpha (.ass) karaoke script from segments."""
    from karaoke_ass import generate_karaoke_ass
    segments = payload.get("segments", [])
    title = payload.get("title", "Hinglish Subtitles - Karaoke")
    style = payload.get("style")
    aspect = payload.get("aspect", "9:16")
    ass_text = generate_karaoke_ass(segments, script_title=title, style=style, aspect=aspect)
    return Response(
        content=ass_text,
        media_type="text/x-ssa",
        headers={"Content-Disposition": 'attachment; filename="karaoke_subtitles.ass"'}
    )


@app.post("/api/export/burn-video")
def api_burn_video(
    video: UploadFile = File(...),
    subtitles: str = Form(...),
    format_type: str = Form("ass")
):
    """
    Burns styled subtitles (.ass karaoke or .srt) directly into the uploaded video using FFmpeg.
    Returns the subtitled MP4 file.
    """
    from video_burner import burn_subtitles_to_video
    suffix = os.path.splitext(video.filename or "video.mp4")[1] or ".mp4"
    if not suffix.startswith("."):
        suffix = f".{suffix}"

    work_dir = tempfile.mkdtemp(prefix="hburn_")
    temp_vid_path = os.path.join(work_dir, f"input{suffix}")
    temp_sub_path = os.path.join(work_dir, f"sub.{format_type}")
    temp_out_path = os.path.join(work_dir, "burned.mp4")

    try:
        with open(temp_vid_path, "wb") as f:
            shutil.copyfileobj(video.file, f)
        with open(temp_sub_path, "w", encoding="utf-8") as f:
            f.write(subtitles)

        res = burn_subtitles_to_video(temp_vid_path, temp_sub_path, temp_out_path)
        if not res.get("success"):
            raise HTTPException(status_code=500, detail=res.get("error", "FFmpeg burn failed"))

        base_name = os.path.splitext(video.filename or "video")[0]
        download_name = f"{base_name}_subtitled.mp4"

        # Stream from disk; delete the work dir only after the download finishes.
        return FileResponse(
            temp_out_path,
            media_type="video/mp4",
            filename=download_name,
            background=BackgroundTask(shutil.rmtree, work_dir, ignore_errors=True),
        )
    except Exception:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise


@app.get("/api/models")
def api_models():
    """Returns cache and download status for all supported Whisper models."""
    return get_models_status()


@app.post("/api/download_model")
def api_download_model(model_size: str = Form(...)):
    """Pre-downloads a Whisper model and caches it locally."""
    try:
        path = download_model(model_size)
        return {"status": "success", "model_size": model_size, "path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _single_job_endpoint(fn):
    """Answer 409 instead of parking the request behind a running transcription.

    The slot is the same RLock the engines take in `single_job`; the request
    thread re-enters it, so the engine is not blocked by its own guard.
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if not claim_job_slot():
            raise HTTPException(
                status_code=409,
                detail="Another transcription is already running. Wait for it to finish, then try again.",
            )
        try:
            return fn(*args, **kwargs)
        finally:
            release_job_slot()
    return wrapper


@app.post("/api/transcribe")
@_single_job_endpoint
def api_transcribe(
    video: UploadFile = File(...),
    language: str = Form("mixed"),
    model_size: str = Form("medium"),
    device: str = Form("auto"),
    topic_hint: str = Form(""),
    pacing: str = Form("short"),
    enable_diarization: bool = Form(False)
):
    """
    Receives an uploaded video/audio file and runs GPU/CPU transcription with Hinglish transliteration.
    """
    # Persist chosen settings on transcription run
    try:
        save_preferences_dict({
            "selected_model": model_size,
            "selected_language": language,
            "selected_device": device,
            "selected_pacing": pacing,
            "enable_diarization": bool(enable_diarization)
        })
    except Exception:
        pass

    suffix = os.path.splitext(video.filename)[1] if video.filename else ".mp4"

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as work_dir:
        temp_video_path = os.path.join(work_dir, f"input{suffix}")
        try:
            with open(temp_video_path, "wb") as f:
                shutil.copyfileobj(video.file, f)

            if language == "hi-en":
                from hindi_to_english_engine import generate_english_subtitles
                results = generate_english_subtitles(
                    video_path=temp_video_path,
                    model_size=model_size,
                    device=device,
                    topic_hint=topic_hint,
                    pacing=pacing,
                    enable_diarization=enable_diarization
                )
            else:
                # Run GPU/CPU transcription & Hinglish transliteration
                results = generate_subtitles(
                    video_path=temp_video_path,
                    language_choice=language,
                    model_size=model_size,
                    device=device,
                    topic_hint=topic_hint,
                    pacing=pacing,
                    enable_diarization=enable_diarization
                )
            return results

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


MODEL_DISPLAY_NAMES = {
    "small": "Small (Fast)",
    "medium": "Medium (Recommended)",
    "large-v3-turbo": "Large-v3-Turbo (⚡ ~3s)",
    "large-v3": "Large-V3 (Studio)",
    "indic-conformer": "IndicConformer (AI4Bharat 600M)",
    "sravaani-1.0": "SraVaani 1.0 (ARTPARK-IISc)",
    "sensevoice-small": "SenseVoice-Small (Alibaba)",
}


# Serve static files & index.html with synchronous config injection
@app.get("/")
def read_root():
    import re
    prefs = {
        "selected_model": "large-v3-turbo",
        "selected_language": "mixed",
        "selected_device": "auto",
        "selected_pacing": "short",
        "silent_launch": True,
        "enable_diarization": False,
        "caption_style": resolve_style(DEFAULT_STYLE_ID)
    }
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k in prefs.keys():
                    if k in data:
                        prefs[k] = data[k]
        except Exception:
            pass
    prefs["caption_style"] = resolve_style(prefs.get("caption_style"))

    index_path = os.path.join(STATIC_DIR, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()

    # 1. Inject synchronous initial preferences into <head>
    config_script = f"""<script>
window.__INITIAL_CONFIG__ = {json.dumps(prefs)};
</script>"""
    html = html.replace("<head>", f"<head>\n  {config_script}", 1)

    sel_lang = prefs.get("selected_language", "mixed")
    sel_model = prefs.get("selected_model", "medium")
    if sel_lang == "hi-en" and sel_model not in ("small", "medium", "large-v3"):
        sel_model = "large-v3" if sel_model == "large-v3-turbo" else "medium"
        prefs["selected_model"] = sel_model

    # 2. Update language ribbon tiles active class directly in HTML
    def replace_lang_tile(m):
        full_tag = m.group(0)
        l_name = m.group(1)
        is_active = (l_name == sel_lang)
        classes = "tile active" if is_active else "tile"
        return re.sub(r'class="[^"]*"', f'class="{classes}"', full_tag)

    html = re.sub(r'<button\s+[^>]*data-lang="([^"]+)"[^>]*>', replace_lang_tile, html)

    # 3. Update model pills active class and initial visibility directly in HTML
    def replace_model_pill(m):
        full_tag = m.group(0)
        m_name = m.group(1)
        is_active = (m_name == sel_model)
        should_hide = False
        if sel_lang == "hi-en":
            should_hide = m_name not in ("small", "medium", "large-v3")
        elif sel_lang == "en":
            should_hide = m_name in ("indic-conformer", "sravaani-1.0")

        classes = "pill active" if is_active else "pill"
        new_tag = re.sub(r'class="[^"]*"', f'class="{classes}"', full_tag)
        new_tag = re.sub(r'\s*style="[^"]*"', '', new_tag)
        if should_hide:
            new_tag = new_tag[:-1] + ' style="display: none;">'
        return new_tag

    html = re.sub(r'<button\s+[^>]*data-model="([^"]+)"[^>]*>', replace_model_pill, html)

    # 4. Update device pills active class directly in HTML
    sel_device = prefs.get("selected_device", "auto")
    def replace_device_pill(m):
        full_tag = m.group(0)
        d_name = m.group(1)
        is_active = (d_name == sel_device)
        classes = "pill active" if is_active else "pill"
        return re.sub(r'class="[^"]*"', f'class="{classes}"', full_tag)

    html = re.sub(r'<button\s+[^>]*data-device="([^"]+)"[^>]*>', replace_device_pill, html)

    # 5. Update pacing pills active class directly in HTML
    sel_pacing = prefs.get("selected_pacing", "short")
    def replace_pacing_pill(m):
        full_tag = m.group(0)
        p_name = m.group(1)
        is_active = (p_name == sel_pacing)
        classes = "pill active" if is_active else "pill"
        return re.sub(r'class="[^"]*"', f'class="{classes}"', full_tag)

    html = re.sub(r'<button\s+[^>]*data-pacing="([^"]+)"[^>]*>', replace_pacing_pill, html)

    # 6. Update modelMetaPill text
    if sel_model in MODEL_DISPLAY_NAMES:
        clean_label = MODEL_DISPLAY_NAMES[sel_model]
        html = re.sub(
            r'<span class="meta-pill" id="modelMetaPill">[^<]*</span>',
            f'<span class="meta-pill" id="modelMetaPill">🤖 Whisper: {clean_label}</span>',
            html
        )

    # 7. Update generate button label based on language
    btn_label = "TRANSLATE TO ENGLISH" if sel_lang == "hi-en" else ("GENERATE ENGLISH SUBTITLES" if sel_lang == "en" else "GENERATE HINGLISH SUBTITLES")
    html = re.sub(
        r'(<button class="btn-primary[^"]*" id="generateBtn"[^>]*>[\s\S]*?<svg[^>]*>[\s\S]*?<\/svg>\s*)([A-Z\s➔]+)(\s*<\/button>)',
        rf'\g<1>{btn_label}\g<3>',
        html
    )

    # 8. Cache buster for app.js (matches app.js or app.js?v=...)
    app_js_path = os.path.join(STATIC_DIR, "app.js")
    v_time = int(os.path.getmtime(app_js_path)) if os.path.exists(app_js_path) else 1
    html = re.sub(r'src="app\.js(?:\?v=[^"]*)?"', f'src="app.js?v={v_time}"', html)

    return HTMLResponse(
        content=html,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

app.mount("/", StaticFiles(directory=STATIC_DIR), name="static")


if __name__ == "__main__":
    import uvicorn
    import webbrowser
    import threading
    import subprocess
    import socket

    def find_free_port(start_port=8501, max_tries=30):
        """Finds the first available port starting from start_port."""
        for p in range(start_port, start_port + max_tries):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('127.0.0.1', p))
                    return p
                except OSError:
                    continue
        return start_port

    active_port = find_free_port(8501)

    if "--server-only" in sys.argv:
        print(f"[*] Starting Hinglish Subtitle Server on http://localhost:{active_port} ...")
        uvicorn.run(app, host="127.0.0.1", port=active_port, log_level="info")
        sys.exit(0)

    # Start FastAPI / Uvicorn server in background daemon thread
    server_thread = threading.Thread(
        target=lambda: uvicorn.run(app, host="127.0.0.1", port=active_port, log_level="warning"),
        daemon=True
    )
    server_thread.start()

    def open_browser_fallback(port: int):
        target_url = f"http://localhost:{port}"
        edge_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        ]
        for exe in edge_paths:
            if os.path.isfile(exe):
                subprocess.Popen([
                    exe,
                    f"--app={target_url}",
                    "--window-size=1380,880",
                    "--window-position=100,50"
                ])
                return
        webbrowser.open(target_url)

    # Set explicit AppUserModelID on Windows so taskbar groups under custom app icon instead of python.exe
    icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "app_icon.ico"))
    has_icon = os.path.isfile(icon_path)
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("antigravity.hinglishsubtitles.desktop.v2")
        except Exception:
            pass

    # Launch native standalone desktop window via pywebview (full native H.264/MP4 hardware codecs)
    try:
        import webview

        # Enable file downloads in pywebview WebView2 (defaults to False, which cancels all downloads!)
        webview.settings["ALLOW_DOWNLOADS"] = True

        desktop_api = DesktopAPI()
        window = webview.create_window(
            title="Hinglish Subtitles — Hybrid Pro",
            url=f"http://127.0.0.1:{active_port}",
            width=1380,
            height=880,
            background_color="#0c0d10",
            text_select=False,
            confirm_close=False,
            js_api=desktop_api
        )
        desktop_api.set_window(window)
        cache_storage = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".webview_cache")
        webview.start(private_mode=False, storage_path=cache_storage, icon=icon_path if has_icon else None)
        os._exit(0)
    except Exception as e:
        print(f"[!] pywebview fallback triggered: {e}")
        try:
            from PySide6.QtWidgets import QApplication, QMainWindow
            from PySide6.QtWebEngineWidgets import QWebEngineView
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QColor, QIcon

            qt_app = QApplication.instance() or QApplication(sys.argv)
            if has_icon:
                app_qicon = QIcon(icon_path)
                qt_app.setWindowIcon(app_qicon)

            win = QMainWindow()
            win.setWindowTitle("Hinglish Subtitles — Hybrid Pro")
            if has_icon:
                win.setWindowIcon(app_qicon)
            win.resize(1380, 880)
            view = QWebEngineView(win)
            view.page().setBackgroundColor(QColor("#0c0d10"))

            # Accept download requests in QtWebEngine
            def _on_download_requested(item):
                item.accept()

            view.page().profile().downloadRequested.connect(_on_download_requested)

            view.setUrl(QUrl(f"http://127.0.0.1:{active_port}"))
            win.setCentralWidget(view)
            win.show()
            sys.exit(qt_app.exec())
        except Exception:
            open_browser_fallback(active_port)
            server_thread.join()

