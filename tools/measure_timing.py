"""Measure caption timing against real audio (read-only, opt-in).

Runs one clip through the shipping pipeline and reports:

  1. ASR word starts vs acoustic energy onsets  -> is the transcript late/early?
  2. Card starts vs onsets                      -> does chunking shift anything?
  3. ASS karaoke \\k chain vs true word starts    -> will the burn drift?
  4. format_ass_time round-trip                 -> centisecond rounding error
  5. Simulated timeupdate-only paint delay       -> the old overlay latency

Item 5 is the number the frame-clock change removes: the live overlay no longer
waits for a `timeupdate` tick, so the expected delay drops from ~90-140 ms to
one frame. Items 1-3 should not change when timing code is refactored.

Usage:
    python tools/measure_timing.py [clip.mp4 ...]

With no arguments it uses the two benchmark reels from benchmark.py. The run
prints ASCII only and writes nothing into the repo.
"""

from __future__ import annotations

import json
import math
import os
import statistics
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Keep the decision-log TSV out of the repo while measuring.
os.environ.setdefault("BENCHMARK_MODE", "1")

MODEL = "large-v3-turbo"

DEFAULT_CLIPS = [
    r"C:\Users\susha\Downloads\The-Genius-Ad-SnapYT.App.mp4",
    r"C:\Users\susha\Downloads\He-Turned-Traffic-SnapYT.App.mp4",
]


def _pct(values, p):
    if not values:
        return float("nan")
    ordered = sorted(values)
    k = (len(ordered) - 1) * p / 100.0
    lo, hi = math.floor(k), math.ceil(k)
    return ordered[int(k)] if lo == hi else ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def _stats(values):
    if not values:
        return {}
    return {
        "n": len(values),
        "median": round(statistics.median(values), 1),
        "mean": round(statistics.fmean(values), 1),
        "p10": round(_pct(values, 10), 1),
        "p90": round(_pct(values, 90), 1),
        "min": round(min(values), 1),
        "max": round(max(values), 1),
    }


def _nearest(seconds, series):
    best = None
    for value in series:
        delta = seconds - value
        if best is None or abs(delta) < abs(best):
            best = delta
    return best


def _onsets(audio, hop=160):
    """Energy-rise onsets: a fresh crossing after >=30 ms of quiet."""
    import numpy as np

    frames = len(audio) // hop
    db = 20.0 * np.log10(
        np.sqrt(np.mean(audio[: frames * hop].reshape(frames, hop) ** 2, axis=1)) + 1e-9
    )
    noise = float(np.percentile(db, 20))
    loud = float(np.percentile(db, 90))
    threshold = noise + 0.35 * max(1.0, loud - noise)

    found, quiet_run = [], 99
    for i, level in enumerate(db):
        quiet_run = 0 if level > threshold else quiet_run + 1
        if quiet_run == 0 and i > 4 and db[i - 1] <= threshold and db[i - 3] <= threshold:
            t = i * hop / 16000.0
            if not found or t - found[-1] > 0.10:
                found.append(round(t, 3))
    return found, noise, loud, threshold


def _ass_chain_starts(card):
    """Replay the \\k chain exactly as libass does."""
    elapsed = float(card["start"])
    starts = []
    for index, word in enumerate(card.get("words", [])):
        dur = max(1, int(round((word["end"] - word["start"]) * 100)))
        gap = int(round((word["start"] - elapsed) * 100))
        if gap > 0:
            elapsed += gap / 100.0
        starts.append((index, elapsed, word["start"]))
        elapsed += dur / 100.0
    return starts


