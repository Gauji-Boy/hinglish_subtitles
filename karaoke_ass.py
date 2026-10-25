"""
karaoke_ass.py - Advanced SubStation Alpha (.ass) generator for word-level karaoke subtitles.

Uses `\\k` word timing for the highlight fill. Style (font, colours, box, margins,
animation) and canvas aspect come from caption_styles.py. Colours are authored in
CSS hex and emitted as ASS ABGR.
"""

import math
import os
import re
from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence, Tuple

from caption_styles import DEFAULT_STYLE_ID, PRESETS, aspect_profile, hex_to_ass, resolve_style

try:  # Pillow is already a project dependency, but keep the generator importable.
    from PIL import ImageFont
except Exception:  # pragma: no cover - only used on stripped-down machines
    ImageFont = None

_KINETIC_FPS = 30.0
_KINETIC_HOLD_SEC = 0.30
# The title phrase ("The Sweet Spot?") sits slightly higher than the normal
# four-line block in the reference. Keep the style's anchor_y as the normal
# anchor and subtract this offset for title phrases.
_KINETIC_TITLE_ANCHOR_OFFSET = 4.5
# libass/FFmpeg renders Arial Bold slightly narrower than the browser and
# Pillow metrics used for wrapping. Scale only the emitted \fs values so line
# breaks stay browser-matched while the burned text fills the same width.
_KINETIC_ASS_FONT_SCALE = 1.399
_KINETIC_ASS_NORMAL_SCALE = 0.95
_KINETIC_ASS_SCALE_X = 90.5
# `kinetic_layout: alternate` in the Honey Punch frames: odd phrases sit flush
# right, even phrases flush left, each 7% of the frame width in from its edge.
_KINETIC_ALTERNATE_MARGIN = 0.07
# A held poster survives ASR card boundaries, so the word cap is the only thing
# that ends a long run without punctuation. The values are set by the rendered
# line count (see tests), not by the word count alone: 8 words still fit five
# lines on 9:16 at the Honey Punch proportions.
_KINETIC_POSTER_MAX_WORDS = (8, 12)  # (portrait, landscape)
# The frames never show more than four lines at 16:9, and a Hinglish poster is
# punch-dense enough to reach six. A poster that wraps past its budget is split
# at the wrap boundary, so line breaks stay identical and only the block is
# shortened.
_KINETIC_POSTER_MAX_LINES = (5, 4)  # (portrait, landscape)
# Punctuation only ends a poster when the speaker actually stops there. In the
# reference clip both full stops sit at a 0.0 s word gap ("The Sweet Spot? It's
# run by Emma," is continuous), while the smallest mid-sentence hesitation is
# 0.20 s. A 200 ms gate therefore keeps continuous delivery as one block and
# still splits a sentence the speaker breathes at.
_KINETIC_SENTENCE_PAUSE_SEC = 0.20
_SENTENCE_END = (".", "?", "!", "\u0964")
_CLOSING_CHARS = "\"'”’)]}»"

# --- Recess (gradient pill) renderer ---------------------------------------
# libass maps Arial Black's \fs through the font's ascent/descent, so it lands
# at roughly 0.72x the nominal size Pillow uses. The ratios below were measured
# by rendering probes with this FFmpeg/libass build at 1920x1080 and comparing
# against the reference frames.
_RECESS_INK_RATIO = 0.640        # rendered ink width / Pillow ink width
_RECESS_ADVANCE_RATIO = 0.652    # rendered advance width / Pillow advance width
_RECESS_CAP_RATIO = 0.520        # rendered cap height / emitted \fs
# \an5 anchors on the middle of the font box, which sits slightly below the
# middle of the caps. Measured +0.025 em across 140 and 284 \fs.
_RECESS_INK_ANCHOR_OFFSET = 0.025
_RECESS_LINE_PITCH_EM = 0.915    # cap top to cap top, in emitted \fs units
# The reference face is ~0.70 cap/em; Arial Black is ~0.52. The pill's padding
# is authored in reference ems, so map emitted \fs -> reference em.
_RECESS_PILL_EM_RATIO = 0.775

# Short English/Hinglish function words stay white. Content words become the
# gold "punch" words seen in the reference. Accent overrides are interjections.
_KINETIC_ACCENTS = frozenset(
    "hey hi hello yo wow yes yeah no nah okay ok oh ah arrey arey oye by".split()
)
_KINETIC_STOPWORDS = frozenset(
    """
    a an the and or but if then so to of in on at by for with from as is are was were be been
    being am do does did have has had i you he she it we they me him her us them my your his its
    our their this that these those there here what which who whom whose when where why how not
    no yes just very too also about into over under again once all any both each few more most
    other some such only own same than now up down out off every each another many much more most
    few several plenty enough really quite rather almost less least lot lots bunch it's i'm you're we're they're don't
    doesn't didn't can't won't isn't aren't wasn't weren't i've you've we've they've i'll you'll
    he'll she'll we'll they'll i'd you'd he'd she'd we'd they'd that's there's let's lets
    ne ko ka ki ke hai hain tha thi the aur par se me mein ek yeh ye wo vo kya nahi nahin bhi toh
    hi na ha ho hua hui hue kar karta karti karte kiya raha rahi rahe gaya gayi gaye liye liya diya
    di de dena lena le lo chalo aao ja jaao sakta sakti sakte chahiye hoga hogi honge mera meri mere
    tera teri tere uska uski uske inka inki inke hamara hamari hamare unka unki unke yahan wahan ab
    phir fir kal aaj roz sab sabse kuch koi kuchh bas sirf bahut zyada kam accha acha
    """.split()
)

_FONT_FILES = {
    "Impact": "impact.ttf",
    "Arial Black": "ariblk.ttf",
    "Segoe UI": "segoeuib.ttf",
    "Arial": "arialbd.ttf",
    "Verdana": "verdanab.ttf",
    "Trebuchet MS": "trebucbd.ttf",
    "Georgia": "georgiab.ttf",
    "Consolas": "consolab.ttf",
}


def format_ass_time(seconds: float) -> str:
    """Format seconds into ASS timestamp format: H:MM:SS.cc (centiseconds)."""
    if seconds < 0:
        seconds = 0.0
    total_cs = int(round(seconds * 100))
    h = total_cs // 360000
    m = (total_cs % 360000) // 6000
    s = (total_cs % 6000) // 100
    cs = total_cs % 100
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def escape_ass_text(text: str) -> str:
    """Escape braces and control characters in ASS text."""
    return text.replace("{", "(").replace("}", ")")


def _as_ass_color(value: Optional[str], fallback: str) -> str:
    """Accept a legacy &HAABBGGRR value or a #RRGGBB(A) value."""
    text = str(value or "").strip()
    if text.upper().startswith("&H"):
        return text.upper()
    if text.startswith("#"):
        return hex_to_ass(text, fallback)
    return fallback


