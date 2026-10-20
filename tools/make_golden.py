#!/usr/bin/env python3
"""
tools/make_golden.py -- Exports editable TSV reference transcripts per reel.

Each row represents one subtitle card:
    start    end    model_text    corrected_text

Rules:
- model_text is seeded from the best current pipeline configuration (large-v3-turbo, float16, zero hints).
- corrected_text starts empty. Until filled by human listening, the row is UNVERIFIED.
- If the TSV already exists with human corrections, existing corrected_text entries are preserved.
"""
import os
import sys
import csv
import argparse
from typing import List, Dict, Any

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from hinglish_engine import generate_subtitles


DEFAULT_REELS = [
    r"C:\Users\susha\Downloads\The-Genius-Ad-SnapYT.App.mp4",
    r"C:\Users\susha\Downloads\He-Turned-Traffic-SnapYT.App.mp4"
]


def load_existing_corrections(tsv_path: str) -> Dict[str, str]:
    """Loads existing human corrections keyed by start timestamp string."""
    corrections = {}
    if not os.path.exists(tsv_path):
        return corrections
    try:
        with open(tsv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                start = row.get("start", "").strip()
                corr = row.get("corrected_text", "").strip()
                if start and corr:
                    corrections[start] = corr
    except Exception as e:
        print(f"[!] Warning reading existing {tsv_path}: {e}")
    return corrections


def export_golden_tsv(
    video_path: str,
    output_tsv: str,
    model_size: str = "large-v3-turbo",
    compute_type: str = "float16",
    pacing: str = "short"
) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(output_tsv)), exist_ok=True)
    existing_corr = load_existing_corrections(output_tsv)

    print(f"[*] Transcribing {os.path.basename(video_path)} with {model_size} ({compute_type}, zero hints)...")
    res = generate_subtitles(
        video_path=video_path,
        language_choice="mixed",
        model_size=model_size,
        device="cuda",
        compute_type=compute_type,
        topic_hint="",
        pacing=pacing
    )

    segments = res.get("segments", [])
    if not segments:
        print(f"[!] No segments produced for {video_path}")
        return output_tsv

    rows = []
    for s in segments:
        start_str = f"{s['start']:.2f}"
        end_str = f"{s['end']:.2f}"
        model_text = s.get("hinglish_text", "").strip() or s.get("text", "").strip()
        # Preserve existing manual correction if timestamp matches
        corr = existing_corr.get(start_str, "")
        rows.append({
            "start": start_str,
            "end": end_str,
            "model_text": model_text,
            "corrected_text": corr
        })

    with open(output_tsv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["start", "end", "model_text", "corrected_text"], delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    verified_count = sum(1 for r in rows if r["corrected_text"])
    total_count = len(rows)
    pct = (verified_count / total_count * 100) if total_count else 0
    print(f"[OK] Written {len(rows)} cards to {output_tsv} ({verified_count}/{total_count} verified - {pct:.1f}%)")
    return output_tsv


def main():
    parser = argparse.ArgumentParser(description="Export editable golden TSV for subtitle review")
    parser.add_argument("--video", type=str, default="", help="Specific video path to process")
    parser.add_argument("--out", type=str, default="", help="Specific output TSV path")
    parser.add_argument("--model", type=str, default="large-v3-turbo")
    parser.add_argument("--compute", type=str, default="float16")
    parser.add_argument("--pacing", type=str, default="short")
    args = parser.parse_args()

    golden_dir = os.path.join(PROJECT_ROOT, "golden")
    os.makedirs(golden_dir, exist_ok=True)

    if args.video:
        out_path = args.out or os.path.join(golden_dir, f"{os.path.splitext(os.path.basename(args.video))[0]}.tsv")
        export_golden_tsv(args.video, out_path, model_size=args.model, compute_type=args.compute, pacing=args.pacing)
    else:
        for v in DEFAULT_REELS:
            if os.path.exists(v):
                stem = os.path.splitext(os.path.basename(v))[0]
                out_path = os.path.join(golden_dir, f"{stem}.tsv")
                export_golden_tsv(v, out_path, model_size=args.model, compute_type=args.compute, pacing=args.pacing)
            else:
                print(f"[!] Warning: test reel not found: {v}")


if __name__ == "__main__":
    main()
