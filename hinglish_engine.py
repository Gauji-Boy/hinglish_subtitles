"""
hinglish_engine.py - Full pipeline for Hinglish subtitle generation with GPU Acceleration.
Extracts audio via ffmpeg directly to numpy array, transcribes with faster-whisper (CUDA/CPU),
and converts Devanagari/Hindi and code-mixed speech into natural Hinglish SRT.
"""

import os
import sys

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

import re
import time
import subprocess
import argparse
from typing import List, Dict, Any, Callable, Optional, Tuple
import numpy as np
from faster_whisper import WhisperModel
from transliteration import convert_to_hinglish


def format_srt_timestamp(seconds: float) -> str:
    """Converts seconds (float) into standard SRT timestamp format: HH:MM:SS,mmm"""
    total_ms = int(round(seconds * 1000))
    hours = total_ms // (3600 * 1000)
    remainder = total_ms % (3600 * 1000)
    minutes = remainder // (60 * 1000)
    remainder = remainder % (60 * 1000)
    secs = remainder // 1000
    ms = remainder % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


_CACHED_HW_INFO = None

def get_hardware_info() -> Dict[str, Any]:
    """Detects available acceleration hardware (CUDA / CPU), caching the result."""
    global _CACHED_HW_INFO
    if _CACHED_HW_INFO is not None:
        return _CACHED_HW_INFO

    result = {
        "cuda_available": False,
        "cuda_devices": 0,
        "recommended_device": "cpu",
        "recommended_compute": "int8",
        "device_name": "CPU"
    }
    try:
        import ctranslate2
        cuda_count = ctranslate2.get_cuda_device_count()
        if cuda_count > 0:
            gpu_name = "NVIDIA GPU (CUDA)"
            try:
                run_kwargs = {"capture_output": True, "text": True, "timeout": 1.5}
                if sys.platform == "win32":
                    run_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                smi = subprocess.run(
                    ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                    **run_kwargs
                )
                if smi.returncode == 0 and smi.stdout.strip():
                    gpu_name = smi.stdout.strip().split("\n")[0]
            except Exception:
                pass

            result = {
                "cuda_available": True,
                "cuda_devices": cuda_count,
                "recommended_device": "cuda",
                "recommended_compute": "float16",
                "device_name": gpu_name
            }
    except Exception:
        pass

    _CACHED_HW_INFO = result
    return result


