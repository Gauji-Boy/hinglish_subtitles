import glob
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

files = glob.glob("logs/decisions_*.tsv")
files.sort(key=os.path.getmtime, reverse=True)

print("Recent Decision Logs (latest 6):")
for f in files[:6]:
    print(f"\n--- {os.path.basename(f)} ---")
    with open(f, encoding="utf-8") as fp:
        lines = [line.strip().split("\t") for line in fp if line.strip()]
        for l in lines[1:]:
            if len(l) >= 7:
                stage, orig, repl, reason = l[1], l[4], l[5], l[6]
                if stage == "unification":
                    print(f"  [UNIFICATION] '{orig}' -> '{repl}' ({reason})")
                elif stage == "casing":
                    print(f"  [CASING] '{orig}' -> '{repl}' ({reason})")
                elif stage == "recovery":
                    print(f"  [RECOVERY] '{orig}' -> '{repl}' ({reason})")