def measure(clip):
    print()
    print("=" * 72)
    print(os.path.basename(clip))
    print("=" * 72)

    from hinglish_engine import extract_audio_numpy, get_recoverer
    import hinglish_upgrades as hu
    from karaoke_ass import format_ass_time, generate_karaoke_ass
    from transliteration import convert_to_hinglish

    audio = extract_audio_numpy(clip, 16000)
    duration = len(audio) / 16000.0

    model = hu.get_model(MODEL, "cuda", "float16")
    prompt, hot = hu.build_prompt("", ())
    kwargs = hu._supported_kwargs(
        model,
        language="hi",
        initial_prompt=prompt,
        hotwords=hot or None,
        task="transcribe",
        beam_size=5,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=400, speech_pad_ms=200, threshold=0.4),
        word_timestamps=True,
        condition_on_previous_text=False,
    )

    raw = []
    for segment in model.transcribe(audio, **kwargs)[0]:
        for word in (getattr(segment, "words", None) or []):
            text = word.word.strip()
            if text:
                raw.append({"start": float(word.start), "end": float(word.end), "text": text})

    words, stretched = [], []
    for word in raw:
        start, end, tail = hu.clamp_word_span(word["start"], word["end"], word["text"])
        entry = {"start": start, "end": end, "text": word["text"]}
        if tail > 0:
            entry["tail"] = tail
            stretched.append((word["text"], round(start, 2), round(word["end"], 2), round(tail, 2)))
        words.append(entry)

    print("duration %.1fs | %d words | %d DTW-stretched tokens" % (duration, len(words), len(stretched)))

    onsets, noise, loud, threshold = _onsets(audio)
    print("energy: noise %.1f dB, speech %.1f dB, threshold %.1f dB, %d onsets"
          % (noise, loud, threshold, len(onsets)))

    # 1. word starts
    word_bias, times = [], []
    for word in words:
        delta = _nearest(word["start"], onsets)
        if delta is None or abs(delta) > 0.25:
            continue
        word_bias.append(round(delta * 1000))
        times.append(word["start"])
    print("\n[1] word start vs acoustic onset (ms, + = caption late)")
    print("   ", json.dumps(_stats(word_bias)))
    print("    unmatched: %d / %d" % (len(words) - len(word_bias), len(words)))
    if len(word_bias) > 3:
        mt, mb = statistics.fmean(times), statistics.fmean(word_bias)
        num = sum((t - mt) * (b - mb) for t, b in zip(times, word_bias))
        den = sum((t - mt) ** 2 for t in times)
        if den:
            print("    drift: %.1f ms/s (r=%.2f)" % (num / den, num / math.sqrt(den * sum((b - mb) ** 2 for b in word_bias)) or 0.0))

    # 2. cards
    recoverer = get_recoverer()
    cards = hu.words_to_cards(words, convert_to_hinglish, recoverer, (), "measure", "short")
    card_bias = []
    for card in cards:
        delta = _nearest(card["start"], onsets)
        if delta is not None and abs(delta) <= 0.35:
            card_bias.append(round(delta * 1000))
    print("\n[2] %d cards | card start vs onset (ms)" % len(cards))
    print("   ", json.dumps(_stats(card_bias)))

    # 3. ASS chain
    ass = generate_karaoke_ass(cards, script_title="measure")
    chain_bias = []
    for card in cards:
        for index, replay, true_start in _ass_chain_starts(card):
            if index > 0:
                chain_bias.append(round((replay - true_start) * 1000))
    over = [b for b in chain_bias if abs(b) > 20]
    print("\n[3] ASS \\k chain vs true word start (ms, + = highlight late)")
    print("   ", json.dumps(_stats(chain_bias)))
    print("    over 20 ms: %d / %d" % (len(over), len(chain_bias)))

    # 4. centisecond round-trip
    worst = 0.0
    for card in cards:
        for value in (card["start"], card["end"]):
            text = format_ass_time(value)
            h, m, rest = text.split(":")
            s, cs = rest.split(".")
            back = int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100.0
            worst = max(worst, abs(back - value))
    print("\n[4] format_ass_time round-trip worst error: %.1f ms" % (worst * 1000))

    # 5. old overlay delay (what the frame clock replaces)
    delays = [round((math.ceil(c["start"] * 4.0 - 1e-9) / 4.0 - c["start"]) * 1000) for c in cards]
    print("\n[5] timeupdate-only paint delay (ms) - fixed by the frame clock")
    print("   ", json.dumps(_stats(delays)))

    if stretched:
        print("\nDTW-stretched tokens (capped, tail held):")
        for token in stretched:
            print("    %-18s %6.2f -> raw end %6.2f, tail %5.2fs" % token)

    return {
        "words": _stats(word_bias),
        "cards": _stats(card_bias),
        "ass": _stats(chain_bias),
        "ass_over_20ms": len(over),
        "ass_total": len(chain_bias),
        "ass_roundtrip_ms": round(worst * 1000, 1),
        "old_delay": _stats(delays),
    }


def main(argv):
    clips = argv[1:] or [p for p in DEFAULT_CLIPS if os.path.isfile(p)]
    if not clips:
        print("No clips found. Pass one or more video paths.")
        return 2
    results = {os.path.basename(clip): measure(clip) for clip in clips}
    print("\n" + "=" * 72)
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
