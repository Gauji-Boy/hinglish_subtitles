"""
caption_styles.py - Caption style schema, built-in presets, and aspect profiles.

Single source of truth for the ASS generator and the HTTP API. Colours in the
schema are CSS hex (#RRGGBB or #RRGGBBAA); the generator converts them to ASS
ABGR. `base_color` is the upcoming (unsung) word colour; `highlight_color` is
the spoken/current word colour, matching libass \\k semantics.
"""

import copy
import re
from typing import Any, Dict, List, Optional

DEFAULT_STYLE_ID = "hormozi"

_HEX_RE = re.compile(r"^#([0-9A-Fa-f]{6})([0-9A-Fa-f]{2})?$")
_ID_RE = re.compile(r"^[a-z0-9_-]{1,32}$")

ALLOWED_FONTS = (
    "Impact",
    "Arial Black",
    "Segoe UI",
    "Arial",
    "Verdana",
    "Trebuchet MS",
    "Georgia",
    "Consolas",
)

# Geometry is authored for 9:16 (1080x1920). Other aspects scale from it.
ASPECTS: Dict[str, Dict[str, Any]] = {
    "9:16": {"play_res_x": 1080, "play_res_y": 1920, "font_scale": 1.0, "margin_scale": 1.0},
    "16:9": {"play_res_x": 1920, "play_res_y": 1080, "font_scale": 0.75, "margin_scale": 0.375},
    "1:1": {"play_res_x": 1080, "play_res_y": 1080, "font_scale": 0.82, "margin_scale": 0.46},
}

_ASPECT_ALIASES = {
    "9:16": "9:16",
    "vertical": "9:16",
    "portrait": "9:16",
    "16:9": "16:9",
    "horizontal": "16:9",
    "landscape": "16:9",
    "1:1": "1:1",
    "square": "1:1",
}

