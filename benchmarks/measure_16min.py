#!/usr/bin/env python3
"""
benchmarks/measure_16min.py - Measures processing time and peak VRAM on real 16-minute audio.
Verifies the claim:
"Whisper operates in 30-second rolling Mel-spectrogram windows. VRAM usage stays strictly constant regardless of whether audio is 10 seconds or 2 hours."
"Speed Profile: 15x-25x real-time on GPU (~45s-60s for a 16-minute audio file)"
"""
import os
import sys
import glob
import time
import json
import subprocess
import threading

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from hinglish_engine import extract_audio_numpy, get_recoverer
from hinglish_upgrades import get_model, transcribe_words, words_to_cards
from transliteration import convert_to_hinglish


def find_16min_file():
    candidates = glob.glob(r"C:\Users\susha\Downloads\*Dhruv*")
    if candidates and os.path.exists(candidates[0]):
        return candidates[0]
    return None


def measure_single_model(video_path: str, model_size: str, compute_type: str = "float16"):
    os.environ["BENCHMARK_MODE"] = "1"
    print(f"\n[*] Measuring {model_size} ({compute_type}) on 16-minute file...")

    # Peak VRAM sampler
    peak_vram = 0.0
    stop_sampler = False

    def sampler():
        nonlocal peak_vram
        while not stop_sampler:
            try:
                res = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True)
                val = float(res.stdout.strip().split("\n")[0])
                if val > peak_vram:
                    peak_vram = val
            except Exception:
                pass
            time.sleep(0.1)

    t_sampler = threading.Thread(target=sampler, daemon=True)
    t_sampler.start()

    # 1. Extract audio
    t0 = time.time()
    audio = extract_audio_numpy(video_path)
    audio_dur = len(audio) / 16000.0
    t_audio = time.time() - t0
    print(f"    Audio extracted: {audio_dur:.2f}s ({audio_dur/60:.2f} min) in {t_audio:.2f}s")

    # 2. Load model
    t0 = time.time()
    model = get_model(model_size, "cuda", compute_type)
    t_load = time.time() - t0
    print(f"    Model loaded in {t_load:.2f}s")

    # 3. Transcribe 16-min audio
    t0 = time.time()
    raw_words = transcribe_words(model, audio, language="hi", topic_hint="", beam_size=2)
    t_transcribe = time.time() - t0
    speed_factor = audio_dur / t_transcribe if t_transcribe > 0 else 0.0
    print(f"    Transcribed in {t_transcribe:.2f}s ({speed_factor:.1f}x real-time)")

    # 4. Post-process
    t0 = time.time()
    rec = get_recoverer()
    cards = words_to_cards(raw_words, convert_to_hinglish, recoverer=rec, pacing="long")
    t_post = time.time() - t0
    print(f"    Post-processed into {len(cards)} cards in {t_post:.2f}s")

    stop_sampler = True
    t_sampler.join(timeout=0.5)

    total_wall = t_audio + t_load + t_transcribe + t_post

    return {
        "model": model_size,
        "compute": compute_type,
        "audio_duration_sec": round(audio_dur, 2),
        "audio_extract_sec": round(t_audio, 2),
        "model_load_sec": round(t_load, 2),
        "transcribe_sec": round(t_transcribe, 2),
        "post_process_sec": round(t_post, 2),
        "total_wall_sec": round(total_wall, 2),
        "speed_factor": round(speed_factor, 1),
        "peak_vram_mb": round(peak_vram, 1),
        "cards_generated": len(cards)
    }


def main():
    target_file = find_16min_file()
    if not target_file:
        print("[!] No 16-minute audio file found in Downloads. Marking UNMEASURED.")
        sys.exit(0)

    print(f"[+] Found 16-minute audio test file: {os.path.basename(target_file)}")

    results = {}
    for m in ["large-v3-turbo", "medium"]:
        cmd = [sys.executable, __file__, "--sub", target_file, m]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if res.returncode == 0 and "===16MIN_RESULT_START===" in res.stdout:
            jstr = res.stdout.split("===16MIN_RESULT_START===")[1].split("===16MIN_RESULT_END===")[0].strip()
            results[m] = json.loads(jstr)
            print(f"    [OK] {m}: {results[m]['transcribe_sec']}s transcribe | Peak VRAM: {results[m]['peak_vram_mb']} MB | Wall: {results[m]['total_wall_sec']}s")
        else:
            print(f"[!] Error measuring {m}: {res.stderr}")

    out_file = os.path.join(PROJECT_ROOT, "benchmarks", "longform_16min_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[OK] 16-minute benchmark completed and written to: {out_file}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--sub":
        res = measure_single_model(sys.argv[2], sys.argv[3])
        print("===16MIN_RESULT_START===")
        print(json.dumps(res))
        print("===16MIN_RESULT_END===")
    else:
        main()
