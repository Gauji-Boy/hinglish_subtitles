"""
hindi_to_english_engine.py - Dedicated Neural Translation Engine (Hindi -> English Subtitles).

Provides a dedicated, isolated pipeline that uses Whisper's multitask translate decoder
to convert spoken Hindi / Hindustani audio directly into natural, grammatically correct
English subtitles without Devanagari transliteration or loanword corruption.
"""

import os
import sys
import time
import inspect
from typing import List, Dict, Any, Callable, Optional, Iterable

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

# Ensure model cache lives on D: drive to protect C: drive disk space
DEFAULT_MODELS_DIR = r"D:\Hinglish_subtitles\models\huggingface"
if not os.environ.get("HF_HOME"):
    os.environ["HF_HOME"] = DEFAULT_MODELS_DIR

from hinglish_engine import extract_audio_numpy, format_srt_timestamp, get_hardware_info
from hinglish_upgrades import (
    get_model,
    single_job,
    semantic_chunk,
    pad_display_times,
    hint_keywords,
    normalize_case,
    clamp_word_span,
    _supported_kwargs
)

try:
    from console_bus import emit_stage
except Exception:
    def emit_stage(s, d): pass


ENGLISH_SUBTITLE_PROMPT = (
    "English subtitles with natural grammar, proper sentence capitalization, and punctuation."
)


