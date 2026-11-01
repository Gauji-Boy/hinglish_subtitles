# Implementation Plan: Phase 1 — Karaoke / Animated Word Subtitles (.ass & Word-Level JSON)

## Overview
Phase 1 introduces millisecond-accurate word-level animated subtitles into the Hinglish Subtitles Studio. It enables creator-focused bouncy / karaoke subtitle exports (`.ass` with Alex Hormozi/Reels highlight tags) and structured word-level JSON for external timeline editors (Premiere, CapCut, DaVinci Resolve).

---

## Architecture & Dependency Graph

```
Faster-Whisper Word Timestamps (already present in words_to_cards)
    │
    ▼
Preserve word spans inside each subtitle card: [{'start', 'end', 'word', 'hinglish_word'}]
    │
    ├──> 1. ASS Karaoke Generator (libass format with \k / \kf animated highlight styles)
    │
    ├──> 2. Word-Level JSON Exporter
    │
    └──> 3. API & Server Endpoints (/api/export/ass, /api/export/word-json)
            │
            └──> 4. Frontend UI Export Buttons (.ASS Karaoke, .JSON)
```

---

## Detailed Task Breakdown

### Task 1: Preserve Word Spans in Subtitle Cards (`hinglish_upgrades.py`)
- **Description:** Currently, `words_to_cards()` returns only aggregated card text (`original_text`, `hinglish_text`). Update the semantic chunker and `words_to_cards` to attach the list of individual word tokens with their start/end timestamps and transliterated forms to each card.
- **Acceptance Criteria:**
  - Each returned card contains a `"words"` array: `[{"start": float, "end": float, "word": str, "hinglish": str}]`.
  - All existing tests pass with 100% backwards compatibility (i.e. `"original_text"` and `"hinglish_text"` fields remain unchanged).
- **Files:** `c:\Users\susha\Documents\General\hinglish_subtitles\hinglish_upgrades.py`

### Task 2: Implement ASS Karaoke Generator (`karaoke_ass.py`)
- **Description:** Create a dedicated helper module `karaoke_ass.py` that formats subtitle cards into valid Advanced SubStation Alpha (`.ass` v4.00+) files.
- **Acceptance Criteria:**
  - Includes standard `[Script Info]`, `[V4+ Styles]`, and `[Events]` sections.
  - Generates two presets:
    - **`Hormozi / TikTok Bouncy`**: Large font (`Impact` or `Montserrat ExtraBold`), high-contrast primary color (`#FFFFFF`), outline (`#000000`), active karaoke highlight (`#FFC700` Yellow or `#38BDF8` Cyan).
    - **`Smooth Word Highlight`**: Subtle continuous karaoke highlighting using `{\k<centiseconds>}` tags.
  - Timestamps formatted accurately as `H:MM:SS.cc` (centiseconds).
  - Escapes special ASS control characters (`{`, `}`).
- **Files:** `c:\Users\susha\Documents\General\hinglish_subtitles\karaoke_ass.py`

### Task 3: Expose Word-Level JSON & ASS in Engines (`hinglish_engine.py` & `hindi_to_english_engine.py`)
- **Description:** Expose `"ass_karaoke"` and `"word_timeline"` in the return dictionary of `generate_subtitles()` and `generate_english_subtitles()`.
- **Acceptance Criteria:**
  - Return dictionary contains:
    - `"ass_karaoke"`: string content of the generated `.ass` file.
    - `"segments"`: each segment contains `"words"` list with word-level timings.
- **Files:**
  - `c:\Users\susha\Documents\General\hinglish_subtitles\hinglish_engine.py`
  - `c:\Users\susha\Documents\General\hinglish_subtitles\hindi_to_english_engine.py`

### Task 4: Server Download Endpoints & Frontend UI
- **Description:** Add `/api/export/ass` and update UI export actions to download `.ass` directly.
- **Acceptance Criteria:**
  - `GET /api/export/ass` or client-side blob download works smoothly.
  - UI export options include `.SRT`, `.VTT`, `.TXT`, and `.ASS (Karaoke)`.
- **Files:**
  - `c:\Users\susha\Documents\General\hinglish_subtitles\server.py`
  - `c:\Users\susha\Documents\General\hinglish_subtitles\static\app.js`
  - `c:\Users\susha\Documents\General\hinglish_subtitles\static\index.html`

### Task 5: Comprehensive Automated Tests
- **Description:** Write unit tests in `tests/test_karaoke_ass.py` verifying ASS syntax, centisecond calculations, word alignment, and API responses.
- **Acceptance Criteria:**
  - Tests verify `.ass` header validity, style presence, and dialogue line count.
  - `python -m pytest tests -q` passes 100%.
- **Files:** `c:\Users\susha\Documents\General\hinglish_subtitles\tests\test_karaoke_ass.py`