def extract_audio_numpy(video_path: str, sampling_rate: int = 16000) -> np.ndarray:
    """
    Extracts audio from video directly into a 16kHz mono float32 numpy array using ffmpeg.
    Bypasses PyAV file opening bugs and disk I/O overhead.
    """
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    cmd = [
        "ffmpeg", "-nostdin", "-threads", "0",
        "-i", video_path,
        "-vn",
        "-f", "s16le",
        "-ac", "1",
        "-acodec", "pcm_s16le",
        "-ar", str(sampling_rate),
        "-"
    ]

    run_kwargs = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE}
    if sys.platform == "win32":
        run_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    result = subprocess.run(cmd, **run_kwargs)
    if result.returncode != 0:
        error_msg = result.stderr.decode("utf-8", errors="ignore")
        raise RuntimeError(f"ffmpeg audio extraction failed: {error_msg}")

    # Convert 16-bit signed PCM buffer to normalized float32 (-1.0 to 1.0)
    audio = np.frombuffer(result.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    return audio


# Ensure model cache lives on D: drive to protect C: drive disk space
DEFAULT_MODELS_DIR = r"D:\Hinglish_subtitles\models\huggingface"
if not os.environ.get("HF_HOME"):
    os.environ["HF_HOME"] = DEFAULT_MODELS_DIR

from faster_whisper.utils import download_model

MODEL_SPECS = {
    "small": {"size": "480 MB", "desc": "Fast & low RAM sweet spot"},
    "medium": {"size": "1.5 GB", "desc": "High accuracy (10-13s)"},
    "large-v3-turbo": {"size": "1.6 GB", "desc": "⚡ Ultra fast GPU (~3s) & Studio Precision"},
    "large-v3": {"size": "3.0 GB", "desc": "Studio precision"},
    "indic-conformer": {"size": "2.5 GB", "desc": "AI4Bharat IndicConformer (600M, 22 Indian languages)"},
    "sravaani-1.0": {"size": "908 MB", "desc": "ARTPARK-IISc SraVaani 1.0 (430M, Dialectal & Code-Mixed)"},
    "sensevoice-small": {"size": "1.1 GB", "desc": "Alibaba SenseVoice (15x fast multi-lingual ASR)"},
}


def is_model_cached(model_size: str) -> bool:
    """Checks whether the given Whisper or ASR model is already downloaded locally."""
    try:
        hf_hub = os.path.join(os.environ.get("HF_HOME", DEFAULT_MODELS_DIR), "hub")
        if model_size == "indic-conformer":
            return os.path.isdir(r"D:\Hinglish_subtitles\indic-conformer\assets")
        if model_size == "sravaani-1.0":
            return os.path.isfile(r"D:\Hinglish_subtitles\SraVaani-1.0\model-asr.fp16.ts")
        if model_size == "sensevoice-small":
            return os.path.isdir(os.path.join(hf_hub, "models--FunAudioLLM--SenseVoiceSmall"))
        if model_size == "large-v3-turbo":
            return os.path.isdir(os.path.join(hf_hub, "models--mobiuslabsgmbh--faster-whisper-large-v3-turbo"))
        if model_size in ("small", "medium", "large-v3"):
            return os.path.isdir(os.path.join(hf_hub, f"models--Systran--faster-whisper-{model_size}"))
        download_model(model_size, local_files_only=True)
        return True
    except Exception:
        return False


def get_models_status() -> Dict[str, Any]:
    """Returns download and cache status for all supported Whisper models."""
    status = {}
    for name, spec in MODEL_SPECS.items():
        cached = is_model_cached(name)
        status[name] = {
            "name": name,
            "cached": cached,
            "size": spec["size"],
            "desc": spec["desc"]
        }
    return status




_RECOVERER = None


def get_recoverer():
    """Initializes and caches LoanwordRecoverer with CMUdict and protected words."""
    global _RECOVERER
    if _RECOVERER is None:
        try:
            from hinglish_upgrades import LoanwordRecoverer, load_cmudict_lexicon, hindi_protect_list
            from transliteration import COMMON_LOANWORDS, HINDI_CONVERSATIONAL_MAP
            lex = load_cmudict_lexicon(min_zipf=3.6)
            prot = set(HINDI_CONVERSATIONAL_MAP) | hindi_protect_list()
            cur = set(COMMON_LOANWORDS)
            _RECOVERER = LoanwordRecoverer(lex, protected=prot, curated=cur)
        except Exception as e:
            print(f"[!] Warning: LoanwordRecoverer initialization skipped: {e}")
            _RECOVERER = False
    return _RECOVERER if _RECOVERER else None


_INDIC_CONFORMER_MODEL = None

def get_indic_conformer_model():
    """Lazily loads and caches the AI4Bharat IndicConformer ONNX inference model."""
    global _INDIC_CONFORMER_MODEL
    if _INDIC_CONFORMER_MODEL is None:
        import sys
        conformer_path = r"D:\Hinglish_subtitles\indic-conformer"
        if conformer_path not in sys.path:
            sys.path.insert(0, conformer_path)
        from model_onnx import IndicASRConfig, IndicASRModel
        cfg = IndicASRConfig(ts_folder=conformer_path, FRAME_DURATION_MS=0.08)
        _INDIC_CONFORMER_MODEL = IndicASRModel(cfg)
    return _INDIC_CONFORMER_MODEL


_SRAVAANI_MODEL = None

def get_sravaani_model():
    """Lazily loads and caches the ARTPARK-IISc SraVaani-1.0 model."""
    global _SRAVAANI_MODEL
    if _SRAVAANI_MODEL is None:
        import torch
        from transformers import AutoModel
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        m = AutoModel.from_pretrained(r"D:\Hinglish_subtitles\SraVaani-1.0", trust_remote_code=True)
        _SRAVAANI_MODEL = m.to(dev).eval()
    return _SRAVAANI_MODEL


_SENSEVOICE_MODEL = None

def get_sensevoice_model():
    """Lazily loads and caches the Alibaba SenseVoice-Small model."""
    global _SENSEVOICE_MODEL
    if _SENSEVOICE_MODEL is None:
        import torch
        from funasr import AutoModel
        model_path = r"D:\Hinglish_subtitles\models\huggingface\hub\models--FunAudioLLM--SenseVoiceSmall\snapshots\3847d57b6bdf2dd8875cb1508d2af43d80a16bf7"
        dev = "cuda:0" if torch.cuda.is_available() else "cpu"
        _SENSEVOICE_MODEL = AutoModel(model=model_path, hub="hf", trust_remote_code=True, disable_update=True, device=dev)
    return _SENSEVOICE_MODEL


def generate_subtitles(
    video_path: str,
    language_choice: str = "mixed",
    model_size: str = "medium",
    device: str = "auto",
    compute_type: Optional[str] = None,
    topic_hint: str = "",
    pacing: str = "short",
    enable_diarization: bool = False,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Dict[str, Any]:
    """
    Transcribes video and converts text into Hinglish subtitles with GPU/CPU acceleration.
    Integrates semantic DP chunking, dynamic loanword recovery, brand snapping, and model caching.

    Args:
        video_path: Path to video/audio file (.mp4, .mkv, .mov, .mp3, .wav, etc.)
        language_choice: 'mixed', 'hi', 'en', or 'auto'
        model_size: 'tiny', 'base', 'small', 'medium', 'large-v3'
        device: 'auto', 'cuda', or 'cpu'
        compute_type: 'float16', 'int8_float16', 'int8', or None (auto-picked)
        topic_hint: Optional caption/title/hashtags to guide brand spelling and hotwords
        pacing: 'short' (reels/shorts: 1.0-2.8s) or 'long' (youtube/16:9: 2.0-5.0s)
        progress_callback: Optional callable(fraction, message)

    Returns:
        Dict with 'srt_hinglish', 'srt_original', 'segments', 'full_text', and performance stats
    """
    start_wall_time = time.time()
    hw = get_hardware_info()

    # Resolve target device and compute_type
    target_device = device.lower()
    if target_device == "auto":
        target_device = "cuda" if hw["cuda_available"] else "cpu"

    target_compute = compute_type
    if not target_compute:
        if target_device == "cuda":
            target_compute = "float16"
        else:
            target_compute = "int8"

    if progress_callback:
        progress_callback(0.05, "Extracting audio with ffmpeg...")

    try:
        from console_bus import emit_stage
    except Exception:
        def emit_stage(s, d): pass

    emit_stage("extract", f"Extracting 16kHz mono audio from {os.path.basename(video_path)}...")
    t0_extract = time.time()
    audio = extract_audio_numpy(video_path, sampling_rate=16000)
    audio_duration = len(audio) / 16000.0
    t_extract = time.time() - t0_extract
    emit_stage("extract", f"Extracted {audio_duration:.2f}s ({audio_duration/60:.2f} min) audio in {t_extract:.2f}s")

    whisper_lang = "hi" if language_choice in ("mixed", "hi", "hi-en") else ("en" if language_choice == "en" else None)

    if model_size == "indic-conformer":
        if progress_callback:
            progress_callback(0.20, f"Loading AI4Bharat IndicConformer (600M) ONNX pipeline on {target_device.upper()}...")
        emit_stage("engine", f"Loading IndicConformer ONNX model on {target_device.upper()}...")
        import torch
        conformer = get_indic_conformer_model()

        if progress_callback:
            progress_callback(0.40, f"Running IndicConformer acoustic decoding & CTC word alignment...")
        emit_stage("conformer", "Running CTC acoustic decode & 80ms word boundary alignment...")

        tensor = torch.tensor(audio, dtype=torch.float32).unsqueeze(0)
        target_lang = "hi"
        hyp, ts = conformer.forward(tensor, lang=target_lang, decoding='ctc', compute_timestamps='w')

        words = []
        if ts and len(ts) > 0:
            for item in ts[0]:
                w_text = str(item[0]).strip()
                if w_text:
                    words.append({
                        "start": float(item[1]),
                        "end": float(item[2]),
                        "text": w_text,
                        "word": w_text,
                        "prob": 1.0
                    })
    elif model_size == "sravaani-1.0":
        if progress_callback:
            progress_callback(0.20, f"Loading ARTPARK SraVaani-1.0 on {target_device.upper()}...")
        emit_stage("engine", f"Loading SraVaani-1.0 TorchScript model on {target_device.upper()}...")
        sravaani = get_sravaani_model()

        if progress_callback:
            progress_callback(0.40, "Transcribing with SraVaani-1.0 and extracting word timestamps...")
        emit_stage("sravaani", "Transcribing speech and extracting acoustic word timestamps...")

        hyps = sravaani.transcribe([audio], timestamps=True)
        words = []
        if hyps and hasattr(hyps[0], "timestamp") and "word" in hyps[0].timestamp:
            for item in hyps[0].timestamp["word"]:
                w_text = str(item["word"]).strip()
                if w_text:
                    words.append({
                        "start": float(item["start"]),
                        "end": float(item["end"]),
                        "text": w_text,
                        "word": w_text,
                        "prob": 1.0
                    })
    elif model_size == "sensevoice-small":
        if progress_callback:
            progress_callback(0.20, f"Loading Alibaba SenseVoice-Small on {target_device.upper()}...")
        emit_stage("engine", f"Loading SenseVoice-Small model...")
        sv_model = get_sensevoice_model()

        if progress_callback:
            progress_callback(0.40, "Transcribing with SenseVoice-Small at high speed...")
        emit_stage("sensevoice", "Transcribing with SenseVoice-Small (note: projected timestamps)...")

        from funasr.utils.postprocess_utils import rich_transcription_postprocess
        sv_lang = "en" if language_choice == "en" else "auto"
        res = sv_model.generate(input=audio, language=sv_lang, use_itn=True)
        raw_text = res[0]["text"] if (res and "text" in res[0]) else ""
        clean_text = rich_transcription_postprocess(raw_text)
        clean_text = re.sub(r'[\U00010000-\U0010ffff]', '', clean_text).strip()

        tokens = [w for w in clean_text.split() if w.strip()]
        words = []
        if tokens:
            dur_per_word = max(0.15, audio_duration / len(tokens))
            for i, tok in enumerate(tokens):
                w_start = round(i * dur_per_word, 3)
                w_end = round(min(audio_duration, (i + 1) * dur_per_word), 3)
                words.append({
                    "start": w_start,
                    "end": w_end,
                    "text": tok,
                    "word": tok,
                    "prob": 1.0
                })
    else:
        if progress_callback:
            progress_callback(0.20, f"Loading Whisper model ({model_size}) on {target_device.upper()} ({target_compute})...")
        emit_stage("whisper", f"Loading Whisper {model_size} ({target_compute}) on {target_device.upper()}...")

        from hinglish_upgrades import get_model, transcribe_words
        model = get_model(model_size, target_device, target_compute)

        is_translation = language_choice == "hi-en"
        whisper_lang = "hi" if language_choice in ("mixed", "hi", "hi-en") else ("en" if language_choice == "en" else None)
        whisper_task = "translate" if is_translation else "transcribe"

        if progress_callback:
            mode_desc = "Translating Hindi speech to English" if is_translation else "Transcribing with domain-neutral hotwords"
            progress_callback(0.35, f"{mode_desc} on {target_device.upper()}...")
        emit_stage("whisper", f"Running Whisper {whisper_task} (language='{whisper_lang}', topic_hint='{topic_hint}')...")

        words = transcribe_words(model, audio, language=whisper_lang, topic_hint=topic_hint, task=whisper_task)

    emit_stage("whisper", f"Transcribed {len(words)} raw acoustic tokens")

    from hinglish_upgrades import words_to_cards, hint_keywords
    rec = get_recoverer()
    hint_terms = hint_keywords(topic_hint)

    if progress_callback:
        progress_callback(0.75, "Applying semantic DP chunker and loanword recovery...")
    emit_stage("recover", f"Applying LoanwordRecoverer, variant unification, and casing normalization...")

    reel_cards = words_to_cards(words, convert_to_hinglish, recoverer=rec, hint_terms=hint_terms, reel_name=video_path, pacing=pacing)
    emit_stage("cards", f"Semantic DP chunker generated {len(reel_cards)} subtitle cards ({pacing} mode)")

    if enable_diarization:
        try:
            from diarization import diarize_segments
            emit_stage("diarize", "Clustering speaker voice acoustic embeddings...")
            reel_cards = diarize_segments(audio, reel_cards)
        except Exception as e:
            emit_stage("diarize", f"Diarization note: {e}")

    segments_list = []
    srt_hinglish_lines = []
    srt_orig_lines = []
    plain_text_lines = []

    for idx, card in enumerate(reel_cards, start=1):
        start_str = format_srt_timestamp(card["start"])
        end_str = format_srt_timestamp(card["end"])

        orig_text = card["original_text"]
        hinglish_text = card["hinglish_text"]
        speaker = card.get("speaker")

        if enable_diarization and speaker:
            display_orig = f"[{speaker}]: {orig_text}"
            display_hinglish = f"[{speaker}]: {hinglish_text}"
        else:
            display_orig = orig_text
            display_hinglish = hinglish_text

        segment_data = {
            "index": idx,
            "start": card["start"],
            "end": card["end"],
            "start_str": start_str,
            "end_str": end_str,
            "original_text": display_orig,
            "hinglish_text": display_hinglish,
            "words": card.get("words", [])
        }
        if speaker:
            segment_data["speaker"] = speaker

        segments_list.append(segment_data)

        srt_hinglish_lines.append(f"{idx}\n{start_str} --> {end_str}\n{display_hinglish}\n")
        srt_orig_lines.append(f"{idx}\n{start_str} --> {end_str}\n{display_orig}\n")
        plain_text_lines.append(display_hinglish)

    elapsed_time = time.time() - start_wall_time
    speed_factor = audio_duration / elapsed_time if elapsed_time > 0 else 1.0

    if progress_callback:
        progress_callback(1.0, f"Complete in {elapsed_time:.1f}s ({speed_factor:.1f}x real-time)!")
    emit_stage("done", f"Pipeline completed in {elapsed_time:.2f}s ({speed_factor:.1f}x real-time speed factor)")

    from karaoke_ass import generate_karaoke_ass
    ass_content = generate_karaoke_ass(reel_cards, script_title=f"Hinglish Subtitles - {os.path.basename(video_path)}")

    return {
        "srt_hinglish": "\n".join(srt_hinglish_lines),
        "srt_original": "\n".join(srt_orig_lines),
        "ass_karaoke": ass_content,
        "segments": segments_list,
        "full_text": "\n".join(plain_text_lines),
        "duration": audio_duration,
        "elapsed_time": elapsed_time,
        "speed_factor": speed_factor,
        "active_device": target_device,
        "active_compute": target_compute,
        "detected_language": whisper_lang
    }


def main():
    parser = argparse.ArgumentParser(description="Generate Hinglish subtitles for videos with GPU Acceleration.")
    parser.add_argument("video_path", help="Path to input video file")
    parser.add_argument("-o", "--output", help="Output .srt file path", default=None)
    parser.add_argument("-m", "--model", choices=["small", "medium", "large-v3-turbo", "large-v3"], default="small", help="Whisper model size")
    parser.add_argument("-l", "--lang", choices=["mixed", "hi", "en", "auto"], default="mixed", help="Spoken language mode")
    parser.add_argument("-d", "--device", choices=["auto", "cuda", "cpu"], default="auto", help="Compute device")
    parser.add_argument("-c", "--compute", choices=["float16", "int8_float16", "int8"], default=None, help="Compute precision type")
    parser.add_argument("-t", "--topic", help="Optional topic/brand hint words (e.g. caption or hashtags)", default="")

    args = parser.parse_args()

    out_file = args.output
    if not out_file:
        base, _ = os.path.splitext(args.video_path)
        out_file = f"{base}_hinglish.srt"

    hw = get_hardware_info()
    print(f"[+] Hardware: {hw['device_name']}")
    print(f"[+] Processing video: {args.video_path}")
    print(f"[+] Model: {args.model} | Lang: {args.lang} | Device: {args.device} | Topic Hint: {args.topic or 'None'}")

    def console_progress(pct, msg):
        print(f"[{int(pct*100):3d}%] {msg}")

    result = generate_subtitles(
        video_path=args.video_path,
        language_choice=args.lang,
        model_size=args.model,
        device=args.device,
        compute_type=args.compute,
        topic_hint=args.topic,
        progress_callback=console_progress
    )

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(result["srt_hinglish"])

    print(f"\n[DONE] Hinglish SRT successfully written to: {out_file}")
    print(f"[STATS] Duration: {result['duration']:.1f}s | Processed in: {result['elapsed_time']:.1f}s ({result['speed_factor']:.1f}x real-time) on {result['active_device'].upper()}")


if __name__ == "__main__":
    main()