PRESETS: Dict[str, Dict[str, Any]] = {
    "hormozi": {
        "id": "hormozi",
        "name": "Hormozi Kinetic",
        "font": "Impact",
        "font_size": 68,
        "bold": True,
        "uppercase": True,
        "base_color": "#FFFFFF",
        "highlight_color": "#FFC700",
        "outline_color": "#000000",
        "back_color": "#00000080",
        "outline_width": 5,
        "shadow": 2,
        "box": False,
        "margin_v": 240,
        "alignment": 2,
        "animation": "fade",
    },
    "vox": {
        "id": "vox",
        "name": "Vox Clean",
        "font": "Segoe UI",
        "font_size": 62,
        "bold": True,
        "uppercase": False,
        "base_color": "#FFFFFF",
        "highlight_color": "#38BDF8",
        "outline_color": "#000000",
        "back_color": "#00000080",
        "outline_width": 3,
        "shadow": 1,
        "box": False,
        "margin_v": 170,
        "alignment": 2,
        "animation": "fade",
    },
    "cyber": {
        "id": "cyber",
        "name": "Cyber Lime",
        "font": "Consolas",
        "font_size": 64,
        "bold": True,
        "uppercase": True,
        "base_color": "#E5E7EB",
        "highlight_color": "#BEF264",
        "outline_color": "#000000",
        "back_color": "#00000080",
        "outline_width": 4,
        "shadow": 2,
        "box": False,
        "margin_v": 220,
        "alignment": 2,
        "animation": "fade",
    },
    "blackout": {
        "id": "blackout",
        "name": "Blackout Box",
        "font": "Arial Black",
        "font_size": 62,
        "bold": True,
        "uppercase": True,
        "base_color": "#FFFFFF",
        "highlight_color": "#FFD400",
        "outline_color": "#000000",
        "back_color": "#000000",
        "outline_width": 18,
        "shadow": 0,
        "box": True,
        "margin_v": 220,
        "alignment": 2,
        "animation": "fade",
    },
    "editorial": {
        "id": "editorial",
        "name": "Editorial Serif",
        "font": "Georgia",
        "font_size": 60,
        "bold": True,
        "uppercase": False,
        "base_color": "#F5F1E8",
        "highlight_color": "#E7C873",
        "outline_color": "#000000",
        "back_color": "#00000080",
        "outline_width": 2,
        "shadow": 3,
        "box": False,
        "margin_v": 140,
        "alignment": 2,
        "animation": "fade",
    },
    # Local lookalikes inspired by the Captions.ai / Mirage template gallery.
    # The gallery itself only exposes template IDs and preview MP4s, so these
    # values are hand-tuned approximations rather than imported style data.
    "buzz": {
        "id": "buzz",
        "name": "Buzz",
        "font": "Arial Black",
        "font_size": 64,
        "bold": True,
        "uppercase": True,
        "base_color": "#FFFFFF",
        "highlight_color": "#C0B0F0",
        "outline_color": "#000000",
        "back_color": "#00000080",
        "outline_width": 0,
        "shadow": 4,
        "box": False,
        "margin_v": 240,
        "alignment": 2,
        "animation": "fade",
    },
    "medusa": {
        "id": "medusa",
        "name": "Medusa",
        "font": "Arial Black",
        "font_size": 62,
        "bold": True,
        "uppercase": True,
        "base_color": "#FFFFFF",
        "highlight_color": "#3BE80D",
        "outline_color": "#000000",
        "back_color": "#000000E6",
        "outline_width": 18,
        "shadow": 0,
        "box": True,
        "margin_v": 220,
        "alignment": 2,
        "animation": "fade",
    },
    "cartwheel": {
        "id": "cartwheel",
        "name": "Cartwheel Black",
        "font": "Arial Black",
        "font_size": 62,
        "bold": True,
        "uppercase": True,
        "base_color": "#FFFFFF",
        "highlight_color": "#8A16F0",
        "outline_color": "#000000",
        "back_color": "#000000E6",
        "outline_width": 18,
        "shadow": 0,
        "box": True,
        "margin_v": 220,
        "alignment": 2,
        "animation": "fade",
    },
    "heat": {
        "id": "heat",
        "name": "Heat",
        "font": "Arial Black",
        "font_size": 66,
        "bold": True,
        "uppercase": False,
        "base_color": "#FF1A1A",
        "highlight_color": "#FF5A1F",
        "outline_color": "#000000",
        "back_color": "#00000080",
        "outline_width": 0,
        "shadow": 4,
        "box": False,
        "margin_v": 240,
        "alignment": 2,
        "animation": "fade",
    },
    "neon": {
        "id": "neon",
        "name": "Neon",
        "font": "Segoe UI",
        "font_size": 64,
        "bold": True,
        "uppercase": False,
        "base_color": "#FFFFFF",
        "highlight_color": "#F08AB5",
        "outline_color": "#000000",
        "back_color": "#00000080",
        "outline_width": 0,
        "shadow": 4,
        "box": False,
        "margin_v": 220,
        "alignment": 2,
        "animation": "fade",
    },
    "magazine": {
        "id": "magazine",
        "name": "Magazine",
        "font": "Segoe UI",
        "font_size": 62,
        "bold": True,
        "uppercase": False,
        "base_color": "#FFFFFF",
        "highlight_color": "#F5E63D",
        "outline_color": "#000000",
        "back_color": "#00000080",
        "outline_width": 0,
        "shadow": 2,
        "box": False,
        "margin_v": 200,
        "alignment": 2,
        "animation": "fade",
    },
    "techwave": {
        "id": "techwave",
        "name": "Techwave",
        "font": "Arial Black",
        "font_size": 72,
        "bold": True,
        "uppercase": True,
        "base_color": "#FFFFFF",
        "highlight_color": "#FFFFFF",
        "outline_color": "#000000",
        "back_color": "#00000080",
        "outline_width": 6,
        "shadow": 4,
        "box": False,
        "margin_v": 220,
        "alignment": 2,
        "animation": "fade",
    },
    "minima": {
        "id": "minima",
        "name": "Minima",
        "font": "Segoe UI",
        "font_size": 64,
        "bold": True,
        "uppercase": False,
        "base_color": "#FFFFFF",
        "highlight_color": "#FFFFFF",
        "outline_color": "#000000",
        "back_color": "#00000080",
        "outline_width": 0,
        "shadow": 0,
        "box": False,
        "margin_v": 180,
        "alignment": 2,
        "animation": "none",
    },
    "honeypunch": {
        "id": "honeypunch",
        "name": "123 Honey Punch",
        # Reference: 123effect (1280x720) - heavy geometric type, white
        # connective words, oversized gold punch words, revealed as spoken.
        "font": "Arial",
        "font_size": 128,
        "bold": True,
        "uppercase": False,
        "base_color": "#FFFFFF",
        "highlight_color": "#F6C83E",
        "outline_color": "#000000",
        "back_color": "#00000080",
        "outline_width": 10,
        "shadow": 3,
        "box": False,
        "margin_v": 0,
        "alignment": 5,
        "animation": "none",
        "motion": "word-pop",
        # Measured off the Resolve frames word by word: connective words are
        # 1.0x white; gold punch words are 1.5x (bakery ascender 78 px vs
        # "the" 52 px). Gold words that are not punch sit at 1.0x — the
        # frames have no middle tier. The active word never inflates.
        "active_scale": 150,
        "accent_scale": 150,
        "accent_size_scale": 100,
        # The normal four-line block sits a little lower than the two-line
        # title phrase; karaoke_ass and the live renderer subtract a small
        # title offset from this value.
        "anchor_y": 22,
        "max_width": 55,
        "phrase_gap_ms": 650,
        "pop_ms": 0,
        "settle_ms": 0,
        "accent_mode": "content",
        # Frames: phrase 1 sits flush right, phrase 2 flush left, ~7% in.
        "kinetic_layout": "alternate",
        # One held block per sentence, not one per Whisper card: the reference
        # keeps a four-line poster up while the speaker works through it.
        "kinetic_grouping": "poster",
        "max_words_per_phrase": 10,
    },
    "recess": {
        "id": "recess",
        "name": "Recess",
        # Reference: centred, all-caps heavy geometric type on a flat dark
        # background. Each spoken word is revealed in place; the active word
        # carries a rounded lime -> periwinkle gradient pill. Punch words are
        # ~2x and own their card.
        "font": "Arial Black",
        "font_size": 136,
        "bold": True,
        "uppercase": True,
        # White type: the pill supplies the colour, not the glyphs.
        "base_color": "#FFFFFF",
        "highlight_color": "#FFFFFF",
        "outline_color": "#000000",
        "back_color": "#00000000",
        "outline_width": 0,
        "shadow": 0,
        "box": False,
        "margin_v": 0,
        "alignment": 5,
        "animation": "none",
        "motion": "word-pop",
        # The active word keeps its size; the pill is the emphasis.
        "active_scale": 100,
        # Measured punch/normal cap ratio is 2.03.
        "accent_scale": 203,
        # The block is centred on the canvas (reference y ~538/1080).
        "anchor_y": 50,
        "max_width": 82,
        "phrase_gap_ms": 450,
        "pop_ms": 0,
        "settle_ms": 0,
        "accent_mode": "content",
        # Centred on both axes: the reference block sits at y ~50%.
        "kinetic_layout": "middle",
        "max_words_per_phrase": 0,
        # libass renders Arial Black at ~0.72x the nominal \fs that Pillow
        # reports, so the emitted em must be scaled up to reproduce the
        # reference 82% line width (measured: \fs 197 at 1080p).
        "kinetic_size_scale": 2.14,
        "kinetic_grouping": "punch",
        "pill": True,
        "pill_gradient_start": "#D2E860",
        "pill_gradient_end": "#A793FF",
        # Padding/radius are em fractions of the NORMAL em, not the word's,
        # because the measured pill padding is identical for normal and punch.
        "pill_pad_x": 0.16,
        "pill_pad_y": 0.32,
        "pill_radius": 0.26,
        # The reference pill is the lime -> periwinkle ramp at ~58% opacity;
        # measured over the #1C1E1D backdrop it reads as olive -> lavender.
        "pill_alpha": 0.58,
        # ~2 frames in/out and ~4 frames of slide at 32 fps.
        "pill_fade_ms": 65,
        "pill_slide_ms": 130,
        # ~2 frames to full alpha and ~4 frames of spring at 32 fps.
        "reveal_fade_ms": 65,
        "reveal_spring_ms": 130,
        "reveal_spring_scale": 1.10,
    },
    "blank": {
        "id": "blank",
        "name": "Blank (Start From Scratch)",
        "font": "Segoe UI",
        "font_size": 60,
        "bold": True,
        "uppercase": False,
        "base_color": "#FFFFFF",
        "highlight_color": "#FFFFFF",
        "outline_color": "#000000",
        "back_color": "#00000080",
        "outline_width": 3,
        "shadow": 0,
        "box": False,
        "margin_v": 180,
        "alignment": 2,
        "animation": "none",
    },
}