@single_job
def generate_english_subtitles(
    video_path: str,
    model_size: str = "medium",
    device: str = "auto",
    compute_type: Optional[str] = None,
    topic_hint: str = "",
    pacing: str = "short",
    enable_diarization: bool = False,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Dict[str, Any]:
    """
    Translates spoken Hindi speech in video/audio directly into English subtitles.
    
    1. Extracts 16kHz mono audio array using ffmpeg
    2. Runs Whisper in task='translate' with an English subtitle prompt (no Devanagari contamination)
    3. Aligns word-level timestamps and clamps spurious duration stretches
    4. Applies English semantic DP chunking and pacing padding
    5. Returns SRT lines, segment objects, and timing telemetry
    """
    start_wall_time = time.time()
    hw = get_hardware_info()

    # Resolve target device and compute_type
    target_device = device.lower()
    if target_device == "auto":
        target_device = "cuda" if hw["cuda_available"] else "cpu"

    target_compute = compute_type
    if not target_compute:
        target_compute = "float16" if target_device == "cuda" else "int8"

    if progress_callback:
        progress_callback(0.05, "Extracting audio with ffmpeg...")

    emit_stage("extract", f"Extracting 16kHz mono audio for English translation from {os.path.basename(video_path)}...")
    t0_extract = time.time()
    audio = extract_audio_numpy(video_path, sampling_rate=16000)
    audio_duration = len(audio) / 16000.0
    t_extract = time.time() - t0_extract
    emit_stage("extract", f"Extracted {audio_duration:.2f}s audio in {t_extract:.2f}s")

    # Translation model compatibility resolution:
    # whisper-large-v3-turbo was distilled with an 8-layer encoder & 4-layer decoder optimized exclusively
    # for speech transcription. The cross-lingual translation head was pruned during distillation,
    # causing task='translate' to collapse back to source-language (Hindi) transcription.
    # Non-Whisper acoustic models (indic-conformer, sravaani-1.0, sensevoice-small) also cannot translate.
    # We resolve them to full multilingual Whisper (large-v3 or medium) for studio-grade English translation.
    active_model_size = model_size
    if model_size == "large-v3-turbo":
        emit_stage("whisper", "Note: large-v3-turbo is distilled for transcription only; routing to full large-v3 for English translation...")
        active_model_size = "large-v3"
    elif model_size in ("indic-conformer", "sravaani-1.0", "sensevoice-small"):
        emit_stage("whisper", f"Note: {model_size} is an acoustic transcription model; routing to medium Whisper for English translation...")
        active_model_size = "medium"

    if progress_callback:
        progress_callback(0.20, f"Loading Whisper ({active_model_size}) on {target_device.upper()} ({target_compute})...")
    emit_stage("whisper", f"Loading Whisper {active_model_size} ({target_compute}) on {target_device.upper()} for Hindi ➔ English translation...")

    # Load cached model instance
    model = get_model(active_model_size, target_device, target_compute)

    if progress_callback:
        progress_callback(0.35, f"Translating Hindi speech to English on {target_device.upper()}...")
    emit_stage("whisper", f"Running Whisper translation (task='translate', language='hi', hint='{topic_hint}')...")

    # Build English translation hotwords from topic/brand hints
    kws = hint_keywords(topic_hint)
    hotwords_str = ", ".join(kws[:30]) if kws else None

    # Verify model parameter support
    params = inspect.signature(model.transcribe).parameters
    prompt = ENGLISH_SUBTITLE_PROMPT
    if "hotwords" not in params and hotwords_str:
        prompt = f"{prompt} Keywords: {hotwords_str}"

    kw = _supported_kwargs(
        model,
        language="hi",
        task="translate",
        initial_prompt=prompt,
        hotwords=hotwords_str if "hotwords" in params else None,
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=400, speech_pad_ms=200, threshold=0.4),
        word_timestamps=True,
        condition_on_previous_text=False,
    )

    segments_gen, info = model.transcribe(audio, **kw)

    # Flatten word list across segments with acoustic duration clamping
    words = []
    for seg in segments_gen:
        for w in (getattr(seg, "words", None) or []):
            t = w.word.strip()
            if t:
                w_start, w_end, tail = clamp_word_span(float(w.start), float(w.end), t)
                word = {"start": w_start, "end": w_end, "text": t}
                if tail > 0:
                    word["tail"] = tail
                words.append(word)

    emit_stage("whisper", f"Whisper translated {len(words)} English word tokens")

    if progress_callback:
        progress_callback(0.75, "Applying English semantic DP chunking and timing padding...")
    emit_stage("cards", f"Structuring English words into {pacing}-mode subtitle cards...")

    # Normalize casing for mid-sentence common words
    words = normalize_case(words)

    # English semantic chunker (no transliteration needed)
    raw_cards = semantic_chunk(words, to_latin=lambda s: s, pacing=pacing)
    reel_cards = pad_display_times(raw_cards, pacing=pacing)

    emit_stage("cards", f"Generated {len(reel_cards)} English subtitle cards ({pacing} mode)")

    if enable_diarization:
        try:
            from diarization import diarize_segments
            emit_stage("diarize", "Clustering speaker voice acoustic embeddings...")
            reel_cards = diarize_segments(audio, reel_cards)
        except Exception as e:
            emit_stage("diarize", f"Diarization note: {e}")

    segments_list = []
    srt_lines = []
    plain_text_lines = []

    for idx, card in enumerate(reel_cards, start=1):
        start_str = format_srt_timestamp(card["start"])
        end_str = format_srt_timestamp(card["end"])
        text = card["text"]
        speaker = card.get("speaker")
        display_text = f"[{speaker}]: {text}" if (enable_diarization and speaker) else text

        segment_data = {
            "index": idx,
            "start": card["start"],
            "end": card["end"],
            "start_str": start_str,
            "end_str": end_str,
            "original_text": display_text,
            "hinglish_text": display_text,  # Populated with English translation for full UI & player compatibility
            "words": [
                {
                    "start": w.get("start", card["start"]),
                    "end": w.get("end", card["end"]),
                    "word": w.get("text", ""),
                    "hinglish": w.get("text", "")
                }
                for w in card.get("words", [])
            ]
        }
        if speaker:
            segment_data["speaker"] = speaker

        segments_list.append(segment_data)

        srt_lines.append(f"{idx}\n{start_str} --> {end_str}\n{display_text}\n")
        plain_text_lines.append(display_text)

    elapsed_time = time.time() - start_wall_time
    speed_factor = audio_duration / elapsed_time if elapsed_time > 0 else 1.0

    if progress_callback:
        progress_callback(1.0, f"Translation complete in {elapsed_time:.1f}s ({speed_factor:.1f}x real-time)!")
    emit_stage("done", f"Hindi ➔ English translation finished in {elapsed_time:.2f}s ({speed_factor:.1f}x real-time)")

    srt_content = "\n".join(srt_lines)

    return {
        "srt_hinglish": srt_content,  # Populated with English translation
        "srt_original": srt_content,
        "segments": segments_list,
        "full_text": "\n".join(plain_text_lines),
        "duration": audio_duration,
        "elapsed_time": elapsed_time,
        "speed_factor": speed_factor,
        "active_device": target_device,
        "active_compute": target_compute,
        "detected_language": "hi➔en"
    }
