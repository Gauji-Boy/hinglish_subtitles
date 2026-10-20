"""
hinglish_upgrades.py -- drop-in upgrades for hinglish_engine.py

Covers the four questions in the dossier:
  1. Prompting / vocabulary conditioning   -> build_prompt(), transcribe_words()
  2. English loanword recovery             -> LoanwordRecoverer
  3. Semantic reel chunking                -> semantic_chunk(), pad_display_times()
  4. Speed / VRAM                          -> get_model() (cached), tuned transcribe kwargs

Optional pip installs (all small, all offline after install):
    pip install cmudict wordfreq
Without `cmudict` the loanword recoverer is disabled (everything else still works).
"""
from __future__ import annotations

import os
import time
import inspect
import re
import unicodedata
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

# =============================================================================
# DECISION LOGGING (logs/decisions_<reel>_<timestamp>.tsv)
# =============================================================================
DECISION_LOG: List[Dict[str, Any]] = []


def record_decision(stage: str, original: str, replaced: str, reason: str,
                    start: float = 0.0, end: float = 0.0) -> None:
    """Record a lexical recovery, unification, or casing decision."""
    if os.environ.get("BENCHMARK_MODE") == "1":
        return
    DECISION_LOG.append({
        "stage": stage,
        "original": original,
        "replaced": replaced,
        "reason": reason,
        "start": start,
        "end": end,
    })


def export_decisions(reel_name: str = "reel", log_dir: str = "logs") -> Optional[str]:
    """Writes accumulated decisions to logs/decisions_<reel>_<timestamp>.tsv and clears the log."""
    global DECISION_LOG
    if os.environ.get("BENCHMARK_MODE") == "1" or not DECISION_LOG:
        DECISION_LOG = []
        return None
    try:
        os.makedirs(log_dir, exist_ok=True)
        clean_reel = re.sub(r"[^\w\-]", "_", os.path.splitext(os.path.basename(reel_name))[0])
        ts = time.strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(log_dir, f"decisions_{clean_reel}_{ts}.tsv")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("timestamp\tstage\tstart\tend\toriginal\treplaced\treason\n")
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            for d in DECISION_LOG:
                f.write(f"{now}\t{d['stage']}\t{d['start']:.2f}\t{d['end']:.2f}\t{d['original']}\t{d['replaced']}\t{d['reason']}\n")
        DECISION_LOG = []
        return filepath
    except Exception:
        return None


# =============================================================================
# 4. MODEL CACHE  (the engine currently re-creates WhisperModel on every request)
# =============================================================================
_MODELS: Dict[Tuple[str, str, str], object] = {}


def get_model(size: str, device: str, compute_type: str):
    """Load once, reuse for every request. Model load is seconds you pay per reel today."""
    from faster_whisper import WhisperModel  # imported lazily so tests don't need it

    key = (size, device, compute_type)
    if key not in _MODELS:
        # One model at a time: two sizes on a 6 GB card can exhaust VRAM.
        _MODELS.clear()
        _MODELS[key] = WhisperModel(size, device=device, compute_type=compute_type)
    return _MODELS[key]


# =============================================================================
# 1. PROMPTING
# =============================================================================
# Script anchor: short, Devanagari, NO topic words. Keeps Whisper out of Urdu script.
SCRIPT_ANCHOR = "नमस्ते दोस्तों, यह वीडियो हिंदी और English मिलाकर बोला गया है।"

# Style template: natural Hinglish where English words sit in Latin script inside a
# Devanagari sentence. This teaches the *format* (English stays English) without
# biasing any domain. Keep generic words only.
STYLE_TEMPLATE = (
    "ये video बहुत interesting है। Basically एक simple idea ने पूरा game change कर दिया, "
    "और अब सब लोग उसे follow करते हैं।"
)


def hint_keywords(text: str, limit: int = 25) -> List[str]:
    """Pull candidate vocabulary out of a caption/title/hashtags the user pastes (best signal there is)."""
    if not text:
        return []
    text = text.replace("#", " ")
    seen, out = set(), []
    for tok in re.findall(r"[A-Za-z][A-Za-z0-9'&-]{2,}|[\u0900-\u097F]{3,}", text):
        k = tok.lower()
        if k not in seen:
            seen.add(k)
            out.append(tok)
    return out[:limit]


def build_prompt(topic_hint: str = "", extra_keywords: Iterable[str] = ()) -> Tuple[str, str]:
    """
    Returns (initial_prompt, hotwords).

    initial_prompt = script anchor + style template  (domain-neutral, always safe)
    hotwords       = caption/hint terms + discovered terms (domain-specific, optional)

    Why two channels: in faster-whisper, initial_prompt is a first-window prompt; with
    condition_on_previous_text=False it is dropped for later 30 s windows. `hotwords` is
    re-inserted for every window. Verify on your installed version (see notes in the reply).
    """
    kws: List[str] = []
    for k in list(hint_keywords(topic_hint)) + list(extra_keywords):
        if k.lower() not in {x.lower() for x in kws}:
            kws.append(k)
    return f"{SCRIPT_ANCHOR} {STYLE_TEMPLATE}", ", ".join(kws[:30])


