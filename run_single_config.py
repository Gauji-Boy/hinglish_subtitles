"""
run_single_config.py - Executes one model configuration on one reel in an ISOLATED process.
Logs:
  - GPU clocks (current, max)
  - Other compute processes on GPU
  - Segment count
  - Temperature fallback count (temp > 0.0)
  - Timings: audio, transcribe, post-process, total
  - WER (normalized: lowercase, punctuation stripped)
  - Named-token score (fraction of Latin/English reference tokens matched)
  - Sample alignments
"""
import sys
import os
import re
import json
import time
import argparse
import subprocess
import statistics
from typing import Tuple, List

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

from faster_whisper import WhisperModel
from hinglish_engine import extract_audio_numpy, get_recoverer
from hinglish_upgrades import transcribe_words, words_to_cards
from transliteration import convert_to_hinglish


def get_gpu_info():
    clocks = "Unknown"
    apps = "None"
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=clocks.sm,clocks.max.sm", "--format=csv,noheader"],
            capture_output=True, text=True, check=True
        )
        clocks = res.stdout.strip().replace("\n", "; ")
    except Exception:
        pass

    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory", "--format=csv,noheader"],
            capture_output=True, text=True, check=True
        )
        out = res.stdout.strip()
        apps = out if out else "None (Exclusive)"
    except Exception:
        pass
    return clocks, apps


def normalize_for_eval(text: str) -> str:
    """Lowercase and strip all punctuation."""
    t = text.lower()
    t = re.sub(r"[^\w\s]", " ", t)
    return " ".join(t.split())


