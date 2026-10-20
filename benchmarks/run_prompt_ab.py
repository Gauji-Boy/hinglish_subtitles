#!/usr/bin/env python3
"""
benchmarks/run_prompt_ab.py -- A/B/C testing of prompt conditioning across 30s Whisper windows.

Condition A: Current behavior
  initial_prompt = SCRIPT_ANCHOR + STYLE_TEMPLATE
  hotwords = ""

Condition B: Style text passed through hotwords so every window gets it
  initial_prompt = SCRIPT_ANCHOR + STYLE_TEMPLATE
  hotwords = "video, interesting, idea, game, change, follow"

Condition C: Shorter style string in hotwords only
  initial_prompt = SCRIPT_ANCHOR + STYLE_TEMPLATE
  hotwords = "video, idea"

Evaluates per window (Window 1: 0-30s, Window 2: 30-60s):
- Latin tokens count
- Devanagari loanwords that had to be fixed by LoanwordRecoverer
- Fraction of English words emitted directly in Latin script
- Average compression ratio
- Repeated 3-grams count
"""
import os
import sys
import json
import re
from typing import Dict, Any, List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from faster_whisper import WhisperModel
from hinglish_engine import extract_audio_numpy, get_recoverer
from hinglish_upgrades import SCRIPT_ANCHOR, STYLE_TEMPLATE, get_model, _supported_kwargs


REELS = [
    (r"C:\Users\susha\Downloads\The-Genius-Ad-SnapYT.App.mp4", "Genius Ad"),
    (r"C:\Users\susha\Downloads\He-Turned-Traffic-SnapYT.App.mp4", "Traffic")
]

CONDITIONS = {
    "A (Current: hotwords empty)": "",
    "B (Style in hotwords)": "video, interesting, idea, game, change, follow",
    "C (Short style in hotwords)": "video, idea"
}


def count_repeated_ngrams(words: List[str], n: int = 3) -> int:
    if len(words) < n:
        return 0
    seen = set()
    repeats = 0
    for i in range(len(words) - n + 1):
        gram = tuple(words[i:i + n])
        if gram in seen:
            repeats += 1
        else:
            seen.add(gram)
    return repeats


def evaluate_condition(video_path: str, hotwords: str, model, recoverer) -> Dict[str, Any]:
    audio = extract_audio_numpy(video_path)
    initial_prompt = f"{SCRIPT_ANCHOR} {STYLE_TEMPLATE}"

    kw = _supported_kwargs(
        model,
        language="hi",
        initial_prompt=initial_prompt,
        hotwords=hotwords if hotwords else None,
        beam_size=2,
        best_of=2,
        condition_on_previous_text=False,
        word_timestamps=True,
        vad_filter=True,
        temperature=0.0
    )

    segments_gen, info = model.transcribe(audio, **kw)
    raw_segments = list(segments_gen)

    # Split into Window 1 (<= 30.0s) and Window 2 (> 30.0s)
    windows = {1: [], 2: []}
    for seg in raw_segments:
        # Determine window by midpoint or start
        mid = (seg.start + seg.end) / 2.0
        win_idx = 1 if mid <= 30.0 else 2
        windows[win_idx].append(seg)

    win_stats = {}
    for win_idx in [1, 2]:
        segs = windows[win_idx]
        words_list = []
        latin_tokens = 0
        loanwords_recovered = 0
        comp_ratios = []

        for s in segs:
            comp_ratios.append(getattr(s, "compression_ratio", 1.0))
            w_objs = getattr(s, "words", None)
            if w_objs:
                for w in w_objs:
                    txt = w.word.strip()
                    words_list.append(txt)
                    clean = re.sub(r"[^\w]", "", txt)
                    if clean.isascii() and clean.isalpha():
                        latin_tokens += 1
                    elif re.search(r"[\u0900-\u097F]", clean):
                        rec = recoverer.recover(clean)
                        if rec:
                            loanwords_recovered += 1
            else:
                for token in s.text.split():
                    clean = re.sub(r"[^\w]", "", token)
                    words_list.append(clean)
                    if clean.isascii() and clean.isalpha():
                        latin_tokens += 1
                    elif re.search(r"[\u0900-\u097F]", clean):
                        rec = recoverer.recover(clean)
                        if rec:
                            loanwords_recovered += 1

        total_english = latin_tokens + loanwords_recovered
        latin_pct = (latin_tokens / total_english * 100.0) if total_english > 0 else 0.0
        avg_comp = sum(comp_ratios) / len(comp_ratios) if comp_ratios else 1.0
        repeats = count_repeated_ngrams(words_list, n=3)

        win_stats[win_idx] = {
            "segments": len(segs),
            "words_count": len(words_list),
            "latin_tokens": latin_tokens,
            "loanwords_recovered": loanwords_recovered,
            "total_english": total_english,
            "latin_fraction_pct": latin_pct,
            "avg_compression_ratio": avg_comp,
            "repeated_3grams": repeats,
            "full_text": " ".join(s.text.strip() for s in segs)
        }

    return win_stats


def main():
    print("[*] Initializing model large-v3-turbo on CUDA float16...")
    model = get_model("large-v3-turbo", "cuda", "float16")
    recoverer = get_recoverer()

    all_results = {}
    for video_path, reel_name in REELS:
        print(f"\n=======================================================")
        print(f"EVALUATING REEL: {reel_name} ({os.path.basename(video_path)})")
        print(f"=======================================================")
        all_results[reel_name] = {}

        for cond_name, hot_str in CONDITIONS.items():
            print(f"[*] Running condition: {cond_name} (hotwords='{hot_str}')")
            res = evaluate_condition(video_path, hot_str, model, recoverer)
            all_results[reel_name][cond_name] = res

    # Output JSON summary
    out_json = os.path.join(PROJECT_ROOT, "benchmarks", "prompt_ab_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Results written to {out_json}")


if __name__ == "__main__":
    main()