def _supported_kwargs(model, **kw):
    """Drop kwargs this faster-whisper version doesn't know (e.g. older builds lack `hotwords`)."""
    params = inspect.signature(model.transcribe).parameters
    return {k: v for k, v in kw.items() if k in params}


def transcribe_words(model, audio, language: Optional[str] = "hi",
                     topic_hint: str = "", extra_keywords: Iterable[str] = (),
                     beam_size: int = 5, task: str = "transcribe") -> List[dict]:
    """Single transcription pass -> ONE flat word list across all segments (no per-segment reset)."""
    prompt, hot = build_prompt(topic_hint, extra_keywords)
    params = inspect.signature(model.transcribe).parameters
    if "hotwords" not in params and hot:
        # Fallback for older faster-whisper versions that lack hotwords
        prompt = f"{prompt} {hot}".strip()

    kw = _supported_kwargs(
        model,
        language=language,
        initial_prompt=prompt,
        hotwords=hot or None,
        task=task,
        beam_size=beam_size,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=400, speech_pad_ms=200, threshold=0.4),
        word_timestamps=True,
        condition_on_previous_text=False,
    )
    segments, info = model.transcribe(audio, **kw)
    words = []
    for seg in segments:
        for w in (getattr(seg, "words", None) or []):
            t = w.word.strip()
            if t:
                w_start = float(w.start)
                w_end = float(w.end)
                # Word-level duration clamp: in natural speech, a single word never lasts > 2.5s.
                # If DTW cross-attention stretches a trailing token across a silence/music break,
                # clamp the acoustic span so it doesn't artificially freeze on screen.
                if w_end - w_start > 2.5:
                    w_end = round(w_start + min(w_end - w_start, max(1.0, len(t) * 0.15 + 0.6)), 3)
                words.append({"start": w_start, "end": w_end, "text": t})
    return words


def discover_keywords(model, audio, seconds: float = 25.0, language: str = "hi") -> List[str]:
    """
    OPTIONAL cheap pass 1: greedy decode of the first ~25 s, harvest Latin-script tokens
    Whisper already got right. Helps *context*; it cannot rescue a brand Whisper has never
    heard (it will mishear it the same way). A user caption is a stronger signal.
    """
    clip = audio[: int(seconds * 16000)]
    kw = _supported_kwargs(
        model, language=language, initial_prompt=f"{SCRIPT_ANCHOR} {STYLE_TEMPLATE}",
        beam_size=1, vad_filter=True, without_timestamps=True,
        condition_on_previous_text=False,
    )
    segs, _ = model.transcribe(clip, **kw)
    text = " ".join(s.text for s in segs)
    freq: Dict[str, int] = {}
    for tok in re.findall(r"[A-Za-z][A-Za-z'-]{3,}", text):
        freq[tok] = freq.get(tok, 0) + 1
    return [t for t, _ in sorted(freq.items(), key=lambda kv: -kv[1])][:15]


# =============================================================================
# 2. LOANWORD RECOVERY  (Devanagari -> English spelling, no hand-written dictionary)
# =============================================================================
# Idea: Devanagari is almost phonemic. Convert the Devanagari token to a rough phoneme
# string, find English words whose CMUdict pronunciation is close (accent-aware costs),
# and accept only when (a) the token is not a known Hindi word and (b) the match is tight.

_CONS = {
    "क": "K", "ख": "K", "ग": "G", "घ": "G", "ङ": "NG", "च": "CH", "छ": "CH", "ज": "JH", "झ": "JH",
    "ञ": "N", "ट": "T", "ठ": "T", "ड": "D", "ढ": "D", "ण": "N", "त": "T", "थ": "T", "द": "D",
    "ध": "D", "न": "N", "प": "P", "फ": "F", "ब": "B", "भ": "B", "म": "M", "य": "Y", "र": "R",
    "ल": "L", "व": "V", "श": "SH", "ष": "SH", "स": "S", "ह": "HH", "ळ": "L",
}
_NUKTA = {"ज": "Z", "फ": "F", "ड": "R", "ढ": "R"}
_IND_VOWEL = {"अ": "AX", "आ": "AA", "इ": "IH", "ई": "IY", "उ": "UH", "ऊ": "UW", "ऋ": "R IH",
              "ए": "EY", "ऐ": "AE", "ओ": "OW", "औ": "AO", "ऑ": "AO", "ऍ": "AE"}
_MATRA = {"ा": "AA", "ि": "IH", "ी": "IY", "ु": "UH", "ू": "UW", "ृ": "R IH", "े": "EY",
          "ै": "AE", "ो": "OW", "ौ": "AO", "ॉ": "AO", "ॅ": "AE"}
