import sys
import difflib
from faster_whisper import WhisperModel
from hinglish_engine import extract_audio_numpy, get_recoverer
from hinglish_upgrades import transcribe_words, words_to_cards, build_prompt, _supported_kwargs
from transliteration import convert_to_hinglish

sys.stdout.reconfigure(encoding="utf-8")

def get_before_after(reel_path):
    audio = extract_audio_numpy(reel_path)
    model = WhisperModel("medium", device="cuda", compute_type="float16")
    
    # 1. Raw transcription before upgrades (no hotwords, condition_on_prev=False)
    kw = dict(
        language="hi",
        task="transcribe",
        beam_size=2,
        vad_filter=True,
        word_timestamps=True,
        condition_on_previous_text=False,
    )
    segs, _ = model.transcribe(audio, **kw)
    raw_words = []
    for s in segs:
        for w in (getattr(s, "words", None) or []):
            t = w.word.strip()
            if t:
                raw_words.append({"start": float(w.start), "end": float(w.end), "text": t})
                
    # Before upgrades: direct transliteration, no loanword recovery, no unification, no case norm
    before_cards = []
    # simple chunking
    chunk = []
    for w in raw_words:
        chunk.append(w["text"])
        if len(chunk) >= 5:
            txt = " ".join(chunk)
            before_cards.append(convert_to_hinglish(txt))
            chunk = []
    if chunk:
        before_cards.append(convert_to_hinglish(" ".join(chunk)))
    before_text = " ".join(before_cards)

    # 2. After upgrades: full pipeline with zero hint
    rec = get_recoverer()
    prompt, hot = build_prompt("", ())
    kw_up = _supported_kwargs(
        model,
        language="hi",
        initial_prompt=prompt,
        hotwords=hot or None,
        task="transcribe",
        beam_size=2,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=400, speech_pad_ms=200, threshold=0.4),
        word_timestamps=True,
        condition_on_previous_text=False,
    )
    segs_up, _ = model.transcribe(audio, **kw_up)
    up_words = []
    for s in segs_up:
        for w in (getattr(s, "words", None) or []):
            t = w.word.strip()
            if t:
                up_words.append({"start": float(w.start), "end": float(w.end), "text": t})
                
    cards_up = words_to_cards(up_words, convert_to_hinglish, recoverer=rec, hint_terms=())
    after_text = " ".join(c["hinglish_text"] for c in cards_up)

    return before_text, after_text

for name, path in [
    ("Genius Ad (Dettol vs Savlon)", r"C:\Users\susha\Downloads\The-Genius-Ad-SnapYT.App.mp4"),
    ("Traffic (Vada Pav)", r"C:\Users\susha\Downloads\He-Turned-Traffic-SnapYT.App.mp4")
]:
    print(f"\n==========================================")
    print(f"REEL: {name}")
    print(f"==========================================")
    b, a = get_before_after(path)
    b_words = b.split()
    a_words = a.split()
    matcher = difflib.SequenceMatcher(None, b_words, a_words)
    diffs = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            diffs.append((tag, " ".join(b_words[i1:i2]), " ".join(a_words[j1:j2])))
    for tag, orig, repl in diffs:
        print(f"  [{tag.upper()}] '{orig}'  -->  '{repl}'")
