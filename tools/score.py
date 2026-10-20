#!/usr/bin/env python3
"""
tools/score.py -- Transcript scoring and alignment against editable golden TSVs.

Rules:
1. Normalizes hypothesis and reference at the exact SAME stage:
   - Unicode NFC normalization
   - Lowercase
   - Punctuation stripped, preserving letters, numbers, and Devanagari combining marks
   - Whitespace collapsed
2. Reports:
   (a) Overall token WER
   (b) English-token accuracy (% of Latin tokens in reference matched in hypothesis)
   (c) Brand/rare-token accuracy (% of rare reference tokens with Zipf < 3.6 matched)
   (d) 5 sample alignments printed for visual sanity check
3. Guard:
   - If fewer than 80% of reference rows have a human 'corrected_text', reports as UNVERIFIED.
4. Self-test:
   - python tools/score.py --self-test must output 0.0% WER.
"""
import os
import sys
import csv
import re
import unicodedata
import argparse
from typing import List, Tuple, Dict, Any, Optional

try:
    from wordfreq import zipf_frequency
except ImportError:
    zipf_frequency = lambda w, lang: 0.0


def normalize_text(text: str) -> str:
    """
    Normalizes transcript text symmetrically:
    - Unicode NFC normalization
    - Lowercase
    - Strip punctuation without splitting Devanagari combining marks (matras, nuktas, halant)
    - Collapse whitespace
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = text.lower()
    # Strip ASCII and unicode punctuation, preserve alphanumeric + devanagari range (\u0900-\u097f) + space
    text = re.sub(r"[^\w\s\u0900-\u097F]", " ", text)
    # Further clean up remaining formatting/symbol punctuation
    text = re.sub(r"[\.,!?:;\-\–\—\"'’‘\(\)\[\]\{\}।॥\/\\_]", " ", text)
    return " ".join(text.split())


def align_tokens(ref_tokens: List[str], hyp_tokens: List[str]) -> Tuple[float, List[Tuple[str, str, str]]]:
    """
    Computes Levenshtein token edit distance and alignment operations.
    Returns: (wer, alignments: List[(ref_token, hyp_token, op)])
    Operations: 'MATCH', 'SUB', 'DEL', 'INS'
    """
    n, m = len(ref_tokens), len(hyp_tokens)
    if n == 0:
        if m == 0:
            return 0.0, []
        return 1.0, [("***", h, "INS") for h in hyp_tokens]

    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ref_tokens[i - 1] == hyp_tokens[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j],        # deletion
                                   dp[i][j - 1],        # insertion
                                   dp[i - 1][j - 1])    # substitution

    # Backtrace alignment path
    i, j = n, m
    alignments = []
    while i > 0 or j > 0:
        if i > 0 and j > 0 and ref_tokens[i - 1] == hyp_tokens[j - 1] and dp[i][j] == dp[i - 1][j - 1]:
            alignments.append((ref_tokens[i - 1], hyp_tokens[j - 1], "MATCH"))
            i -= 1
            j -= 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + 1:
            alignments.append((ref_tokens[i - 1], hyp_tokens[j - 1], "SUB"))
            i -= 1
            j -= 1
        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            alignments.append((ref_tokens[i - 1], "***", "DEL"))
            i -= 1
        else:
            alignments.append(("***", hyp_tokens[j - 1], "INS"))
            j -= 1

    alignments.reverse()
    wer = dp[n][m] / n
    return wer, alignments


def is_latin_word(w: str) -> bool:
    """True if token is primarily Latin characters."""
    return bool(w and w != "***" and w.isascii() and any(c.isalpha() for c in w))


def is_brand_or_rare(w: str) -> bool:
    """True if token is a rare English loanword/brand (Zipf < 3.6)."""
    if not is_latin_word(w):
        return False
    # If rare in English and not a frequent Hindi dictionary word
    zf_en = zipf_frequency(w.lower(), "en")
    zf_hi = zipf_frequency(w.lower(), "hi")
    return zf_en < 3.6 and zf_hi < 3.6


def score_hypothesis(
    reference_text: str,
    hypothesis_text: str,
    print_alignments_count: int = 5
) -> Dict[str, Any]:
    """Scores hypothesis against reference string."""
    norm_ref = normalize_text(reference_text)
    norm_hyp = normalize_text(hypothesis_text)

    ref_tokens = norm_ref.split()
    hyp_tokens = norm_hyp.split()

    wer, alignments = align_tokens(ref_tokens, hyp_tokens)

    # Sub-metrics
    total_latin_ref = 0
    matched_latin = 0

    total_rare_ref = 0
    matched_rare = 0

    for r, h, op in alignments:
        if r != "***" and is_latin_word(r):
            total_latin_ref += 1
            if op == "MATCH":
                matched_latin += 1

        if r != "***" and is_brand_or_rare(r):
            total_rare_ref += 1
            if op == "MATCH":
                matched_rare += 1

    latin_acc = (matched_latin / total_latin_ref * 100.0) if total_latin_ref > 0 else 100.0
    rare_acc = (matched_rare / total_rare_ref * 100.0) if total_rare_ref > 0 else 100.0

    # Pick sample alignments to show
    sample_alignments = []
    # Filter for interesting spans (errors or around matches)
    step = max(1, len(alignments) // print_alignments_count) if alignments else 1
    for k in range(0, len(alignments), step):
        sample_alignments.append(alignments[k:k + 5])
        if len(sample_alignments) >= print_alignments_count:
            break

    return {
        "wer": wer,
        "token_wer_pct": wer * 100.0,
        "ref_token_count": len(ref_tokens),
        "hyp_token_count": len(hyp_tokens),
        "latin_accuracy_pct": latin_acc,
        "total_latin_tokens": total_latin_ref,
        "matched_latin_tokens": matched_latin,
        "brand_rare_accuracy_pct": rare_acc,
        "total_brand_rare_tokens": total_rare_ref,
        "matched_brand_rare_tokens": matched_rare,
        "sample_alignments": sample_alignments,
        "normalized_ref": norm_ref,
        "normalized_hyp": norm_hyp,
    }


def score_tsv(
    tsv_path: str,
    hypothesis_text: Optional[str] = None
) -> Dict[str, Any]:
    """Scores hypothesis against a golden TSV file."""
    if not os.path.exists(tsv_path):
        raise FileNotFoundError(f"Golden TSV not found: {tsv_path}")

    rows = []
    with open(tsv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for r in reader:
            rows.append(r)

    total_rows = len(rows)
    corrected_rows = [r for r in rows if r.get("corrected_text", "").strip()]
    verified_pct = (len(corrected_rows) / total_rows * 100.0) if total_rows > 0 else 0.0

    is_verified = (verified_pct >= 80.0)
    status_label = "VERIFIED" if is_verified else f"UNVERIFIED ({verified_pct:.1f}% corrected rows < 80%)"

    # Build reference text
    if is_verified:
        # Use human corrected text
        ref_text = " ".join(r["corrected_text"].strip() for r in rows)
    else:
        # If unverified, fallback to corrected where available or model_text as baseline seed
        ref_text = " ".join(r.get("corrected_text", "").strip() or r.get("model_text", "").strip() for r in rows)

    if hypothesis_text is None:
        # Default hypothesis is model_text from TSV
        hypothesis_text = " ".join(r.get("model_text", "").strip() for r in rows)

    res = score_hypothesis(ref_text, hypothesis_text)
    res["status"] = status_label
    res["is_verified"] = is_verified
    res["verified_pct"] = verified_pct
    res["total_rows"] = total_rows
    res["corrected_rows"] = len(corrected_rows)
    return res


def run_self_test():
    """Self-test: Scoring any transcript against itself must give 0.0% WER and 100% accuracy."""
    print("[*] Running score.py self-test...")
    test_sentences = [
        "Kaise ek ad ne Dettol ko doobte hue bacha liya.",
        "Dekho market mein Savlon aati hai, aur Dettol ke disadvantage.",
        "Monthly revenue 2 lakh plus in Mumbai India.",
        "और मार्केटिंग, बिलबोर्ड, एड, कैंपेन har jagah chipka diya.",
        "Jalega to chalega tagline Dettol."
    ]
    sample = " ".join(test_sentences)
    res = score_hypothesis(sample, sample)
    assert res["wer"] == 0.0, f"Expected 0.0 WER, got {res['wer']}"
    assert res["token_wer_pct"] == 0.0
    assert res["latin_accuracy_pct"] == 100.0
    assert res["brand_rare_accuracy_pct"] == 100.0
    print("[OK] Self-test passed: WER = 0.0%, Latin Accuracy = 100.0%, Brand Accuracy = 100.0%")
    return True


def main():
    parser = argparse.ArgumentParser(description="Score Hinglish transcript against golden reference TSV")
    parser.add_argument("--tsv", type=str, default="", help="Path to golden TSV")
    parser.add_argument("--hyp", type=str, default="", help="Path to hypothesis text file or string")
    parser.add_argument("--self-test", action="store_true", help="Run self-test and exit")
    args = parser.parse_args()

    if args.self_test:
        run_self_test()
        sys.exit(0)

    if not args.tsv:
        print("Usage: python tools/score.py --tsv golden/<reel>.tsv [--hyp <hyp_file>]")
        print("Or:    python tools/score.py --self-test")
        sys.exit(1)

    hyp_text = None
    if args.hyp:
        if os.path.isfile(args.hyp):
            with open(args.hyp, "r", encoding="utf-8") as f:
                hyp_text = f.read()
        else:
            hyp_text = args.hyp

    results = score_tsv(args.tsv, hyp_text)
    print("\n" + "=" * 60)
    print(f"BENCHMARK SCORE: {os.path.basename(args.tsv)}")
    print(f"STATUS:          {results['status']}")
    print(f"Rows Verified:   {results['corrected_rows']}/{results['total_rows']} ({results['verified_pct']:.1f}%)")
    print(f"Token WER:       {results['token_wer_pct']:.2f}% (Ref tokens: {results['ref_token_count']}, Hyp tokens: {results['hyp_token_count']})")
    print(f"Latin Accuracy:  {results['latin_accuracy_pct']:.1f}% ({results['matched_latin_tokens']}/{results['total_latin_tokens']} Latin tokens)")
    print(f"Brand Accuracy:  {results['brand_rare_accuracy_pct']:.1f}% ({results['matched_brand_rare_tokens']}/{results['total_brand_rare_tokens']} Zipf < 3.6 tokens)")
    print("=" * 60)

    print("\nSample Alignments (Ref vs Hyp):")
    for group in results["sample_alignments"]:
        line_ref = []
        line_hyp = []
        for r, h, op in group:
            mark = "" if op == "MATCH" else f"[{op}]"
            line_ref.append(f"{r}{mark}")
            line_hyp.append(f"{h}{mark}")
        print("  REF: " + " ".join(line_ref))
        print("  HYP: " + " ".join(line_hyp))
        print("-" * 40)


if __name__ == "__main__":
    main()