_VOWELS = {"AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY", "IH", "IY", "OW", "OY", "UH", "UW", "AX"}
_SOFT_VOWEL_SETS = [
    {"AA", "AO", "AH", "AX", "OW", "AW"}, {"IH", "IY", "AX", "EH", "EY"},
    {"UH", "UW", "OW", "AX"}, {"EH", "EY", "AE", "AY", "AX"}, {"AY", "AA", "AE", "EY"}, {"OY", "OW", "AO"},
]
_CLASS = {  # coarse consonant skeleton (voicing / place folded) for fast candidate retrieval
    "P": "p", "B": "p", "F": "p", "V": "p", "W": "p", "T": "t", "D": "t", "TH": "t", "DH": "t",
    "K": "k", "G": "k", "CH": "s", "JH": "s", "S": "s", "Z": "s", "SH": "s", "ZH": "s",
    "M": "m", "N": "n", "NG": "n", "L": "l", "R": "r", "Y": "y", "HH": "h",
}


def deva_to_phones(word: str) -> List[str]:
    """Rough Devanagari -> ARPAbet-like phones. Inherent schwa = 'AX' (cheap to skip later)."""
    s = unicodedata.normalize("NFD", word)
    out: List[str] = []
    pending = False
    i = 0
    while i < len(s):
        ch = s[i]
        nxt = s[i + 1] if i + 1 < len(s) else ""
        if ch in _CONS:
            if pending:
                out.append("AX")
            ph = _CONS[ch]
            if nxt == "\u093c":  # nukta
                ph = _NUKTA.get(ch, ph)
                i += 1
            out.append(ph)
            pending = True
        elif ch in _MATRA:
            pending = False
            out.extend(_MATRA[ch].split())
        elif ch == "\u094d":  # halant
            pending = False
        elif ch in _IND_VOWEL:
            if pending:
                out.append("AX")
                pending = False
            out.extend(_IND_VOWEL[ch].split())
        elif ch in ("\u0902", "\u0901"):  # anusvara / chandrabindu: nasal takes the place of the next consonant
            if pending:
                out.append("AX")
                pending = False
            out.append("M" if nxt and nxt in "पफबभम" else "NG" if nxt and nxt in "कखगघ" else "N")
        elif ch == "\u0903" or ch == "\u093c":
            pass
        i += 1
    if out[-2:] == ["NG", "G"]:  # word-final -ंग is just /ŋ/ (marketing, shopping)
        out = out[:-1]
    return out  # a trailing inherent schwa is never emitted (schwa deletion)


def _skeleton(phones: Sequence[str]) -> str:
    return "".join(_CLASS[p] for p in phones if p in _CLASS)


def _sub_cost(q: str, c: str) -> float:
    if q == c:
        return 0.0
    qv, cv = q in _VOWELS, c in _VOWELS
    if qv and cv:
        if "AX" in (q, c):
            return 0.15
        return 0.15 if any(q in s and c in s for s in _SOFT_VOWEL_SETS) else 0.45
    if qv != cv:
        return 1.5
    if {q, c} <= {"V", "W"}:
        return 0.0
    if {q, c} in ({"T", "TH"}, {"D", "DH"}):
        return 0.1
    if _CLASS.get(q) and _CLASS.get(q) == _CLASS.get(c):
        return 0.25
    return 1.0


def _indel_cost(p: str) -> float:
    if p == "AX":
        return 0.1
    if p in _VOWELS:
        return 0.45
    if p == "Y":
        return 0.3
    if p in ("N", "NG", "HH"):
        return 0.5
    return 0.9


def phone_distance(q: Sequence[str], c: Sequence[str]) -> float:
    """Weighted edit distance, normalised by the longer non-schwa length (0 = identical)."""
    n, m = len(q), len(c)
    prev = [0.0] * (m + 1)
    for j in range(1, m + 1):
        prev[j] = prev[j - 1] + _indel_cost(c[j - 1])
    for i in range(1, n + 1):
        cur = [prev[0] + _indel_cost(q[i - 1])] + [0.0] * m
        for j in range(1, m + 1):
            cur[j] = min(prev[j - 1] + _sub_cost(q[i - 1], c[j - 1]),
                         prev[j] + _indel_cost(q[i - 1]),
                         cur[j - 1] + _indel_cost(c[j - 1]))
        prev = cur
    denom = max(1, max(sum(p != "AX" for p in q), len(c)))
    return prev[m] / denom


def _expand_cmu(phones: Sequence[str]) -> List[str]:
    out: List[str] = []
    for p in phones:
        stress = re.sub(r"\D", "", p)
        p = re.sub(r"\d", "", p)
        if p == "AH" and stress == "0":
            p = "AX"
        if p == "ER":
            out.extend(["AX", "R"])
        else:
            out.append(p)
    return out


def load_cmudict_lexicon(min_zipf: float = 3.6) -> Dict[str, List[str]]:
    """English word -> phones. Filters to common words with wordfreq (if installed)."""
    import cmudict  # pip install cmudict

    try:
        from wordfreq import zipf_frequency
    except Exception:
        zipf_frequency = None
    lex: Dict[str, List[str]] = {}
    for w, prons in cmudict.dict().items():
        if not w.isalpha() or len(w) < 3:
            continue
        if zipf_frequency and zipf_frequency(w, "en") < min_zipf:
            continue
        lex[w] = _expand_cmu(prons[0])
    return lex