def hex_to_ass(value: str, fallback: str = "&H00FFFFFF") -> str:
    """Convert #RRGGBB or #RRGGBBAA to ASS &HAABBGGRR (alpha is inverted)."""
    match = _HEX_RE.match(str(value or "").strip())
    if not match:
        return fallback
    rgb = match.group(1)
    css_alpha = int(match.group(2), 16) if match.group(2) else 255
    ass_alpha = 255 - css_alpha
    r, g, b = rgb[0:2], rgb[2:4], rgb[4:6]
    return f"&H{ass_alpha:02X}{b}{g}{r}".upper()


def aspect_profile(aspect: str = "9:16") -> Dict[str, Any]:
    """Return PlayRes and scale factors for a supported aspect (aliases allowed)."""
    key = _ASPECT_ALIASES.get(str(aspect or "").strip().lower(), "9:16")
    return copy.deepcopy(ASPECTS[key])


def _number(value: Any, default: int, low: int, high: int) -> int:
    try:
        num = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    return max(low, min(high, num))


def _bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "1", "yes", "on"):
            return True
        if lowered in ("false", "0", "no", "off"):
            return False
    return default


def _float(value: Any, default: float, low: float, high: float) -> float:
    """Coerce to float, clamp, and fall back on non-numeric input."""
    try:
        num = float(value)
    except (TypeError, ValueError):
        return default
    if num != num or num in (float("inf"), float("-inf")):
        return default
    return max(low, min(high, num))


