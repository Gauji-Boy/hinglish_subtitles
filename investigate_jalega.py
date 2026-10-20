"""
investigate_jalega.py - TASK 6: Investigate 'jalegaa to chalegaa' span.
Extracts 5s audio span to WAV and dumps Whisper word timestamps and probabilities.
"""
import os
import sys
import subprocess
import numpy as np
from faster_whisper import WhisperModel
from hinglish_engine import extract_audio_numpy

sys.stdout.reconfigure(encoding='utf-8')

video_path = r'C:\Users\susha\Downloads\The-Genius-Ad-SnapYT.App.mp4'
wav_path = os.path.join(os.path.dirname(__file__), 'jalegaa_chalegaa_span.wav')

# Extract 49.0s to 54.0s
cmd = [
    'ffmpeg', '-y', '-ss', '49.0', '-t', '5.0',
    '-i', video_path,
    '-ar', '16000', '-ac', '1',
    wav_path
]
subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
print(f"Extracted 5s span to: {wav_path} (exists: {os.path.exists(wav_path)})")

audio = extract_audio_numpy(wav_path)

for m_name in ['medium', 'small', 'large-v3-turbo']:
    m = WhisperModel(m_name, device='cuda', compute_type='float16')
    segs, info = m.transcribe(audio, language='hi', word_timestamps=True, condition_on_previous_text=False)
    print(f"\n=== Model: {m_name} (language={info.language}, prob={info.language_probability:.2f}) ===")
    for s in segs:
        print(f"Segment [{s.start:.2f}s -> {s.end:.2f}s]: '{s.text.strip()}' (avg_logprob={s.avg_logprob:.3f})")
        if s.words:
            for w in s.words:
                print(f"    Word: '{w.word.strip():15s}' | span: {w.start:.2f}s - {w.end:.2f}s | prob: {w.probability:.4f}")