_HINDI_INFLECTION = re.compile(r"(ते|ता|ती|गा|गे|गी|ेगा|ेगी|रहा|रही|रहे|से|ने|को|का|के|की|में|पर|वा|वाया|वाये|वायी)$")


def _has_english_signal(word: str) -> bool:
    """Spelling habits that almost only occur in Devanagari-written English."""
    if re.search(r"[ऑॉऍॅ]", word):
        return True
    if re.search(r"िंग$", word):
        return True
    if re.search(r"[\u095b\u095e]|ज़|फ़", word):
        return True
    return False


def hindi_protect_list(n: int = 25000, extra_file: str = "protected_extra.txt") -> Set[str]:
    """Top-n Hindi words (Devanagari) from wordfreq: real Hindi that must never be 'recovered' as English.
    Tokens with an English spelling signal (ऑ, -िंग, ज़/फ़) bypass this protection.
    Also loads extra words from protected_extra.txt if present."""
    words: Set[str] = set()
    try:
        from wordfreq import top_n_list
        words = set(top_n_list("hi", n))
    except Exception:
        pass

    for candidate in [extra_file, os.path.join(os.path.dirname(__file__), extra_file)]:
        if os.path.isfile(candidate):
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            words.add(line)
            except Exception:
                pass
            break
    return words


class LoanwordRecoverer:
    """
    lexicon  : {english_word: [phones]}  (see load_cmudict_lexicon)
    protected: set of Devanagari words that are real Hindi -> never converted
               (pass set(transliteration.HINDI_CONVERSATIONAL_MAP) | your own)
    curated  : Devanagari words your hand-written COMMON_LOANWORDS already handles -> always skipped,
               so the curated dictionary stays the first trust layer (pass set(COMMON_LOANWORDS))
    """

    def __init__(self, lexicon: Dict[str, List[str]], protected: Optional[Set[str]] = None,
                 curated: Optional[Set[str]] = None,
                 accept_with_signal: float = 0.34, accept_plain: float = 0.07, min_phones: int = 4):
        self.lex = lexicon
        self.protected = protected or set()
        self.curated = curated or set()
        self.t_sig, self.t_plain, self.min_phones = accept_with_signal, accept_plain, min_phones
        # SymSpell-style delete-1 index on the consonant skeleton => cheap candidate retrieval
        self.exact: Dict[str, List[str]] = {}
        self.dele: Dict[str, List[str]] = {}
        for w, ph in lexicon.items():
            sk = _skeleton(ph)
            if not sk:
                continue
            self.exact.setdefault(sk, []).append(w)
            for k in range(len(sk)):
                self.dele.setdefault(sk[:k] + sk[k + 1:], []).append(w)
        self._cache: Dict[str, Optional[str]] = {}
        self.decisions: List[Tuple[str, str]] = []  # (devanagari, english) -- review this to grow `protected`

    def _candidates(self, sk: str) -> Set[str]:
        cands: Set[str] = set(self.exact.get(sk, ()))
        cands.update(self.dele.get(sk, ()))                       # candidate has 1 extra consonant
        for k in range(len(sk)):                                   # query has 1 extra consonant
            cands.update(self.exact.get(sk[:k] + sk[k + 1:], ()))
        return cands

    def recover(self, deva_word: str) -> Optional[str]:
        """Return an English word for a Devanagari token, or None (leave it to the transliterator)."""
        if deva_word in self._cache:
            return self._cache[deva_word]
        res = self._recover(deva_word)
        self._cache[deva_word] = res
        return res

    def _recover(self, w: str) -> Optional[str]:
        core = re.sub(r"[^\u0900-\u097F]", "", w)
        signal = _has_english_signal(core)
        if not core or core in self.curated:
            return None
        if not signal and (core in self.protected or _HINDI_INFLECTION.search(core)):
            return None
        phones = deva_to_phones(core)
        if sum(p != "AX" for p in phones) < self.min_phones and not signal:
            return None
        sk = _skeleton(phones)
        if len(sk) < 2:
            return None
        deva_ends_vowel = bool(re.search(r"[\u093e-\u094c\u094e\u094f\u0955-\u0957]$", core))
        best: List[Tuple[float, str]] = []
        for cand in self._candidates(sk):
            cand_ph = self.lex[cand]
            if not signal:
                cand_ends_vowel = cand_ph[-1] in _VOWELS
                if cand_ends_vowel != deva_ends_vowel:
                    continue
            best.append((phone_distance(phones, cand_ph), cand))
        if not best:
            return None
        best.sort()
        score, word = best[0]
        limit = self.t_sig if signal else self.t_plain
        if score > limit:
            return None
        if len(best) > 1 and best[1][0] - score < 0.02 and best[1][1] != word:
            # near-tie between different words: keep the shorter lexicon-closest one (already sorted);
            # ties are rare once the candidate set is skeleton-filtered.
            pass
        return word

    def merge_split_words(self, words: List[dict], max_gap: float = 0.15) -> List[dict]:
        """Heal 'रेवे'+'न्यू' style splits: join neighbours when the *joined* phones match an English word."""
        out: List[dict] = []
        i = 0
        while i < len(words):
            w = words[i]
            if i + 1 < len(words):
                n = words[i + 1]
                a = re.sub(r"[^\u0900-\u097F]", "", w["text"])
                b = re.sub(r"[^\u0900-\u097F]", "", n["text"])
                if a and b and n["start"] - w["end"] <= max_gap:
                    joined = deva_to_phones(a) + deva_to_phones(b)
                    sk = _skeleton(joined)
                    if len(sk) >= 3:
                        scored = sorted((phone_distance(joined, self.lex[c]), c) for c in self._candidates(sk))
                        if scored and scored[0][0] <= 0.15:
                            out.append({"start": w["start"], "end": n["end"], "text": scored[0][1]})
                            i += 2
                            continue
            out.append(w)
            i += 1
        return out

    def apply(self, words: List[dict]) -> List[dict]:
        """Full word-level pass: heal splits, then swap Devanagari loanwords for English spelling."""
        words = self.merge_split_words(words)
        res = []
        for w in words:
            if re.search(r"[\u0900-\u097F]", w["text"]):
                eng = self.recover(w["text"])
                if eng:
                    self.decisions.append((w["text"], eng))
                    record_decision("recovery", w["text"], eng, "cmu_phoneme_match",
                                    w.get("start", 0.0), w.get("end", 0.0))
                    tail = re.search(r"[.,!?।]+$", w["text"])
                    w = dict(w, text=eng + (tail.group(0) if tail else ""))
            res.append(w)
        return res