def _color(value: Any, default: str) -> str:
    text = str(value or "").strip()
    return text.upper() if _HEX_RE.match(text) else default


def resolve_style(style: Optional[Any] = None) -> Dict[str, Any]:
    """Normalize a style id or partial dict into a complete, clamped style."""
    if style is None:
        style = {}
    if isinstance(style, str):
        style = {"id": style}
    if not isinstance(style, dict):
        style = {}

    style_id = str(style.get("id") or DEFAULT_STYLE_ID).strip().lower()
    if not _ID_RE.match(style_id):
        style_id = DEFAULT_STYLE_ID

    base = copy.deepcopy(PRESETS.get(style_id, PRESETS[DEFAULT_STYLE_ID]))
    for key, value in style.items():
        if value is not None:
            base[key] = value

    base["id"] = style_id if style_id in PRESETS or style_id == "custom" else DEFAULT_STYLE_ID
    if style_id == "custom":
        base["id"] = "custom"
        base["name"] = str(base.get("name") or "Custom")[:40].replace("\n", " ").strip() or "Custom"
    else:
        base["name"] = PRESETS[base["id"]]["name"]

    font = str(base.get("font") or "").strip()
    base["font"] = font if font in ALLOWED_FONTS else "Segoe UI"
    base["font_size"] = _number(base.get("font_size"), 60, 24, 140)
    base["bold"] = _bool(base.get("bold"), True)
    base["uppercase"] = _bool(base.get("uppercase"), False)
    base["base_color"] = _color(base.get("base_color"), "#FFFFFF")
    base["highlight_color"] = _color(base.get("highlight_color"), "#FFC700")
    base["outline_color"] = _color(base.get("outline_color"), "#000000")
    base["back_color"] = _color(base.get("back_color"), "#00000080")
    base["outline_width"] = _number(base.get("outline_width"), 3, 0, 40)
    base["shadow"] = _number(base.get("shadow"), 0, 0, 12)
    base["box"] = _bool(base.get("box"), False)
    base["margin_v"] = _number(base.get("margin_v"), 180, 0, 900)
    alignment = _number(base.get("alignment"), 2, 1, 9)
    base["alignment"] = alignment if alignment in (2, 5, 8) else 2
    base["animation"] = "fade" if str(base.get("animation")).lower() == "fade" else "none"

    # Kinetic typography (v2). `none` keeps the classic one-card karaoke path.
    motion = str(base.get("motion") or "none").strip().lower()
    base["motion"] = motion if motion in ("none", "word-pop") else "none"
    base["active_scale"] = _number(base.get("active_scale"), 150, 100, 220)
    base["accent_scale"] = _number(base.get("accent_scale"), 150, 100, 210)
    # Middle tier: gold words that are not punch. Default 100 keeps every
    # existing preset byte-identical.
    base["accent_size_scale"] = _number(base.get("accent_size_scale"), 100, 100, 210)
    base["anchor_y"] = _number(base.get("anchor_y"), 42, 0, 100)
    base["max_width"] = _number(base.get("max_width"), 82, 35, 100)
    base["phrase_gap_ms"] = _number(base.get("phrase_gap_ms"), 650, 100, 3000)
    base["pop_ms"] = _number(base.get("pop_ms"), 0, 0, 1000)
    base["settle_ms"] = _number(base.get("settle_ms"), 0, 0, 1000)
    accent_mode = str(base.get("accent_mode") or "content").strip().lower()
    base["accent_mode"] = accent_mode if accent_mode in ("content", "all", "none") else "content"
    kinetic_layout = str(base.get("kinetic_layout") or "center").strip().lower()
    base["kinetic_layout"] = (
        kinetic_layout if kinetic_layout in ("center", "middle", "right", "alternate") else "center"
    )
    base["max_words_per_phrase"] = _number(base.get("max_words_per_phrase"), 0, 0, 20)

    # Recess additions. Every default preserves the previous behaviour of the
    # existing presets: no pill, no reveal envelope, no size scaling, flow
    # grouping.
    base["pill"] = _bool(base.get("pill"), False)
    base["pill_gradient_start"] = _color(base.get("pill_gradient_start"), "#FFFFFF")
    base["pill_gradient_end"] = _color(base.get("pill_gradient_end"), "#FFFFFF")
    base["pill_pad_x"] = _float(base.get("pill_pad_x"), 0.16, 0.0, 1.0)
    base["pill_pad_y"] = _float(base.get("pill_pad_y"), 0.32, 0.0, 1.0)
    base["pill_radius"] = _float(base.get("pill_radius"), 0.21, 0.0, 1.0)
    base["pill_alpha"] = _float(base.get("pill_alpha"), 1.0, 0.0, 1.0)
    base["pill_fade_ms"] = _number(base.get("pill_fade_ms"), 65, 0, 2000)
    base["pill_slide_ms"] = _number(base.get("pill_slide_ms"), 130, 0, 2000)
    base["reveal_fade_ms"] = _number(base.get("reveal_fade_ms"), 0, 0, 2000)
    base["reveal_spring_ms"] = _number(base.get("reveal_spring_ms"), 0, 0, 2000)
    base["reveal_spring_scale"] = _float(base.get("reveal_spring_scale"), 1.0, 1.0, 2.0)
    base["kinetic_size_scale"] = _float(base.get("kinetic_size_scale"), 1.0, 0.25, 2.5)
    grouping = str(base.get("kinetic_grouping") or "flow").strip().lower()
    base["kinetic_grouping"] = grouping if grouping in ("flow", "punch", "poster") else "flow"
    return base


def list_presets() -> List[Dict[str, Any]]:
    """All built-in presets, normalized, in display order."""
    order = (
        "hormozi", "vox", "cyber", "blackout", "editorial",
        "buzz", "medusa", "cartwheel", "heat", "neon", "magazine",
        "techwave", "minima", "honeypunch", "recess", "blank",
    )
    return [resolve_style(order[i]) for i in range(len(order))]
