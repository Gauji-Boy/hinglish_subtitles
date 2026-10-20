"""
run_matrix_isolated.py - Runs the required benchmark matrix where EACH configuration
runs in its own independent Python subprocess to prevent CUDA memory fragmentation
and measure pure warm-state performance.
"""

import sys
import os
import subprocess
import json
import time

REELS = [
    {
        "name": "Genius Ad (Dettol vs Savlon)",
        "reel_path": r"C:\Users\susha\Downloads\The-Genius-Ad-SnapYT.App.mp4",
        "golden_path": r"golden\The-Genius-Ad-SnapYT.App.txt"
    },
    {
        "name": "Traffic (Vada Pav)",
        "reel_path": r"C:\Users\susha\Downloads\He-Turned-Traffic-SnapYT.App.mp4",
        "golden_path": r"golden\He-Turned-Traffic-SnapYT.App.txt"
    }
]

CONFIGS = [
    # 1. Baseline
    {"model": "medium", "compute_type": "float16", "beam_size": 5, "label": "medium/float16/beam5 (baseline)"},
    # 2. Anomalous rows under investigation
    {"model": "medium", "compute_type": "int8_float16", "beam_size": 2, "label": "medium/int8_float16/beam2"},
    {"model": "small", "compute_type": "float16", "beam_size": 2, "label": "small/float16/beam2"},
    # 3. Medium beam 2
    {"model": "medium", "compute_type": "float16", "beam_size": 2, "label": "medium/float16/beam2"},
    # 4. Large-v3-turbo
    {"model": "large-v3-turbo", "compute_type": "float16", "beam_size": 2, "label": "large-v3-turbo/float16/beam2"},
    # 5. Greedy decode for 6.5s reconciliation (Genius Ad only)
    {"model": "medium", "compute_type": "float16", "beam_size": 1, "label": "medium/float16/beam1 (reconciliation)"},
]

def main():
    os.makedirs("benchmarks/isolated", exist_ok=True)
    all_results = []

    for cfg in CONFIGS:
        for reel in REELS:
            # If beam 1 reconciliation, only run on Genius Ad
            if cfg.get("beam_size") == 1 and "Genius" not in reel["name"]:
                continue

            print(f"\n=======================================================")
            print(f"Launching ISOLATED run: {cfg['label']} on {reel['name']}")
            print(f"=======================================================")

            cmd = [
                sys.executable,
                "run_single_config.py",
                "--model", cfg["model"],
                "--compute_type", cfg["compute_type"],
                "--beam_size", str(cfg["beam_size"]),
                "--reel_path", reel["reel_path"],
                "--golden_path", reel["golden_path"],
                "--label", cfg["label"]
            ]

            t0 = time.time()
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            elapsed = time.time() - t0

            if proc.returncode != 0:
                print(f"ERROR: process failed with code {proc.returncode}")
                print("STDERR:", proc.stderr)
                continue

            # Parse JSON from stdout
            try:
                # Find JSON block in stdout
                stdout_text = proc.stdout.strip()
                json_start = stdout_text.find("{")
                json_end = stdout_text.rfind("}")
                if json_start != -1 and json_end != -1:
                    data = json.loads(stdout_text[json_start:json_end+1])
                    data["reel_friendly_name"] = reel["name"]
                    data["process_wall_time"] = elapsed
                    all_results.append(data)
                    print(f"SUCCESS: Warm Total = {data['med_total']:.2f}s (Transcribe: {data['med_transcribe']:.2f}s, Audio: {data['med_audio']:.2f}s, Post: {data['med_post']:.2f}s)")
                    print(f"GPU Clocks: {data['clocks_start']}, Compute Apps: {data['concurrent_apps']}")
                    print(f"Fallbacks: {data['total_temperature_fallbacks']}, Segments: {data['avg_segments']:.1f}")
                    print(f"UNVERIFIED WER: {data['wer_unverified']:.1f}%, Named-Tokens: {data['named_token_score']:.1f}% ({data['named_matched']}/{data['named_total']})")
                else:
                    print("Could not find JSON in output:", stdout_text)
            except Exception as e:
                print(f"JSON parse error: {e}")
                print("STDOUT:", proc.stdout)

    out_file = "benchmarks/isolated/isolated_benchmark_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nAll benchmark results saved to {out_file}")

if __name__ == "__main__":
    main()