# --- brand / proper-noun snapping (words NOT in CMUdict, e.g. Dettol, Savlon) ---------
def _latin_skeleton(term: str) -> str:
    t = term.lower()
    for a, b in (("ph", "f"), ("th", "t"), ("sh", "s"), ("ch", "s"), ("ck", "k"), ("x", "ks"), ("qu", "kw")):
        t = t.replace(a, b)
    t = re.sub(r"c(?=[ei])", "s", t)
    t = t.replace("c", "k").replace("q", "k").replace("j", "s")
    m = {"b": "p", "f": "p", "v": "p", "w": "p", "p": "p", "d": "t", "t": "t", "g": "k", "k": "k", "z": "s", "s": "s",
         "m": "m", "n": "n", "l": "l", "r": "r", "y": "y", "h": "h"}
    return "".join(m[ch] for ch in t if ch in m)


def _edit1(a: str, b: str) -> bool:
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) <= 1
    if len(a) > len(b):
        a, b = b, a
    return any(b[:i] + b[i + 1:] == a for i in range(len(b)))


def snap_to_terms(words: List[dict], terms: Iterable[str]) -> List[dict]:
    """
    Replace Devanagari tokens whose consonant skeleton is within 1 edit of a hint term
    (from the user's caption) with that term's exact spelling. 'दिटाल' -> 'Dettol'.
    Requires same first consonant class and >=3 consonants to avoid false hits.
    """
    index = [(t, _latin_skeleton(t)) for t in terms]
    index = [(t, s) for t, s in index if len(s) >= 3]
    res = []
    for w in words:
        core = re.sub(r"[^\u0900-\u097F]", "", w["text"])
        if core:
            sk = _skeleton(deva_to_phones(core))
            for t, ts in index:
                if len(sk) >= 3 and sk[0] == ts[0] and _edit1(sk, ts):
                    record_decision("brand_snap", w["text"], t, "caption_hint",
                                    w.get("start", 0.0), w.get("end", 0.0))
                    tail = re.search(r"[.,!?।]+$", w["text"])
                    w = dict(w, text=t + (tail.group(0) if tail else ""))
                    break
        res.append(w)
    return res


def _word_edit_dist(s1: str, s2: str) -> int:
    """Standard Levenshtein distance on characters."""
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    return dp[m][n]


_COMMON_FUNCTION_WORDS = {
    "to", "do", "in", "on", "is", "us", "at", "it", "an", "as", "be", "by", "he", "if",
    "me", "my", "no", "or", "so", "up", "we", "the", "and", "for", "are", "but", "not",
    "you", "all", "any", "can", "had", "her", "was", "one", "our", "out", "day", "get",
    "has", "him", "his", "how", "man", "new", "now", "old", "see", "two", "way", "who",
    "boy", "did", "its", "let", "put", "say", "she", "too", "use", "with", "from", "that",
    "this", "have", "here", "were", "will", "your", "they", "them", "then", "than"
}