def _safe_float(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number or number in (float("inf"), float("-inf")):
        return default
    return number


def _word_key(text: str) -> str:
    """Lowercase a display token without its surrounding punctuation."""
    raw = re.sub(r"^[^\w']+|[^\w']+$", "", str(text or "").strip(), flags=re.UNICODE)
    return raw.lower().replace("\u2019", "'")


def is_accent_word(text: str, mode: str = "content") -> bool:
    """Return True when a word should be gold."""
    if mode == "all":
        return True
    if mode == "none":
        return False
    raw = re.sub(r"^[^\w']+|[^\w']+$", "", str(text or "").strip(), flags=re.UNICODE)
    key = _word_key(raw)
    if not key:
        return False
    if key in _KINETIC_ACCENTS:
        return True
    if key in _KINETIC_STOPWORDS:
        return False
    # The reference highlights nouns, verbs and proper names, but leaves short
    # glue words like "run" white. "by" is the one preposition the reference
    # paints gold in "It's run by Emma".
    return len(key) >= 4 or raw[:1].isupper()


def is_punch_word(text: str, mode: str = "content") -> bool:
    """Return True when a word should get the oversized punch size.

    Gold and oversized are separate in the reference. "hear" is gold but
    normal-sized; "bakery", proper nouns, and interjections are oversized.
    """
    if mode == "none" or not is_accent_word(text, mode):
        return False
    raw = re.sub(r"^[^\w']+|[^\w']+$", "", str(text or "").strip(), flags=re.UNICODE)
    key = _word_key(raw)
    if not key or key in _KINETIC_STOPWORDS:
        return False
    if key in _KINETIC_ACCENTS or raw[:1].isupper():
        return True
    return len(key) >= 5


def _is_title_phrase(phrase: Sequence[Dict[str, Any]]) -> bool:
    """True for "The Sweet Spot?"-style title phrases."""
    return (
        len(phrase) >= 2
        and _word_key(phrase[0].get("raw_text", "")) == "the"
        and str(phrase[1].get("raw_text", "")).strip()[:1].isupper()
    )


def _flatten_caption_words(
    cards: Sequence[Dict[str, Any]],
    use_hinglish: bool,
    use_upper: bool,
    accent_mode: str = "content",
) -> List[Dict[str, Any]]:
    """Flatten cards into a stable, timed word stream."""
    flat: List[Dict[str, Any]] = []
    order = 0
    for card_index, card in enumerate(cards):
        if not isinstance(card, dict):
            continue
        card_start = _safe_float(card.get("start"), 0.0)
        card_end = _safe_float(card.get("end"), card_start + 2.0)
        if card_end < card_start:
            card_end = card_start

        raw_words = card.get("words") or []
        if not raw_words:
            fallback_text = str(
                card.get("hinglish_text" if use_hinglish else "original_text") or ""
            ).strip()
            raw_words = (
                [{"start": card_start, "end": card_end, "text": fallback_text}]
                if fallback_text
                else []
            )

        for word_index, word in enumerate(raw_words):
            if not isinstance(word, dict):
                continue
            raw_text = word.get("hinglish" if use_hinglish else "word")
            if not raw_text:
                raw_text = word.get("text") or word.get("word") or word.get("hinglish") or ""
            text = str(raw_text).strip()
            if not text:
                continue
            start = _safe_float(word.get("start"), card_start)
            end = _safe_float(word.get("end"), start + 0.3)
            if end < start:
                end = start + 0.3
            accent = is_accent_word(text, accent_mode)
            # Detect punch from the original casing: uppercase is a display
            # transform, and letting it drive punch would promote every
            # accent word (e.g. "hear" -> "HEAR") to oversized.
            punch = is_punch_word(text, accent_mode)
            raw_text = text
            if use_upper:
                text = text.upper()
            flat.append(
                {
                    "text": escape_ass_text(text),
                    "raw_text": raw_text,
                    "accent": accent,
                    "punch": punch,
                    "start": start,
                    "end": end,
                    "card_start": card_start,
                    "card_end": card_end,
                    "card_index": card_index,
                    "word_index": word_index,
                    "order": order,
                }
            )
            order += 1

    flat.sort(key=lambda item: (item["start"], item["order"]))
    return flat


def _ends_sentence(text: str) -> bool:
    """True when a token closes a sentence, ignoring a trailing quote or bracket."""
    stripped = str(text or "").strip().rstrip(_CLOSING_CHARS).rstrip()
    return bool(stripped) and stripped[-1] in _SENTENCE_END


def _group_phrases(
    words: Sequence[Dict[str, Any]],
    gap_sec: float,
    max_words: Optional[int] = None,
    split_on_punct: bool = False,
    accent_mode: str = "content",
    grouping: str = "flow",
) -> List[List[Dict[str, Any]]]:
    """Split a word stream at audible pauses, card boundaries, or a safety cap.

    ``grouping="punch"`` isolates every punch word into its own card and keeps
    each run of non-punch words together, which is the Recess card rhythm:
    ``[HEY] [DID YOU HEAR ABOUT THE] [BAKERY] ...``.

    ``grouping="poster"`` holds one block across ASR cards (a card break is not a
    pause by itself). A poster ends at a real ``gap_sec`` silence, at sentence
    punctuation when the audio or the segmentation agrees (the speaker pauses
    ``_KINETIC_SENTENCE_PAUSE_SEC``, or the ASR card ends on the stop), or at the
    word cap, which is applied afterwards per sentence so the split stays
    balanced.
    """
    phrases: List[List[Dict[str, Any]]] = []
    current: List[Dict[str, Any]] = []
    punch_grouping = grouping == "punch"
    poster_grouping = grouping == "poster"
    for word in words:
        reset = False
        if current:
            previous = current[-1]
            word_gap = word["start"] - previous["end"]
            card_gap = word["card_start"] - previous["card_end"]
            if poster_grouping:
                # The word cap is applied later, per sentence, so a long poster
                # splits evenly instead of leaving a one-word tail. A full stop
                # only ends the block when the audio or the segmentation agrees:
                # the speaker pauses, or the ASR card ends there. Continuous
                # delivery mid-card keeps "? It's run by Emma," in place.
                if _ends_sentence(previous.get("text", "")) and (
                    word_gap >= _KINETIC_SENTENCE_PAUSE_SEC
                    or word["card_start"] != previous["card_start"]
                ):
                    reset = True
                elif word_gap > gap_sec:
                    reset = True
            elif punch_grouping and (previous.get("punch") or word.get("punch")):
                # A punch word never shares a card.
                reset = True
            elif word_gap > gap_sec or card_gap > gap_sec:
                reset = True
            elif max_words and len(current) >= max_words:
                reset = True
            elif split_on_punct and len(current) >= 2:
                prev_text = str(previous.get("text") or "").rstrip()
                if prev_text and prev_text[-1] in (",", ";", ".", "!", "?", "—", "-"):
                    reset = True
        if reset and current:
            phrases.append(current)
            current = []
        current.append(word)
    if current:
        phrases.append(current)

    for phrase in phrases:
        for index, word in enumerate(phrase):
            word["next_start"] = (
                phrase[index + 1]["start"] if index + 1 < len(phrase) else word["end"]
            )
        # "The Sweet Spot?" is a title phrase, so its leading "The" joins the
        # gold/punch treatment. Plain "the bakery" stays white and base-sized.
        if accent_mode != "none" and _is_title_phrase(phrase):
            phrase[0]["accent"] = True
            phrase[0]["punch"] = True
    return phrases


def _split_overlong_posters(
    phrases: Sequence[List[Dict[str, Any]]],
    resolved: Dict[str, Any],
    play_res_x: int,
    play_res_y: int,
    base_size: float,
    max_words: int,
    max_lines: int,
) -> List[List[Dict[str, Any]]]:
    """Cut a poster that is too long for one block into balanced blocks.

    Two limits apply: the word cap (``max_words``) and the rendered line budget
    (``max_lines``). A cut is made on a wrap boundary of the current block, so
    the kept lines are the lines the burn would have drawn and type size and
    alignment never change. Among the feasible boundaries the cut closest to an
    even word split wins, so a 14-word run reads 5 + 4 + 5 rather than 8 + 6 or
    8 + 1.
    """
    split: List[List[Dict[str, Any]]] = []
    for phrase in phrases:
        pending = list(phrase)
        while pending:
            lines = _kinetic_lines(
                pending,
                _kinetic_scales(pending, resolved),
                base_size,
                _phrase_max_width(pending, resolved, play_res_x, play_res_y),
                str(resolved["font"]),
                _forced_break_after_first(pending),
                _forced_break_after_question(pending),
                _forced_break_before_the(pending),
            )
            fits_words = max_words <= 0 or len(pending) <= max_words
            fits_lines = max_lines <= 0 or len(lines) <= max_lines
            if fits_words and fits_lines:
                split.append(pending)
                break

            blocks = 1
            if max_lines > 0:
                blocks = max(blocks, -(-len(lines) // max_lines))
            if max_words > 0:
                blocks = max(blocks, -(-len(pending) // max_words))
            target = len(pending) / blocks

            best: Optional[Tuple[float, int]] = None
            for keep in range(1, len(pending)):
                if max_words > 0 and keep > max_words:
                    break
                if max_lines > 0:
                    head = _kinetic_lines(
                        pending[:keep],
                        _kinetic_scales(pending[:keep], resolved),
                        base_size,
                        _phrase_max_width(pending[:keep], resolved, play_res_x, play_res_y),
                        str(resolved["font"]),
                        _forced_break_after_first(pending[:keep]),
                        _forced_break_after_question(pending[:keep]),
                        _forced_break_before_the(pending[:keep]),
                    )
                    if len(head) > max_lines:
                        continue
                score = abs(keep - target)
                if best is None or score < best[0] or (score == best[0] and keep < best[1]):
                    best = (score, keep)
            if best is None:
                # No boundary satisfies both limits (a single line already
                # exceeds the cap); keep the run whole rather than lose words.
                split.append(pending)
                break
            keep = best[1]
            split.append(pending[:keep])
            pending = pending[keep:]
    for phrase in split:
        for index, word in enumerate(phrase):
            word["next_start"] = (
                phrase[index + 1]["start"] if index + 1 < len(phrase) else word["end"]
            )
    return split


def _forced_break_after_first(phrase: Sequence[Dict[str, Any]]) -> bool:
    """Keep an opening interjection ("Hey,") on its own top line like the reference."""
    return (
        len(phrase) > 1
        and _word_key(phrase[0].get("raw_text", "")) in _KINETIC_ACCENTS
    )


def _forced_break_after_question(phrase: Sequence[Dict[str, Any]]) -> bool:
    """Keep a title question ("The Sweet Spot?") on its own line."""
    return any(
        str(word.get("text", "")).rstrip().endswith("?")
        for word in phrase[:-1]
    )


def _forced_break_before_the(phrase: Sequence[Dict[str, Any]]) -> Optional[int]:
    """Break before "the" in "about the bakery" to preserve the reference.

    The reference lays out phrase 1 as:
        Hey, / did you hear about / the bakery in / Willow Creek,
    Greedy wrapping can fit that "the" on line 2 once the type is scaled to
    match, so this semantic break keeps the same four-line shape in both the
    live overlay and the ASS export.
    """
    for index, word in enumerate(phrase):
        if index == 0:
            continue
        if (
            _word_key(word.get("text", "")) == "the"
            and _word_key(phrase[index - 1].get("text", "")) == "about"
        ):
            if index < len(phrase) - 1:
                return index
    return None


def _active_word_index(phrase: Sequence[Dict[str, Any]], seconds: float) -> int:
    """Last word whose start time has passed."""
    low, high = 0, len(phrase) - 1
    answer = -1
    while low <= high:
        mid = (low + high) // 2
        if phrase[mid]["start"] <= seconds + 1e-6:
            answer = mid
            low = mid + 1
        else:
            high = mid - 1
    return answer


def _kinetic_base_size(play_res_y: int, font_size: int, play_res_x: Optional[int] = None) -> int:
    """The reference uses roughly 8% of frame height for a 128px style size.

    Portrait frames are much narrower per line, so a slightly smaller base keeps
    a 3-word punch phrase from collapsing to one word per line.
    """
    factor = 1.0
    if play_res_x and play_res_y > play_res_x * 1.15:
        factor = 0.70
    return max(12, int(round(play_res_y * float(font_size) * factor / 1600.0)))


def _kinetic_max_width(play_res_x: int, play_res_y: int, width_percent: int) -> float:
    percent = float(width_percent)
    if play_res_y > play_res_x:
        percent = min(92.0, percent + 18.0)
    return max(80.0, play_res_x * percent / 100.0)


def _phrase_max_width(
    phrase: Sequence[Dict[str, Any]],
    resolved: Dict[str, Any],
    play_res_x: int,
    play_res_y: int,
) -> float:
    """Title phrases get a wider line box so "The Sweet Spot?" stays intact."""
    percent = int(resolved["max_width"])
    if _is_title_phrase(phrase):
        percent = min(88, percent + 10)
    return _kinetic_max_width(play_res_x, play_res_y, percent)


@lru_cache(maxsize=32)
def _load_pillow_font(path: str, size: int):
    if ImageFont is None:
        return None
    try:
        return ImageFont.truetype(path, max(8, int(size)))
    except Exception:
        return None


@lru_cache(maxsize=16)
def _font_path(font_name: str) -> Optional[str]:
    filename = _FONT_FILES.get(font_name)
    if not filename:
        return None
    windir = os.environ.get("WINDIR", r"C:\Windows")
    candidates = [
        os.path.join(windir, "Fonts", filename),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "fonts", filename),
        filename,
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return None


def _measure_kinetic_text(text: str, size: float, font_name: str) -> float:
    rounded = max(8, int(round(size)))
    path = _font_path(font_name)
    font = _load_pillow_font(path, rounded) if path else None
    if font is not None:
        try:
            return float(font.getlength(text))
        except Exception:
            pass
    return len(text) * float(rounded) * 0.58


def _kinetic_lines(
    words: Sequence[Dict[str, Any]],
    scales: Sequence[float],
    base_size: float,
    max_width: float,
    font_name: str,
    break_after_first: bool = False,
    break_after_question: bool = False,
    break_before_index: Optional[int] = None,
    measure: Optional[Any] = None,
) -> List[List[Tuple[Dict[str, Any], float, float, int]]]:
    """Greedy word wrap using real font metrics so ASS matches the live overlay."""
    measure_word = measure or _measure_kinetic_text
    lines: List[List[Tuple[Dict[str, Any], float, float, int]]] = []
    current: List[Tuple[Dict[str, Any], float, float, int]] = []
    current_width = 0.0
    for word_index, (word, scale) in enumerate(zip(words, scales)):
        if current and word_index == break_before_index:
            lines.append(current)
            current = []
            current_width = 0.0
        size = base_size * scale
        word_width = measure_word(word["text"], size, font_name)
        if word_width > max_width > 0:
            # A word wider than the line box cannot be wrapped, so it used to
            # run off the frame (long gold punch words on 9:16). Shrink that
            # one word to fit instead of clipping it.
            scale *= max_width / word_width
            size = base_size * scale
            word_width = measure_word(word["text"], size, font_name)
        space_width = measure_word(" ", size, font_name) if current else 0.0
        if current and current_width + space_width + word_width > max_width:
            lines.append(current)
            current = []
            current_width = 0.0
            space_width = 0.0
        current.append((word, scale, size, word_index))
        current_width += space_width + word_width
        ends_question = str(word.get("text", "")).rstrip().endswith("?")
        if (
            (break_after_first and word_index == 0 and len(words) > 1)
            or (break_after_question and ends_question and word_index < len(words) - 1)
        ):
            lines.append(current)
            current = []
            current_width = 0.0
    if current:
        lines.append(current)
    return lines


def _inline_ass_color(ass_color: str) -> str:
    """Convert &HAABBGGRR to the inline \\c&HBBGGRR& form."""
    text = str(ass_color or "").strip().upper()
    if text.startswith("&H") and len(text) >= 10:
        return f"&H{text[4:]}&"
    return "&HFFFFFF&"


def _kinetic_scales(
    phrase: Sequence[Dict[str, Any]], resolved: Dict[str, Any]
) -> List[float]:
    """Per-word size multipliers: punch > gold accent > connective.

    The Honey Punch frames show three tiers. Presets that never set
    `accent_size_scale` resolve to 100, so older styles keep their geometry.
    """
    punch = float(resolved["accent_scale"]) / 100.0
    accent = float(resolved.get("accent_size_scale", 100)) / 100.0
    return [
        punch if word.get("punch") else (accent if word.get("accent") else 1.0)
        for word in phrase
    ]


def _render_kinetic_text(
    words: Sequence[Dict[str, Any]],
    scales: Sequence[float],
    base_size: float,
    max_width: float,
    font_name: str,
    base_ass: str,
    highlight_ass: str,
    active_index: int,
    break_after_first: bool = False,
    break_after_question: bool = False,
    break_before_index: Optional[int] = None,
    font_scale: float = 1.0,
) -> str:
    """Render the full phrase, making unspoken words transparent.

    Keeping every word in the event reserves the final line widths, so the
    speaker's phrase does not reflow while words are revealed.
    """
    lines = _kinetic_lines(
        words,
        scales,
        base_size,
        max_width,
        font_name,
        break_after_first,
        break_after_question,
        break_before_index,
    )
    base_inline = _inline_ass_color(base_ass)
    highlight_inline = _inline_ass_color(highlight_ass)
    rendered_lines: List[str] = []
    for line in lines:
        parts: List[str] = []
        for word, _scale, size, word_index in line:
            color = highlight_inline if word["accent"] else base_inline
            alpha = "00" if word_index <= active_index else "FF"
            # libass renders this font narrower than the Pillow metrics used
            # for wrapping, so every tier carries the same correction. That
            # keeps `accent_scale` / `accent_size_scale` meaning the true
            # ratio to a connective word.
            word_scale = font_scale * _KINETIC_ASS_NORMAL_SCALE
            parts.append(
                f"{{\\c{color}\\fs{max(8, int(round(size * word_scale)))}\\alpha&H{alpha}&}}"
                f"{word['text']}"
            )
        rendered_lines.append(" ".join(parts))
    return r"\N".join(rendered_lines)


def _kinetic_event_anchor(
    phrase_index: int,
    resolved: Dict[str, Any],
    play_res_x: int,
    play_res_y: int,
    is_title: bool = False,
) -> Tuple[int, float, float]:
    """Return (ASS alignment, x, y) for a top-anchored phrase.

    `alternate` keeps the frames' ragged rhythm: phrase 1 flush right, phrase 2
    flush left, ~7% in from the respective edge. `right` keeps the older single
    right margin for saved custom styles.
    Title phrases sit slightly higher than the normal multi-line block.
    """
    layout = resolved.get("kinetic_layout", "center")
    anchor_y = float(resolved["anchor_y"])
    if is_title:
        anchor_y -= _KINETIC_TITLE_ANCHOR_OFFSET
    y = play_res_y * anchor_y / 100.0
    if layout == "middle":
        # Recess centres the block on both axes; every word is placed with
        # \an5, so the anchor is the block centre rather than its top edge.
        return 5, play_res_x / 2.0, y
    if layout == "alternate":
        # \an9 and \an7 put the anchor on that edge of the block, so the x
        # value is the margin from the frame edge, not the block's centre.
        if phrase_index % 2 == 0:
            return 9, play_res_x * (1.0 - _KINETIC_ALTERNATE_MARGIN), y
        return 7, play_res_x * _KINETIC_ALTERNATE_MARGIN, y
    if layout == "right":
        return 9, play_res_x * 0.80, y
    return 8, play_res_x / 2.0, y


def _generate_kinetic_ass(
    cards: Sequence[Dict[str, Any]],
    resolved: Dict[str, Any],
    script_title: str,
    use_hinglish: bool,
    play_res_x: int,
    play_res_y: int,
    base_ass: str,
    highlight_ass: str,
    outline_ass: str,
    back_ass: str,
) -> str:
    words = _flatten_caption_words(
        cards,
        use_hinglish,
        bool(resolved["uppercase"]),
        str(resolved.get("accent_mode", "content")),
    )
    is_portrait = play_res_y > play_res_x
    grouping = str(resolved.get("kinetic_grouping", "flow"))
    default_max_words = 4 if is_portrait else 10
    max_words = int(resolved.get("max_words_per_phrase") or default_max_words)
    if grouping == "poster":
        # Posters span ASR cards, so the cap is capped by rendered line count.
        max_words = min(max_words, _KINETIC_POSTER_MAX_WORDS[0 if is_portrait else 1])
    elif is_portrait:
        max_words = min(max_words, 4)
    phrases = _group_phrases(
        words,
        float(resolved["phrase_gap_ms"]) / 1000.0,
        max_words=max_words,
        split_on_punct=False,
        accent_mode=str(resolved.get("accent_mode", "content")),
        grouping=grouping,
    )

    base_size = _kinetic_base_size(play_res_y, int(resolved["font_size"]), play_res_x)
    if grouping == "poster":
        phrases = _split_overlong_posters(
            phrases,
            resolved,
            play_res_x,
            play_res_y,
            base_size,
            max_words,
            _KINETIC_POSTER_MAX_LINES[0 if is_portrait else 1],
        )
    font_name = str(resolved["font"])
    bold = -1 if resolved["bold"] else 0
    shadow = int(resolved["shadow"])
    style_name = "HoneyPunchKinetic"

    header = f"""[Script Info]
; Script generated by Hinglish Subtitles Studio v2.5 (kinetic pre-layout)
Title: {script_title}
ScriptType: v4.00+
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: {play_res_x}
PlayResY: {play_res_y}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: {style_name},{font_name},{base_size},{highlight_ass},{base_ass},{outline_ass},{back_ass},{bold},0,0,0,{_KINETIC_ASS_SCALE_X},100,0,0,1,{resolved["outline_width"]},{shadow},9,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    dialogue_lines: List[str] = []
    frame_step = 1.0 / _KINETIC_FPS

    for phrase_index, phrase in enumerate(phrases):
        if not phrase:
            continue
        first_start = max(0.0, phrase[0]["start"])
        last = phrase[-1]
        next_start = (
            phrases[phrase_index + 1][0]["start"]
            if phrase_index + 1 < len(phrases)
            else None
        )
        natural_end = max(last["end"], last["start"] + 0.35)
        if next_start is not None and next_start > first_start:
            # Keep the completed phrase on screen until the next phrase starts,
            # but do not leave a stale card up through a very long silence.
            display_end = min(next_start, natural_end + 1.30)
        else:
            display_end = natural_end + _KINETIC_HOLD_SEC
        display_end = max(display_end, first_start + 0.05)

        times: List[float] = []
        seconds = first_start
        while seconds < display_end - 1e-6:
            times.append(seconds)
            seconds += frame_step
        if not times:
            times = [first_start]

        alignment, anchor_x, anchor_y = _kinetic_event_anchor(
            phrase_index, resolved, play_res_x, play_res_y,
            is_title=_is_title_phrase(phrase),
        )
        phrase_max_width = _phrase_max_width(
            phrase, resolved, play_res_x, play_res_y
        )
        scales = _kinetic_scales(phrase, resolved)
        break_after_first = _forced_break_after_first(phrase)
        break_after_question = _forced_break_after_question(phrase)
        break_before_index = _forced_break_before_the(phrase)
        for frame_index, seconds in enumerate(times):
            active_index = _active_word_index(phrase, seconds)
            if active_index < 0:
                continue
            event_end = (
                times[frame_index + 1] if frame_index + 1 < len(times) else display_end
            )
            if event_end <= seconds + 1e-6:
                continue

            text = _render_kinetic_text(
                phrase,
                scales,
                base_size,
                phrase_max_width,
                font_name,
                base_ass,
                highlight_ass,
                active_index,
                break_after_first,
                break_after_question,
                break_before_index,
                _KINETIC_ASS_FONT_SCALE,
            )
            if not text:
                continue

            start_cs = max(0, int(round(seconds * 100.0)))
            end_cs = max(start_cs + 1, int(round(event_end * 100.0)))
            prefix = (
                f"{{\\an{alignment}\\pos({anchor_x:.0f},{anchor_y:.0f})\\q2}}"
            )
            dialogue_lines.append(
                "Dialogue: 0,"
                f"{format_ass_time(start_cs / 100.0)},"
                f"{format_ass_time(end_cs / 100.0)},"
                f"{style_name},,0,0,0,,{prefix}{text}"
            )

    if not dialogue_lines:
        # No timed words: fall back to one static event per card.
        for card in cards:
            if not isinstance(card, dict):
                continue
            start = _safe_float(card.get("start"), 0.0)
            end = _safe_float(card.get("end"), start + 2.0)
            text = str(card.get("hinglish_text" if use_hinglish else "original_text") or "").strip()
            if not text:
                continue
            if resolved["uppercase"]:
                text = text.upper()
            alignment, anchor_x, anchor_y = _kinetic_event_anchor(
                0, resolved, play_res_x, play_res_y
            )
            prefix = f"{{\\an{alignment}\\pos({anchor_x:.0f},{anchor_y:.0f})\\q2}}"
            dialogue_lines.append(
                "Dialogue: 0,"
                f"{format_ass_time(start)},{format_ass_time(end)},"
                f"{style_name},,0,0,0,,{prefix}{escape_ass_text(text)}"
            )

    return header + "\n".join(dialogue_lines) + "\n"


def _recess_base_em(play_res_x: int, play_res_y: int, resolved: Dict[str, Any]) -> float:
    """Emitted \\fs for a normal (non-punch) word."""
    base = _kinetic_base_size(play_res_y, int(resolved["font_size"]), play_res_x)
    em = base * float(resolved.get("kinetic_size_scale", 1.0))
    if play_res_y > play_res_x:
        # Portrait canvases are narrower. Keep roughly the same line fill
        # instead of overflowing at the landscape em.
        em *= 0.55
    return em


def _measure_kinetic_bbox(
    text: str, size: float, font_name: str
) -> Tuple[float, float]:
    """Pillow ink extents (left, right) relative to the text origin."""
    rounded = max(8, int(round(size)))
    path = _font_path(font_name)
    font = _load_pillow_font(path, rounded) if path else None
    if font is not None:
        try:
            box = font.getmask(text).getbbox()
            if box:
                return float(box[0]), float(box[2])
        except Exception:
            pass
    return 0.0, _measure_kinetic_text(text, size, font_name)


def _measure_kinetic_ink(text: str, size: float, font_name: str) -> float:
    """Pillow ink extents (not the advance) so short words do not overshoot."""
    left, right = _measure_kinetic_bbox(text, size, font_name)
    return max(0.0, right - left)


def _recess_ink(text: str, size: float, font_name: str) -> float:
    """Rendered ink width in canvas pixels (used for wrapping and pills)."""
    return _measure_kinetic_ink(text, size, font_name) * _RECESS_INK_RATIO


def _recess_advance(text: str, size: float, font_name: str) -> float:
    """Rendered advance width in canvas pixels (used for word placement)."""
    return _measure_kinetic_text(text, size, font_name) * _RECESS_ADVANCE_RATIO


def _recess_layout(
    phrase: Sequence[Dict[str, Any]],
    scales: Sequence[float],
    base_em: float,
    max_width: float,
    font_name: str,
    centre_x: float,
    centre_y: float,
) -> List[Dict[str, Any]]:
    """Wrap a card and place every word with an explicit \\an5 anchor.

    Words are positioned individually so the reveal spring scales each one
    around its own centre and the line pitch stays exact regardless of the
    tallest glyph in the line.
    """
    lines = _kinetic_lines(
        phrase,
        scales,
        base_em,
        max_width,
        font_name,
        measure=_recess_ink,
    )
    pitch = base_em * _RECESS_LINE_PITCH_EM
    count = max(1, len(lines))
    space = _recess_advance(" ", base_em, font_name)
    placed: List[Dict[str, Any]] = []
    for line_index, line in enumerate(lines):
        line_y = centre_y + (line_index - (count - 1) / 2.0) * pitch
        advances = [
            _recess_advance(word["text"], size, font_name)
            for word, _scale, size, _index in line
        ]
        total = sum(advances) + space * max(0, len(line) - 1)
        cursor = centre_x - total / 2.0
        for (word, _scale, size, word_index), advance in zip(line, advances):
            left, right = _measure_kinetic_bbox(word["text"], size, font_name)
            measured = _measure_kinetic_text(word["text"], size, font_name)
            centre = cursor + advance / 2.0
            # The pill should hug the ink, not the advance box; the two centres
            # differ by the glyph's asymmetric side bearings.
            ink_shift = (((left + right) / 2.0) - measured / 2.0) * _RECESS_ADVANCE_RATIO
            placed.append(
                {
                    "word": word,
                    "index": word_index,
                    "em": size,
                    "x": centre,
                    "ink_x": centre + ink_shift,
                    # Shift up so the cap centre, not the font-box centre,
                    # lands on the line.
                    "y": line_y - size * _RECESS_INK_ANCHOR_OFFSET,
                    "ink": (right - left) * _RECESS_INK_RATIO,
                    "line": line_index,
                }
            )
            cursor += advance + space
    return placed


def _recess_pill_box(
    item: Dict[str, Any],
    resolved: Dict[str, Any],
    pill_em: float,
) -> Tuple[float, float, float, float, float]:
    """Return (x0, y0, width, height, radius) for a word's pill."""
    pad_x = float(resolved["pill_pad_x"]) * pill_em
    pad_y = float(resolved["pill_pad_y"]) * pill_em
    radius = float(resolved["pill_radius"]) * pill_em
    width = item["ink"] + 2.0 * pad_x
    # The padding is identical for normal and punch words in the reference,
    # so only the cap height follows the word's own em.
    height = item["em"] * _RECESS_CAP_RATIO + 2.0 * pad_y
    ink_centre_y = item["y"] + item["em"] * _RECESS_INK_ANCHOR_OFFSET
    ink_centre_x = item.get("ink_x", item["x"])
    return ink_centre_x - width / 2.0, ink_centre_y - height / 2.0, width, height, radius


def _recess_strips(
    x0: float,
    y0: float,
    width: float,
    height: float,
    radius: float,
) -> List[Tuple[float, float, float, float, float]]:
    """Slice a rounded rect into horizontal bands, dense near the corners.

    ASS has no gradient fill and no blur, so the pill is approximated by
    stacking bands. Uniform bands show a staircase on the corner arcs, so the
    cut points follow a cosine inside each corner and run coarse through the
    straight middle.
    """
    radius = max(0.0, min(radius, width / 2.0, height / 2.0))
    bottom = y0 + height
    corner_steps = 7 if radius >= 6.0 else 2
    cuts: List[float] = []
    if radius > 0.0:
        for index in range(corner_steps + 1):
            angle = (math.pi / 2.0) * index / corner_steps
            cuts.append(y0 + radius * (1.0 - math.cos(angle)))
            cuts.append(bottom - radius * (1.0 - math.cos(angle)))
    middle_top, middle_bottom = y0 + radius, bottom - radius
    if middle_bottom > middle_top:
        steps = max(1, int(round((middle_bottom - middle_top) / 16.0)))
        cuts.extend(
            middle_top + (middle_bottom - middle_top) * index / steps
            for index in range(steps + 1)
        )
    cuts.append(y0)
    cuts.append(bottom)
    ordered = sorted({round(value, 1) for value in cuts})

    bands: List[Tuple[float, float, float, float, float]] = []
    for top, edge in zip(ordered, ordered[1:]):
        if edge - top < 0.5:
            continue
        middle = (top + edge) / 2.0
        inset = 0.0
        if radius > 0.0:
            distance = min(middle - y0, bottom - middle)
            if distance < radius:
                inset = radius - math.sqrt(
                    max(0.0, radius * radius - (radius - distance) ** 2)
                )
        bands.append(
            (x0 + inset, x0 + width - inset, top, edge, (middle - y0) / height)
        )
    return bands


def _hex_rgb(value: Any) -> Tuple[int, int, int]:
    text = str(value or "").strip().lstrip("#")
    if len(text) < 6:
        return (255, 255, 255)
    try:
        return tuple(int(text[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except (TypeError, ValueError):
        return (255, 255, 255)


def _ass_inline_rgb(rgb: Tuple[int, int, int]) -> str:
    red, green, blue = rgb
    return f"&H{blue:02X}{green:02X}{red:02X}&"


def _recess_pill_events(
    x0: float,
    y0: float,
    width: float,
    height: float,
    radius: float,
    resolved: Dict[str, Any],
    prefix: str,
    fade: str,
) -> List[str]:
    """One event per gradient band.

    libass merges multiple ``\\p1`` blocks inside a single event into one
    drawing, so each band needs its own event. Bands are ~14 px tall, which
    keeps the banding below the noise floor of the reference's soft edges.
    """
    start = _hex_rgb(resolved["pill_gradient_start"])
    end = _hex_rgb(resolved["pill_gradient_end"])
    # ASS alpha is inverted: 0 is opaque, 255 is invisible.
    alpha = int(round((1.0 - float(resolved.get("pill_alpha", 1.0))) * 255))
    alpha_tag = f"\\alpha&H{alpha:02X}&" if alpha else ""
    events: List[str] = []
    for left, right, top, bottom, ratio in _recess_strips(
        x0, y0, width, height, radius
    ):
        colour = tuple(
            int(round(a + (b - a) * ratio)) for a, b in zip(start, end)
        )
        drawing = (
            f"m {left:.0f} {top:.0f} l {right:.0f} {top:.0f} "
            f"l {right:.0f} {bottom:.0f} l {left:.0f} {bottom:.0f}"
        )
        events.append(
            f"{{{prefix}{fade}\\p1\\c{_ass_inline_rgb(colour)}{alpha_tag}}}"
            f"{drawing}{{\\p0}}"
        )
    return events


def _generate_recess_ass(
    cards: Sequence[Dict[str, Any]],
    resolved: Dict[str, Any],
    script_title: str,
    use_hinglish: bool,
    play_res_x: int,
    play_res_y: int,
    base_ass: str,
    highlight_ass: str,
    outline_ass: str,
    back_ass: str,
) -> str:
    """Recess: centre each word, reveal it in place, and slide a pill behind it."""
    words = _flatten_caption_words(
        cards,
        use_hinglish,
        bool(resolved["uppercase"]),
        str(resolved.get("accent_mode", "content")),
    )
    is_portrait = play_res_y > play_res_x
    default_max_words = 4 if is_portrait else 10
    max_words = int(resolved.get("max_words_per_phrase") or default_max_words)
    if is_portrait:
        max_words = min(max_words, 4)
    phrases = _group_phrases(
        words,
        float(resolved["phrase_gap_ms"]) / 1000.0,
        max_words=max_words,
        split_on_punct=False,
        accent_mode=str(resolved.get("accent_mode", "content")),
        grouping=str(resolved.get("kinetic_grouping", "flow")),
    )

    base_em = _recess_base_em(play_res_x, play_res_y, resolved)
    pill_em = base_em * _RECESS_PILL_EM_RATIO
    font_name = str(resolved["font"])
    centre_x = play_res_x / 2.0
    centre_y = play_res_y * float(resolved["anchor_y"]) / 100.0
    max_width = _kinetic_max_width(play_res_x, play_res_y, int(resolved["max_width"]))

    reveal_fade = int(resolved["reveal_fade_ms"])
    reveal_spring = int(resolved["reveal_spring_ms"])
    spring_scale = round(float(resolved["reveal_spring_scale"]) * 100.0)
    pill_fade = int(resolved["pill_fade_ms"])
    pill_slide = int(resolved["pill_slide_ms"])

    header = f"""[Script Info]
; Script generated by Hinglish Subtitles Studio v2.5 (recess pill)
Title: {script_title}
ScriptType: v4.00+
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: {play_res_x}
PlayResY: {play_res_y}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: RecessKinetic,{font_name},{int(round(base_em))},{highlight_ass},{base_ass},{outline_ass},{back_ass},-1,0,0,0,{_KINETIC_ASS_SCALE_X},100,0,0,1,0,0,5,0,0,0,1
Style: RecessPill,{font_name},{int(round(base_em))},{highlight_ass},{base_ass},{outline_ass},{back_ass},-1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def dialogue(style: str, layer: int, start: float, end: float, body: str) -> str:
        start_cs = max(0, int(round(start * 100.0)))
        end_cs = max(start_cs + 1, int(round(end * 100.0)))
        return (
            f"Dialogue: {layer},{format_ass_time(start_cs / 100.0)},"
            f"{format_ass_time(end_cs / 100.0)},{style},,0,0,0,,{body}"
        )

    timed: List[Tuple[float, int, str]] = []

    for phrase_index, phrase in enumerate(phrases):
        if not phrase:
            continue
        first_start = max(0.0, phrase[0]["start"])
        last = phrase[-1]
        next_start = (
            phrases[phrase_index + 1][0]["start"]
            if phrase_index + 1 < len(phrases)
            else None
        )
        natural_end = max(last["end"], last["start"] + 0.35)
        if next_start is not None and next_start > first_start:
            display_end = min(next_start, natural_end + 1.30)
        else:
            display_end = natural_end + _KINETIC_HOLD_SEC
        display_end = max(display_end, first_start + 0.05)
        if display_end <= first_start:
            continue

        scales = _kinetic_scales(phrase, resolved)
        placed = _recess_layout(
            phrase, scales, base_em, max_width, font_name, centre_x, centre_y
        )
        for position, item in enumerate(placed):
            word = item["word"]
            start = max(0.0, float(word["start"]))
            if start >= display_end - 1e-6:
                continue
            previous = placed[position - 1] if position > 0 else None
            next_start_word = (
                float(placed[position + 1]["word"]["start"])
                if position + 1 < len(placed)
                else display_end
            )
            pill_end = min(display_end, max(start + 0.05, next_start_word))

            reveal = (
                f"{{\\an5\\pos({item['x']:.0f},{item['y']:.0f})"
                f"\\fs{max(8, int(round(item['em'])))}"
                f"\\c&HFFFFFF&\\fad({reveal_fade},{reveal_fade})"
                # \fscx is absolute in libass, so it must end on the style's
                # condensation or the spring silently un-squeezes the type.
                f"\\fscx{_KINETIC_ASS_SCALE_X * spring_scale / 100.0:.1f}"
                f"\\fscy{spring_scale}"
                f"\\t(0,{reveal_spring},"
                f"\\fscx{_KINETIC_ASS_SCALE_X}\\fscy100)}}"
            )
            timed.append(
                (start, 1, dialogue("RecessKinetic", 1, start, display_end, reveal + word["text"]))
            )

            x0, y0, width, height, radius = _recess_pill_box(item, resolved, pill_em)
            if (
                previous is not None
                and pill_slide > 0
                and previous["line"] == item["line"]
            ):
                origin = (
                    f"\\an7\\move({previous['x'] - item['x']:.0f},"
                    f"{previous['y'] - item['y']:.0f},0,0,0,{pill_slide})"
                )
            else:
                origin = "\\an7\\pos(0,0)"
            fade_out = pill_fade if position + 1 >= len(placed) else 0
            for body in _recess_pill_events(
                x0,
                y0,
                width,
                height,
                radius,
                resolved,
                origin,
                f"\\fad({pill_fade},{fade_out})",
            ):
                timed.append(
                    (start, 0, dialogue("RecessPill", 0, start, pill_end, body))
                )

    if not timed:
        # No timed words: one static centred line per card.
        for card in cards:
            if not isinstance(card, dict):
                continue
            start = _safe_float(card.get("start"), 0.0)
            end = _safe_float(card.get("end"), start + 2.0)
            text = str(
                card.get("hinglish_text" if use_hinglish else "original_text") or ""
            ).strip()
            if not text:
                continue
            if resolved["uppercase"]:
                text = text.upper()
            body = (
                f"{{\\an5\\pos({centre_x:.0f},{centre_y:.0f})"
                f"\\fs{max(8, int(round(base_em)))}\\c&HFFFFFF&}}"
                f"{escape_ass_text(text)}"
            )
            timed.append((start, 1, dialogue("RecessKinetic", 1, start, end, body)))

    timed.sort(key=lambda entry: (entry[0], entry[1]))
    return header + "\n".join(entry[2] for entry in timed) + "\n"


def generate_karaoke_ass(
    cards: List[Dict[str, Any]],
    script_title: str = "Hinglish Subtitles - Karaoke",
    play_res_x: int = 1080,
    play_res_y: int = 1920,
    font_name: Optional[str] = None,
    font_size: Optional[int] = None,
    primary_color: Optional[str] = None,
    secondary_color: Optional[str] = None,
    outline_color: Optional[str] = None,
    back_color: Optional[str] = None,
    outline_width: Optional[int] = None,
    shadow_depth: Optional[int] = None,
    margin_v: Optional[int] = None,
    use_hinglish: bool = True,
    style: Optional[Any] = None,
    aspect: str = "9:16",
) -> str:
    """
    Generate a complete .ass script with word-level karaoke timing tags (\\k).

    `style` is a preset id or a partial style dict (see caption_styles.py).
    Legacy keyword arguments still work and are only applied when `style` is None.
    """
    resolved = resolve_style(style) if style is not None else dict(PRESETS[DEFAULT_STYLE_ID])
    profile = aspect_profile(aspect)

    if style is None:
        resolved["uppercase"] = False
        if font_name:
            resolved["font"] = font_name
        if font_size:
            resolved["font_size"] = font_size
        if outline_width is not None:
            resolved["outline_width"] = outline_width
        if shadow_depth is not None:
            resolved["shadow"] = shadow_depth
        if margin_v is not None:
            resolved["margin_v"] = margin_v
        base_ass = _as_ass_color(primary_color, "&H00FFFFFF")
        highlight_ass = _as_ass_color(secondary_color, "&H0000C7FF")
        outline_ass = _as_ass_color(outline_color, "&H00000000")
        back_ass = _as_ass_color(back_color, "&H7F000000")
    else:
        base_ass = hex_to_ass(resolved["base_color"], "&H00FFFFFF")
        highlight_ass = hex_to_ass(resolved["highlight_color"], "&H0000C7FF")
        outline_ass = hex_to_ass(resolved["outline_color"], "&H00000000")
        back_ass = hex_to_ass(resolved["back_color"], "&H7F000000")

    if play_res_x == 1080 and play_res_y == 1920:
        play_res_x = profile["play_res_x"]
        play_res_y = profile["play_res_y"]

    if resolved.get("motion") == "word-pop":
        if resolved.get("pill"):
            return _generate_recess_ass(
                cards,
                resolved,
                script_title,
                use_hinglish,
                play_res_x,
                play_res_y,
                base_ass,
                highlight_ass,
                outline_ass,
                back_ass,
            )
        return _generate_kinetic_ass(
            cards,
            resolved,
            script_title,
            use_hinglish,
            play_res_x,
            play_res_y,
            base_ass,
            highlight_ass,
            outline_ass,
            back_ass,
        )

    size = max(12, int(round(resolved["font_size"] * profile["font_scale"])))
    margin = max(0, int(round(resolved["margin_v"] * profile["margin_scale"])))
    bold = -1 if resolved["bold"] else 0
    border_style = 3 if resolved["box"] else 1
    shadow = 0 if resolved["box"] else resolved["shadow"]
    style_name = "HormoziYellow" if resolved["id"] == "hormozi" else "CaptionStyle"
    fade = r"{\fad(80,0)}" if resolved["animation"] == "fade" else ""
    use_upper = resolved["uppercase"]

    header = f"""[Script Info]
; Script generated by Hinglish Subtitles Studio v2.5
Title: {script_title}
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: {play_res_x}
PlayResY: {play_res_y}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: {style_name},{resolved["font"]},{size},{highlight_ass},{base_ass},{outline_ass},{back_ass},{bold},0,0,0,100,100,0,0,{border_style},{resolved["outline_width"]},{shadow},{resolved["alignment"]},40,40,{margin},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    dialogue_lines = []

    for card in cards:
        card_start = card.get("start", 0.0)
        card_end = card.get("end", card_start + 2.0)
        start_str = format_ass_time(card_start)
        end_str = format_ass_time(card_end)

        words = card.get("words", [])
        if not words:
            text = card.get("hinglish_text" if use_hinglish else "original_text", "")
            if use_upper:
                text = text.upper()
            dialogue_lines.append(
                f"Dialogue: 0,{start_str},{end_str},{style_name},,0,0,0,,{fade}{escape_ass_text(text)}"
            )
            continue

        karaoke_parts = []
        cur_t = card_start

        for idx, w in enumerate(words):
            w_start = w.get("start", cur_t)
            w_end = w.get("end", w_start + 0.3)
            w_text = w.get("hinglish" if use_hinglish else "word", "")

            dur_cs = max(1, int(round((w_end - w_start) * 100)))

            # Karaoke \k is a running sum, so every silence inside the card has
            # to be emitted as its own empty \k. Skipping them (only the first
            # word used to get a lead) made the highlight run early by the sum
            # of the gaps, while the live overlay used absolute word starts.
            gap_cs = int(round((w_start - cur_t) * 100))
            if gap_cs > 0:
                karaoke_parts.append(f"{{\\k{gap_cs}}}")

            clean_word = escape_ass_text(w_text).strip()
            if use_upper:
                clean_word = clean_word.upper()
            if clean_word:
                karaoke_parts.append(f"{{\\k{dur_cs}}}{clean_word} ")

            cur_t = w_end

        dialogue_text = "".join(karaoke_parts).strip()
        dialogue_lines.append(
            f"Dialogue: 0,{start_str},{end_str},{style_name},,0,0,0,,{fade}{dialogue_text}"
        )

    return header + "\n".join(dialogue_lines) + "\n"
