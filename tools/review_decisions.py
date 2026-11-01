"""
review_decisions.py - Inspect lexical decisions (recovery, unification, casing)
and optionally add words to protected_extra.txt.
"""
import os
import sys
import glob
import argparse

sys.stdout.reconfigure(encoding="utf-8")


def list_log_files(log_dir: str = "logs"):
    if not os.path.exists(log_dir):
        return []
    files = glob.glob(os.path.join(log_dir, "decisions_*.tsv"))
    files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return files


def read_tsv(filepath: str):
    rows = []
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        header = f.readline().strip().split("\t")
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 7:
                rows.append({
                    "timestamp": parts[0],
                    "stage": parts[1],
                    "start": float(parts[2]),
                    "end": float(parts[3]),
                    "original": parts[4],
                    "replaced": parts[5],
                    "reason": parts[6],
                })
    return rows


def print_decisions_table(rows, filename=""):
    print("=" * 80)
    print(f" DECISION LOG: {os.path.basename(filename) if filename else 'Combined'}")
    print("=" * 80)

    by_stage = {}
    for r in rows:
        by_stage.setdefault(r["stage"], []).append(r)

    print("\n[Summary by Stage]")
    for stg, items in by_stage.items():
        print(f"  - {stg:15s}: {len(items)} decisions")

    print("\n[Detailed Decisions]")
    print(f"{'TIME':12s} | {'STAGE':12s} | {'SPAN':13s} | {'ORIGINAL':18s} -> {'REPLACED':18s} | {'REASON'}")
    print("-" * 95)
    for r in rows:
        span = f"{r['start']:.2f}-{r['end']:.2f}s"
        print(f"{r['timestamp'][-8:]:12s} | {r['stage']:12s} | {span:13s} | {r['original']:18s} -> {r['replaced']:18s} | {r['reason']}")
    print("=" * 80)


def add_to_protected(word: str, target_file: str = "protected_extra.txt"):
    word = word.strip()
    if not word:
        return
    existing = set()
    if os.path.isfile(target_file):
        with open(target_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    existing.add(line)
    if word in existing:
        print(f"'{word}' is already in {target_file}")
        return
    with open(target_file, "a", encoding="utf-8") as f:
        f.write(word + "\n")
    print(f"Added '{word}' to {target_file}")


def main():
    parser = argparse.ArgumentParser(description="Inspect subtitle generator lexical decisions.")
    parser.add_argument("--file", help="Path to specific decisions TSV file")
    parser.add_argument("--all", action="store_true", help="Inspect all log files combined")
    parser.add_argument("--protect", help="Append a Hindi word to protected_extra.txt")
    parser.add_argument("--list", action="store_true", help="List available decision logs")
    args = parser.parse_args()

    if args.protect:
        add_to_protected(args.protect)
        return

    log_files = list_log_files()

    if args.list:
        print(f"Found {len(log_files)} decision log(s):")
        for f in log_files:
            print("  ", f)
        return

    if not log_files and not args.file:
        print("No decision logs found in logs/ directory.")
        return

    target_files = []
    if args.file:
        target_files = [args.file]
    elif args.all:
        target_files = log_files
    else:
        target_files = [log_files[0]]

    for tf in target_files:
        rows = read_tsv(tf)
        print_decisions_table(rows, tf)


if __name__ == "__main__":
    main()