def unify_variants(words: List[dict],
                   min_freq: int = 1,
                   protected: Optional[Set[str]] = None,
                   lexicon: Optional[Dict[str, Any]] = None) -> List[dict]:
    """
    1. Clusters inconsistent Latin variants across the reel (e.g. 'Detol' / 'DTOL' / 'Dettol').
    2. Cross-script snaps Devanagari tokens to established Latin brands in the same reel.
    Guarded against short words and false positives.
    """
    if protected is None:
        protected = set(hindi_protect_list())
    try:
        from wordfreq import zipf_frequency
    except Exception:
        zipf_frequency = lambda w, lang: 0.0

    # Step 1: Collect Latin tokens
    latin_freq: Dict[str, int] = {}
    latin_words: Dict[str, str] = {}
    for w in words:
        clean = re.sub(r"^[^\w]+|[^\w]+$", "", w["text"])
        if clean.isalpha() and ord(clean[0]) < 128 and len(clean) >= 3:
            k = clean.lower()
            if k in _COMMON_FUNCTION_WORDS:
                continue
            latin_freq[k] = latin_freq.get(k, 0) + 1
            if k not in latin_words or (clean[0].isupper() and not latin_words[k][0].isupper()):
                latin_words[k] = clean

    # Step 2: Cluster Latin spelling variants
    clusters: List[Set[str]] = []
    keys = list(latin_freq.keys())
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            k1, k2 = keys[i], keys[j]
            if min(len(k1), len(k2)) >= 4 or (len(k1) >= 3 and len(k2) >= 3 and abs(len(k1) - len(k2)) <= 1):
                sk1 = _latin_skeleton(k1)
                sk2 = _latin_skeleton(k2)
                if sk1 and sk2 and (sk1 == sk2 or _edit1(sk1, sk2)):
                    max_d = 2 if max(len(k1), len(k2)) >= 6 else 1
                    if abs(len(k1) - len(k2)) <= max_d:
                        d = _word_edit_dist(k1, k2)
                        if d <= max_d:
                            merged = False
                            for c in clusters:
                                if k1 in c or k2 in c:
                                    c.add(k1)
                                    c.add(k2)
                                    merged = True
                                    break
                            if not merged:
                                clusters.append({k1, k2})

    # Pick canonical form for each cluster
    latin_map: Dict[str, str] = {}
    for c in clusters:
        def rank_candidate(k):
            orig = latin_words[k]
            freq = latin_freq[k]
            zf = zipf_frequency(k, "en")
            is_title = orig[0].isupper() and not orig.isupper()
            return (freq, zf, is_title, len(k))

        best_k = sorted(c, key=rank_candidate, reverse=True)[0]
        canonical = latin_words[best_k]
        for k in c:
            if k != best_k:
                latin_map[k] = canonical
                record_decision("unification", latin_words[k], canonical, f"cluster_canonical_freq={latin_freq[best_k]}")

    # Step 3: Build Latin brand index for cross-script snapping
    brand_index: List[Tuple[str, str]] = []
    for k, freq in sorted(latin_freq.items(), key=lambda kv: -kv[1]):
        zf = zipf_frequency(k, "en")
        # Only brands / proper nouns / rare terms (zipf < 3.8) are candidates for cross-script snapping
        if zf < 3.8:
            canonical = latin_map.get(k, latin_words[k])
            sk = _latin_skeleton(canonical)
            if len(sk) >= 3 and (canonical, sk) not in brand_index:
                brand_index.append((canonical, sk))

    # Step 4: Apply to all words
    out = []
    for w in words:
        t = w["text"]
        clean = re.sub(r"^[^\w]+|[^\w]+$", "", t)
        if clean.lower() in latin_map:
            canonical = latin_map[clean.lower()]
            tail = re.search(r"[.,!?।]+$", t)
            new_text = canonical + (tail.group(0) if tail else "")
            out.append(dict(w, text=new_text))
            continue

        core_deva = re.sub(r"[^\u0900-\u097F]", "", t)
        if core_deva and core_deva not in protected and not _HINDI_INFLECTION.search(core_deva):
            ph = deva_to_phones(core_deva)
            sk = _skeleton(ph)
            deva_ends_matra = bool(re.search(r"[\u093e-\u094c\u094e\u094f\u0955-\u0957]$", core_deva))
            deva_vowels = [p for p in ph if p in _VOWELS and p != "AX"]
            snapped = False
            for cand, csk in brand_index:
                cand_ends_vowel = cand.lower()[-1] in "aeiou"
                # Ending type must match: consonant-ending brand cannot match vowel-ending Hindi word (e.g. तितली ending in ी)
                if cand_ends_vowel != deva_ends_matra:
                    continue
                cand_vowels = [ch for ch in cand.lower() if ch in "aeiou"]
                if abs(len(cand_vowels) - len(deva_vowels)) > 1:
                    continue

                if len(sk) >= 3 and sk == csk:
                    tail = re.search(r"[.,!?।]+$", t)
                    new_text = cand + (tail.group(0) if tail else "")
                    record_decision("unification", t, new_text, f"cross_script_exact_skeleton={sk}",
                                    w.get("start", 0.0), w.get("end", 0.0))
                    out.append(dict(w, text=new_text))
                    snapped = True
                    break
            if not snapped:
                out.append(w)
        else:
            out.append(w)

    return out


