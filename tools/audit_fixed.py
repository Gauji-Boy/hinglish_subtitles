"""Post-fix audit harness: full-pipeline decode, saved intermediates, invariants.

Usage:
  python tools/audit_fixed.py --repeat 3
  python tools/audit_fixed.py --clip "I GOT ROASTED BY SAMAY RAINA.mp4" --repeat 3
  python tools/audit_fixed.py --seconds 60 --clip "...mp4"   # smoke test

Import hinglish_engine before hinglish_upgrades or CUDA fails to load cublas64_12.dll.
"""

import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
os.environ.setdefault("BENCHMARK_MODE", "1")

import hinglish_engine as he  # noqa: E402 - CUDA DLL load order
import hinglish_upgrades as hu  # noqa: E402
from transliteration import convert_to_hinglish  # noqa: E402
from measure_timing import _ass_chain_starts  # noqa: E402

VIDEOS = r"C:\Users\susha\Downloads\Video"
DEFAULT_CLIPS = [
    "I GOT ROASTED BY SAMAY RAINA.mp4",
    "Instagram showed me my AUKAAT.mp4",
    "Is This The DualSense Killer_ Cosmic Byte Sensa.mp4",
    "MY BIGGEST ANNOUNCEMENT EVER.mp4",
]
DEFAULT_OUT = os.path.join(os.environ.get("TEMP", r"C:\Users\susha\AppData\Local\Temp"),
                           "video_audit_fixed")


def covered_by(word, cards):
    start, end = float(word["start"]), float(word["end"])
    return any(min(end, c["end"]) - max(start, c["start"]) > 0.005 for c in cards)


def audit(name, model, out_dir, run_idx, seconds=None, hint=""):
    clip = os.path.join(VIDEOS, name)
    print("START", name, "run", run_idx, flush=True)
    t0 = time.time()
    audio = he.extract_audio_numpy(clip, 16000)
    if seconds:
        audio = audio[: int(seconds * 16000)]
    duration = len(audio) / 16000.0
    words, cov = hu.transcribe_words(model, audio, language="hi",
                                     topic_hint=hint, task="transcribe")
    cards = hu.words_to_cards(words, convert_to_hinglish, he.get_recoverer(),
                              (), name, "short")
    regions = hu.speech_regions(audio, sampling_rate=16000)
    speech_s = sum(b - a for a, b in regions)

    sorted_words = sorted(words, key=lambda w: (w["start"], w["end"]))
    zero_span = sum(1 for w in words if w["end"] <= w["start"])
    overlaps = sum(1 for a, b in zip(sorted_words, sorted_words[1:])
                   if b["start"] < a["end"] - 0.02)
    early_cards = []
    for c in cards:
        if c["words"] and c["words"][-1]["end"] > c["end"] + 0.005:
            early_cards.append(round((c["words"][-1]["end"] - c["end"]) * 1000))
    orphans = sum(1 for w in words if w["end"] > w["start"] and not covered_by(w, cards))

    ass_outliers = []
    for c in cards:
        for index, replay, true_start in _ass_chain_starts(c):
            if index > 0 and abs((replay - true_start) * 1000) > 20:
                ass_outliers.append(round((replay - true_start) * 1000))

    # The production visible-hole pass uses density=0. The 40% default would
    # hide a real 3.8 s hole with 1.51 s of speech, so the gate must match it.
    word_holes = hu.find_speech_gaps(words, regions, duration, min_gap=2.0, density=0.0)
    card_holes = hu.find_speech_gaps(cards, regions, duration, min_gap=2.0, density=0.0)
    voiced_fractions = []
    for c in cards:
        voiced = sum(max(0.0, min(c["end"], b) - max(c["start"], a)) for a, b in regions)
        voiced_fractions.append(round(voiced / max(0.001, c["end"] - c["start"]), 3))

    metrics = {
        "clip": name, "run": run_idx, "seconds_window": seconds,
        "duration": round(duration, 2), "elapsed_s": round(time.time() - t0, 1),
        "words": len(words), "cards": len(cards),
        "covered_ratio": cov.get("covered_ratio"),
        "gaps_filled": cov.get("gaps_filled"), "gaps_skipped": cov.get("gaps_skipped"),
        "tail_attempted": cov.get("tail_attempted"),
        "tail_recovered_s": cov.get("tail_recovered_s"),
        "zero_span_words": zero_span, "word_overlaps": overlaps,
        "cards_ending_early": len(early_cards),
        "cards_early_over_100ms": sum(1 for x in early_cards if x > 100),
        "cards_early_max_ms": max(early_cards, default=0),
        "orphan_word_spans": orphans,
        "ass_chain_over_20ms": len(ass_outliers),
        "ass_chain_max_ms": max((abs(x) for x in ass_outliers), default=0),
        "word_holes_2s": len(word_holes),
        "card_holes_2s": len(card_holes),
        "card_max_hole_s": round(max((b - a for a, b in card_holes), default=0), 2),
        "card_holes": [[round(a, 2), round(b, 2)] for a, b in card_holes],
        "card_voiced_fraction_p10": sorted(voiced_fractions)[len(voiced_fractions) // 10]
                                    if voiced_fractions else None,
        "cards_below_20pct_voiced": sum(1 for v in voiced_fractions if v < 0.2),
        "speech_s": round(speech_s, 1),
    }
    os.makedirs(out_dir, exist_ok=True)
    safe = name.replace(".mp4", "").replace(" ", "_") + "_run%d.json" % run_idx
    payload = dict(metrics, words=words, cards=cards, regions=regions,
                   coverage=cov, word_holes=word_holes, card_holes=card_holes)
    with open(os.path.join(out_dir, safe), "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1)
    print("DONE", json.dumps(metrics, ensure_ascii=False), flush=True)
    ok = (metrics["card_holes_2s"] == 0 and metrics["zero_span_words"] == 0
          and metrics["word_overlaps"] == 0 and metrics["cards_ending_early"] == 0
          and metrics["orphan_word_spans"] == 0
          and metrics["ass_chain_over_20ms"] == 0)
    print("INVARIANTS", "PASS" if ok else "FAIL", flush=True)
    return metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--clip", action="append", default=None)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--seconds", type=float, default=None)
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args()

    model = hu.get_model("large-v3-turbo", "cuda", "float16")
    for name in args.clip or DEFAULT_CLIPS:
        for i in range(1, args.repeat + 1):
            audit(name, model, args.out, i, seconds=args.seconds)
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
