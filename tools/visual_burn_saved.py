"""Burn a window from a saved full-clip audit run and extract inspection frames.

Usage:
  python tools/visual_burn_saved.py "I GOT ROASTED BY SAMAY RAINA" 1 834 30
  python tools/visual_burn_saved.py "I GOT ROASTED BY SAMAY RAINA" 1 155 30

The ASS is built from the *saved full-clip cards*, not a fresh slice decode, so
this checks the exact timeline the audit measured.
"""

import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("BENCHMARK_MODE", "1")

import hinglish_engine  # noqa: F401 - CUDA DLL load order
from karaoke_ass import generate_karaoke_ass  # noqa: E402

VIDEOS = r"C:\Users\susha\Downloads\Video"
RUNS = os.path.join(os.environ.get("TEMP", r"C:\Users\susha\AppData\Local\Temp"),
                    "video_audit_fixed")


def main():
    name, run, start, length = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
    end = start + length
    payload = json.load(open(os.path.join(RUNS, name.replace(" ", "_") + "_run%d.json" % run),
                             encoding="utf-8"))
    cards = [c for c in payload["cards"] if c["end"] > start and c["start"] < end]
    clip = name + ".mp4"
    video = os.path.join(VIDEOS, clip)
    work = os.path.join(tempfile.gettempdir(), "visual_fixed", name)
    os.makedirs(work, exist_ok=True)

    style = json.load(open(os.path.join(ROOT, "launch_config.json"), encoding="utf-8")).get(
        "caption_style", {})
    ass = generate_karaoke_ass(cards, script_title="post-fix audit", style=style, aspect="16:9")
    sub = os.path.join(work, "sub.ass")
    with open(sub, "w", encoding="utf-8") as handle:
        handle.write(ass)

    out = os.path.join(work, "burned_%05.1f.mp4" % start)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", video,
           "-ss", str(start), "-t", str(length),
           "-vf", "ass=filename='sub.ass'", "-c:v", "h264_mf", "-b:v", "3M", "-an", out]
    p = subprocess.run(cmd, cwd=work, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    print("burn exit:", p.returncode, p.stderr[-300:] if p.returncode else "")
    if p.returncode:
        return

    print("cards in window:", len(cards))
    for c in cards:
        print("  [%7.2f -> %7.2f] %s" % (c["start"], c["end"], c.get("hinglish_text", c.get("text", ""))))
    chosen = [max(start + 0.1, c["start"] + min(0.35, (c["end"] - c["start"]) / 2))
              for c in cards][:6]
    for i, t in enumerate(chosen):
        if not (start + 0.1 <= t <= end - 0.5):
            continue
        frame = os.path.join(work, "frame_%05.1f.png" % t)
        q = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", out,
                            "-ss", str(t - start), "-frames:v", "1", frame],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        print("frame %.2f:" % t, q.returncode, os.path.exists(frame))
    print("workdir:", work)


if __name__ == "__main__":
    main()