_PROPER_NOUN_ENTITIES = {
    "india", "bharat", "hindustan", "mumbai", "delhi", "bangalore", "bengaluru",
    "kolkata", "chennai", "hyderabad", "pune", "ahmedabad", "jaipur", "lucknow",
    "chandigarh", "goa", "kerala", "gujarat", "punjab", "maharashtra", "bihar",
    "rajasthan", "up", "mp", "usa", "uk", "america", "london", "dubai", "europe", "asia"
}


def normalize_case(words: List[dict]) -> List[dict]:
    """
    Lowercase common words from CMUdict lexicon / English vocabulary unless:
    - It is at the start of a sentence (after '.', '?', '!', or index 0).
    - It is a known proper entity (India, Mumbai, Delhi).
    - It is a low-frequency brand or proper noun (low English general frequency, e.g. Dettol, Savlon, Vada, Pav).
    """
    try:
        from wordfreq import zipf_frequency
    except Exception:
        zipf_frequency = lambda w, lang: 0.0

    out = []
    for i, w in enumerate(words):
        t = w["text"]
        m = re.match(r"^([^\w]*)([\w]+)([^\w]*)$", t)
        if not m:
            out.append(w)
            continue
        pre, core, post = m.groups()
        if not core.isalpha() or ord(core[0]) >= 128:
            out.append(w)
            continue

        is_start = (i == 0) or bool(re.search(r"[.!?।]$", words[i - 1]["text"]))
        zf_en = zipf_frequency(core.lower(), "en")
        zf_hi = zipf_frequency(core.lower(), "hi")

        if is_start:
            norm = core.capitalize() if not core.isupper() else core
            reason = "sentence_start"
        elif core.lower() in _PROPER_NOUN_ENTITIES:
            # Established geographic / proper entity (e.g. India, Mumbai, Delhi)
            norm = core.capitalize() if not core.isupper() else core
            reason = "proper_noun_entity"
        elif zf_en >= 3.6:
            # Common English dictionary word occurring mid-sentence (e.g. talent, execution, monthly, revenue, marketing, campaign)
            norm = core.lower()
            reason = f"common_word_en_zipf={zf_en:.2f}"
        else:
            # Low-frequency brand or proper noun (e.g. Dettol, Savlon, Vada, Pav)
            norm = core
            reason = f"proper_or_brand_en_zipf={zf_en:.2f}"

        if norm != core:
            record_decision("casing", core, norm, reason, w.get("start", 0.0), w.get("end", 0.0))
            out.append(dict(w, text=pre + norm + post))
        else:
            out.append(w)
    return out


# =============================================================================
# 3. SEMANTIC REEL CHUNKING  (DP instead of greedy thresholds)
# =============================================================================
# Hindi is head-final with postpositions, so: never break BEFORE a postposition / auxiliary /
# light verb / clitic; avoid ENDING a card on a genitive or conjunction; prefer breaking
# BEFORE conjunctions and clause openers. Matching is on Whisper's Devanagari spelling
# (stable) plus common English function words.
_NO_BREAK_BEFORE = set("""का के की को से में पर तक ने है हैं था थी थे हो होगा होगी रहा रही रहे कर किया दिया लिया गया गई गए
हुआ हुई हुए ही भी तो वाला वाली वाले सकता सकती सकते चाहिए
लाख करोड़ हज़ार हजार प्लस परसेंट lakh crore thousand plus percent
of the to is are was were""".split())
_BAD_END = set("""का के की और या कि लेकिन पर क्योंकि जब अगर तो एक यह वह ये वो इस उस बहुत कुछ हर अपना अपनी अपने मेरा मेरी मेरे
the a an of in on to and or but with for my your our their this that""".split())
_GOOD_START = set("""और लेकिन पर कि क्योंकि जब अगर फिर या जो तभी इसलिए बस अब but and so because when if then""".split())
_NUM = re.compile(r"^[\d\u0966-\u096F][\d\u0966-\u096F.,]*$")
_PUNCT_END = re.compile(r"[.?!।]$")


def _norm(t: str) -> str:
    return re.sub(r"[^\w\u0900-\u097F]", "", t.lower())


def _break_cost(prev: dict, nxt: dict) -> float:
    p, n = _norm(prev["text"]), _norm(nxt["text"])
    gap = nxt["start"] - prev["end"]
    c = 0.0
    if _PUNCT_END.search(prev["text"]):
        c -= 3.0
    elif prev["text"].endswith(","):
        c -= 1.5
    if gap >= 0.35:
        c -= 3.0
    elif gap >= 0.2:
        c -= 1.2
    if n in _NO_BREAK_BEFORE:
        c += 4.0
    if p in _BAD_END:
        c += 3.0
    if n in _GOOD_START:
        c -= 1.5
    if _NUM.match(p):
        c += 3.0
    if re.match(r"^[a-z]+$", p) and re.match(r"^[a-z]+$", n) and p not in _BAD_END:
        c += 0.8  # "tissue|paper", "water|bottle": mild glue between consecutive English words
    return c