def compute_wer(ref_norm: str, hyp_norm: str) -> Tuple[float, List[Tuple[str, str, str]]]:
    ref_words = ref_norm.split()
    hyp_words = hyp_norm.split()
    if not ref_words:
        return (0.0 if not hyp_words else 100.0), []

    r_len, h_len = len(ref_words), len(hyp_words)
    dp = [[0] * (h_len + 1) for _ in range(r_len + 1)]
    back = [[(0, 0, "")] * (h_len + 1) for _ in range(r_len + 1)]

    for i in range(r_len + 1):
        dp[i][0] = i
        back[i][0] = (i - 1, 0, "D")
    for j in range(h_len + 1):
        dp[0][j] = j
        back[0][j] = (0, j - 1, "I")
    back[0][0] = (-1, -1, "")

    for i in range(1, r_len + 1):
        for j in range(1, h_len + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
                back[i][j] = (i - 1, j - 1, "M")
            else:
                sub = dp[i - 1][j - 1] + 1
                ins = dp[i][j - 1] + 1
                dele = dp[i - 1][j] + 1
                best = min(sub, ins, dele)
                dp[i][j] = best
                if best == sub:
                    back[i][j] = (i - 1, j - 1, "S")
                elif best == dele:
                    back[i][j] = (i - 1, j, "D")
                else:
                    back[i][j] = (i, j - 1, "I")

    wer = (dp[r_len][h_len] / r_len) * 100.0

    # Backtrace alignment
    alignments = []
    ci, cj = r_len, h_len
    while ci > 0 or cj > 0:
        pi, pj, op = back[ci][cj]
        r_w = ref_words[pi] if ci > pi and pi >= 0 else ""
        h_w = hyp_words[pj] if cj > pj and pj >= 0 else ""
        alignments.append((op, r_w, h_w))
        ci, cj = pi, pj

    alignments.reverse()
    return wer, alignments


def compute_named_token_score(ref_norm: str, hyp_norm: str) -> Tuple[float, int, int]:
    ref_words = ref_norm.split()
    hyp_set = set(hyp_norm.split())
    # English/Latin tokens in reference (length >= 2, ASCII alphabet)
    ref_latin = [w for w in ref_words if w.isalpha() and ord(w[0]) < 128 and len(w) >= 2]
    if not ref_latin:
        return 100.0, 0, 0
    matched = sum(1 for w in ref_latin if w in hyp_set)
    score = (matched / len(ref_latin)) * 100.0
    return score, matched, len(ref_latin)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--compute_type", required=True)
    parser.add_argument("--beam_size", type=int, default=2)
    parser.add_argument("--reel_path", required=True)
    parser.add_argument("--golden_path", required=True)
    parser.add_argument("--label", default="")
    args = parser.parse_args()

    clocks_start, apps = get_gpu_info()
    rec = get_recoverer()

    # Load golden
    golden_raw = ""
    if os.path.exists(args.golden_path):
        with open(args.golden_path, "r", encoding="utf-8", errors="ignore") as f:
            golden_raw = f.read().strip()
    golden_norm = normalize_for_eval(golden_raw)

    audio = extract_audio_numpy(args.reel_path)
    audio_dur = len(audio) / 16000.0

    # 1. Model Load
    t0 = time.perf_counter()
    model = WhisperModel(args.model, device="cuda", compute_type=args.compute_type)
    t_model_load = time.perf_counter() - t0

    # 2. Warmup: 2 runs (discarded)
    for _ in range(2):
        w_words = transcribe_words(model, audio, language="hi", topic_hint="", beam_size=args.beam_size)
        _ = words_to_cards(w_words, convert_to_hinglish, recoverer=rec, hint_terms=())

    # 3. Measured: 3 runs
    measured_runs = []
    alignments_sample = []

    for run_idx in range(1, 4):
        clocks_run, _ = get_gpu_info()

        # Measure audio extract
        t0 = time.perf_counter()
        _aud = extract_audio_numpy(args.reel_path)
        t_audio = time.perf_counter() - t0

        # Measure transcribe and capture segments & fallbacks
        t0 = time.perf_counter()
        prompt, hot = "", None
        from hinglish_upgrades import build_prompt, _supported_kwargs
        prompt, hot = build_prompt("", ())
        kw = _supported_kwargs(
            model,
            language="hi",
            initial_prompt=prompt,
            hotwords=hot or None,
            task="transcribe",
            beam_size=args.beam_size,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=400, speech_pad_ms=200, threshold=0.4),
            word_timestamps=True,
            condition_on_previous_text=False,
        )
        segs_gen, info = model.transcribe(audio, **kw)
        segs = list(segs_gen)
        t_transcribe = time.perf_counter() - t0

        # Count fallbacks and extract words
        fallback_count = sum(1 for s in segs if getattr(s, "temperature", 0.0) > 0.0)
        seg_count = len(segs)

        words = []
        for s in segs:
            for w in (getattr(s, "words", None) or []):
                t = w.word.strip()
                if t:
                    words.append({"start": float(w.start), "end": float(w.end), "text": t})

        # Measure post-process
        t0 = time.perf_counter()
        cards = words_to_cards(words, convert_to_hinglish, recoverer=rec, hint_terms=())
        t_post = time.perf_counter() - t0

        t_total = t_audio + t_transcribe + t_post

        # Evaluate accuracy
        hyp_raw = " ".join(c["hinglish_text"] for c in cards)
        hyp_norm = normalize_for_eval(hyp_raw)
        wer, aligns = compute_wer(golden_norm, hyp_norm)
        named_score, n_matched, n_total = compute_named_token_score(golden_norm, hyp_norm)

        if not alignments_sample:
            # Capture non-matching alignments for inspection
            alignments_sample = [a for a in aligns if a[0] != "M"][:10]

        measured_runs.append({
            "run": run_idx,
            "t_audio": t_audio,
            "t_transcribe": t_transcribe,
            "t_post": t_post,
            "t_total": t_total,
            "seg_count": seg_count,
            "fallback_count": fallback_count,
            "clocks": clocks_run,
            "wer": wer,
            "named_token_score": named_score,
            "named_matched": n_matched,
            "named_total": n_total,
        })

    med_total = statistics.median(r["t_total"] for r in measured_runs)
    med_transcribe = statistics.median(r["t_transcribe"] for r in measured_runs)
    med_audio = statistics.median(r["t_audio"] for r in measured_runs)
    med_post = statistics.median(r["t_post"] for r in measured_runs)
    med_wer = statistics.median(r["wer"] for r in measured_runs)
    med_named = statistics.median(r["named_token_score"] for r in measured_runs)
    tot_fallbacks = sum(r["fallback_count"] for r in measured_runs)
    avg_segs = statistics.mean(r["seg_count"] for r in measured_runs)

    result_data = {
        "label": args.label or f"{args.model}/{args.compute_type}/beam{args.beam_size}",
        "model": args.model,
        "compute_type": args.compute_type,
        "beam_size": args.beam_size,
        "reel": os.path.basename(args.reel_path),
        "audio_dur": audio_dur,
        "model_load_time": t_model_load,
        "clocks_start": clocks_start,
        "concurrent_apps": apps,
        "avg_segments": avg_segs,
        "total_temperature_fallbacks": tot_fallbacks,
        "med_audio": med_audio,
        "med_transcribe": med_transcribe,
        "med_post": med_post,
        "med_total": med_total,
        "speed_ratio": audio_dur / med_total if med_total > 0 else 0.0,
        "wer_unverified": med_wer,
        "named_token_score": med_named,
        "named_matched": measured_runs[0]["named_matched"],
        "named_total": measured_runs[0]["named_total"],
        "sample_alignments": alignments_sample[:5],
        "measured_runs": measured_runs
    }

    print(json.dumps(result_data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
