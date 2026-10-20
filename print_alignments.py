import json

with open("benchmarks/isolated/isolated_benchmark_results.json", encoding="utf-8") as f:
    data = json.load(f)

for d in [data[0], data[1]]:
    print(f"\n=== {d['label']} on {d['reel_friendly_name']} ===")
    print(f"WER (UNVERIFIED): {d['wer_unverified']:.1f}%")
    for op, ref, hyp in d['sample_alignments']:
        print(f"  [{op}] ref='{ref}' <---> hyp='{hyp}'")