def semantic_chunk(words: List[dict], to_latin: Callable[[str], str] = lambda s: s,
                   min_dur: float = 1.3, target_dur: float = 2.0, max_dur: float = 2.8,
                   max_chars: int = 42, soft_max_words: int = 7,
                   pacing: str = "short") -> List[dict]:
    """
    words: [{'start','end','text'}] for the WHOLE clip (flatten Whisper segments first).
    to_latin: callable that returns the displayed (Roman) form, used only to measure line width.
    pacing: 'short' (reels/shorts: 1.0-2.8s, ~42 chars) or 'long' (youtube/16:9: 2.0-5.0s, ~76 chars).
    Returns cards [{'start','end','text'}].
    """
    if pacing == "long":
        min_dur = 2.0
        target_dur = 3.5
        max_dur = 5.0
        max_chars = 76
        soft_max_words = 14
    elif pacing == "short":
        max_chars = 42
    n = len(words)
    if n == 0:
        return []
    widths = [len(to_latin(w["text"])) + 1 for w in words]
    INF = float("inf")
    best = [INF] * (n + 1)
    back = [0] * (n + 1)
    best[0] = 0.0
    for j in range(1, n + 1):
        chars = 0
        window_limit = 24 if pacing == "long" else 14
        for i in range(j - 1, max(-1, j - window_limit), -1):
            chars += widths[i]
            dur = words[j - 1]["end"] - words[i]["start"]
            if dur > max_dur * 1.6 and i < j - 1:
                break
            nw = j - i
            cost = 0.0
            if dur > max_dur:
                cost += (100.0 + 200.0 * (dur - max_dur)) if nw > 1 else 20.0 * (dur - max_dur)
            if dur < min_dur and j != n:
                cost += 4.0 * (min_dur - dur)
            cost += 0.6 * (dur - target_dur) ** 2
            if nw > soft_max_words:
                cost += 2.0 * (nw - soft_max_words)
            if chars > max_chars:
                cost += 0.6 * (chars - max_chars)
            if nw == 1 and n > 1:
                cost += 3.0
            if i > 0:
                cost += _break_cost(words[i - 1], words[i])
            if best[i] + cost < best[j]:
                best[j] = best[i] + cost
                back[j] = i
    cards, j = [], n
    while j > 0:
        i = back[j]
        grp = words[i:j]
        cards.append({"start": grp[0]["start"], "end": grp[-1]["end"],
                      "text": " ".join(w["text"] for w in grp).strip(),
                      "words": grp})
        j = i
    return cards[::-1]


def pad_display_times(cards: List[dict], min_dur: float = 1.0, hold: float = 0.3, gap: float = 0.04,
                      max_dur: float = 2.8, pacing: str = "short") -> List[dict]:
    """Hold each card a little after the last word and up to min_dur if room remains (never overlaps next)."""
    if pacing == "long":
        min_dur = 2.0
        hold = 0.45
        max_dur = 5.0
    out = []
    for k, c in enumerate(cards):
        limit = cards[k + 1]["start"] - gap if k + 1 < len(cards) else c["end"] + hold
        end = max(c["end"], min(c["end"] + hold, limit), min(c["start"] + min_dur, limit))
        end = min(end, c["start"] + max_dur)
        if k + 1 < len(cards):
            end = min(end, limit)
        out.append(dict(c, end=round(end, 3)))
    return out



# =============================================================================
# GLUE: words -> final cards (what generate_subtitles() should call)
# =============================================================================
def words_to_cards(words: List[dict], to_hinglish: Callable[[str], str],
                   recoverer: Optional[LoanwordRecoverer] = None,
                   hint_terms: Iterable[str] = (),
                   reel_name: str = "reel",
                   pacing: str = "short") -> List[dict]:
    """
    words        : flat word list from transcribe_words()
    to_hinglish  : transliteration.convert_to_hinglish
    pacing       : 'short' (reels) or 'long' (youtube/16:9)
    Returns [{'start','end','original_text','hinglish_text'}]
    """
    if hint_terms:
        words = snap_to_terms(words, hint_terms)

    # 1. Unify inconsistent Latin variants and cross-script brand references
    words = unify_variants(words)

    # 2. Loanword recovery (Devanagari -> English)
    if recoverer is not None:
        words = recoverer.apply(words)

    # 3. Case normalization (eliminate stray capitals mid-sentence)
    words = normalize_case(words)

    # 4. Semantic chunking and padding
    cards = pad_display_times(semantic_chunk(words, to_latin=to_hinglish, pacing=pacing), pacing=pacing)

    # 5. Export decisions to TSV
    export_decisions(reel_name)

    return [{
        "start": c["start"],
        "end": c["end"],
        "original_text": c["text"],
        "hinglish_text": to_hinglish(c["text"]),
        "words": [
            {
                "start": w.get("start", c["start"]),
                "end": w.get("end", c["end"]),
                "word": w.get("text", ""),
                "hinglish": to_hinglish(w.get("text", ""))
            }
            for w in c.get("words", [])
        ]
    } for c in cards]
