import json

with open("benchmarks/isolated/isolated_benchmark_results.json", encoding="utf-8") as f:
    data = json.load(f)

print("| Configuration | Reel | Warm Transcribe | Warm Total | Speed | Clocks | Segs | Fallbacks | UNVERIFIED WER | Named-Tokens |")
print("|---|---|---|---|---|---|---|---|---|---|")
for d in data:
    cfg = d["label"]
    reel = "Genius" if "Genius" in d["reel_friendly_name"] else "Traffic"
    clocks = d["clocks_start"].split(",")[0].strip()
    print(f"| `{cfg}` | {reel} | {d['med_transcribe']:.2f}s | **{d['med_total']:.2f}s** | {d['speed_ratio']:.1f}x | {clocks} | {d['avg_segments']:.1f} | {d['total_temperature_fallbacks']} | **{d['wer_unverified']:.1f}%** | {d['named_token_score']:.1f}% ({d['named_matched']}/{d['named_total']}) |")
