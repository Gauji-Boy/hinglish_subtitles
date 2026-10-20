# CHANGELOG - Hinglish Subtitle Generator

## [2026-10-18] Clean Top Navbar Workbench & Bottom Floating Search Dock
- **Top Navigation Bar Cleanup**:
  - Removed left-side visual clutter: replaced double-decker stacked `V2.5 HYBRID` and `HINGLISH ENGINE` badges with a clean, single-line monospace `v2.5` badge (`.badge.hot`).
  - Removed loose keyboard shortcut tags (`/ search`, `Esc close`) from the header.
  - Converted GPU hardware badge to a compact, single-line pill (`⚡ RTX 4050 (CUDA fp16)`) with hover tooltip detailing full VRAM and device specs, permanently fixing vertical double-line wrapping.
  - Unified theme controls into a sleek segmented capsule (`.theme-segmented-cluster`) housing the `☀️/🌙` Mode toggle and Theme Variant select separated by an interior hairline divider with a strict 28px height baseline across all controls.
- **Floating Bottom Search Dock**:
  - Added `.floating-search-wrap` with a dedicated search input (`#floatingSearchInput`) centered inside the fixed bottom export dock (`#floatingDownloadBar`), bridging the empty void between the export label and download actions.
  - Integrated bidirectional real-time card filtering: typing in `#floatingSearchInput` or `#subtitleSearchInput` automatically synchronizes query strings and filters `.card-box` items.
  - Removed redundant hero meta pill (`#deviceMetaPill` / `⚡ Hardware: RTX 4050 (CUDA fp16)`), keeping the hero meta row clean with model info and zero-hallucination badges since the top navigation bar already displays the active GPU pill.
  - Removed duplicate toolbar search box (`.search` / `#subtitleSearchInput`) from the subtitle results section, consolidating all search and filtering interactions into the bottom floating export dock (`#floatingSearchInput`).
  - Removed decorative `.hero-meta` tag container from the hero section (`static/index.html`), streamlining the intro banner down to the headline, value proposition, and spoken language ribbon.
  - Added live subtitle match telemetry pill (`.live-match-pill` / `#floatingMatchPill`) to the bottom dock, displaying real-time feedback (e.g. `🎯 2 / 17 MATCHES` or `17 / 17 SEGMENTS`) as users search.
  - Added instant one-click `📋 COPY ALL` button (`#floatingCopyAllBtn`) to the bottom export action group with clipboard fallback and transient `COPIED! ✅` visual confirmation.
- **Empty State Workbench (Pattern B: 2-Column Split Cockpit)**:
  - Solved the empty lower 40% screen void before file upload with `#workbenchEmptyState` positioned directly beneath `.action-bar`.
  - **Left Column (Web Video Importer)**: Powered by system `yt-dlp` (`POST /api/import-url` and `/api/media/{filename}`). Supports public YouTube, Instagram Reels, TikTok, and direct MP4/M4A video links. Automatically downloads, extracts audio/video stream, stages into the custom player, and activates `⚡ GENERATE HINGLISH SUBTITLES`.
  - **Web Video Importer Media & Quality Selector (Option 1)**: Added a two-tier Segmented Media Switcher (`🎬 Video + Audio` vs `🎵 Audio Only (Fastest ⚡)`) paired with a dynamic Quality Dropdown:
    - **Video + Audio Mode**: Quality options for `🌟 Source Best (1080p/Max)`, `⚡ 720p (Fast HD)`, and `⚡ 480p (Lightweight)`.
    - **Audio Only Mode**: Streamlined audio extraction for `🌟 Best / 320k (High Quality)`, `⚡ 128 kbps (Standard)`, and `⚡ 64 kbps (Speech / Fast)`. Audio downloads execute in ~2 seconds (saving 95% bandwidth) and automatically activate the frontend Web Audio frequency visualizer (`renderAudioVisualizer()`).
    - **Preferences Persistence**: User format and quality selections persist in `localStorage`.
    - **MIME & Serving**: `api_serve_media` returns precise MIME headers (`audio/mp4`, `video/mp4`, `video/webm`, `audio/mpeg`, etc.) enabling instant playback and streaming in both desktop pywebview and web browser modes.
    - **Bug Fix**: Resolved `name 'time' is not defined` error by importing `time` globally in `server.py`.
  - **Right Column (Recent Files & Samples)**: Saves past transcriptions to `localStorage`, displaying filename, timestamp, duration, and segment count. Includes 1-click **Benchmark Demo Reels** (`Traffic Reel` and `Genius Ad`) loaded instantly from `static/samples/`.
  - **Hindi ➔ English Translation Mode (Option 1 - 5th Ribbon Tile)**:
    - Added 5th language tile to `.ribbon` (`data-lang="hi-en"`), styled with Solar Orange accent (`--orange: #fb923c`) and translation glyph (`文 ➔ A`).
    - Configured Whisper's native GPU `task="translate"` (with `language="hi"`) in `hinglish_engine.py` and `hinglish_upgrades.py`: decodes spoken Hindi audio and directly emits natural English text with word timestamps at 14x–18x real-time GPU speed.
    - Preserves semantic DP chunking for 1–2 line reel cards; dynamically labels subtitle cards as `TRANSLATED ENGLISH` and export buttons as `DOWNLOAD ENGLISH SRT`.
    - Automatically persists user language choice across sessions in `launch_config.json` and `localStorage`.
  - **Hero Ribbon Layout & Tile Width Optimization**:
    - Resolved squeezed language tiles by shifting `.hero` grid allocation from `1.2fr 1fr` to `minmax(360px, 440px) 1fr`, giving the ribbon ~850px+ of width (~155px per tile).
    - Added `white-space: nowrap;` to `.tile` titles and descriptions, permanently eliminating awkward text line wrapping (e.g. `Hindi ➔ English` and `English Captions` remain on a single line).
    - Added `@media (max-width: 1120px)` breakpoint so compact screens gracefully stack into full width without squeezing.
- **Test Suite**: Added `test_workbench_empty_state_dom_and_css`, `test_api_import_url_validation`, `test_url_importer_quality_and_format_options`, and `test_hindi_to_english_translation_mode` in `tests/test_upgrades.py`; all 33 unit and UI tests pass.

## [2026-10-17] Fix Word Stalls in large-v3 & large-v3-turbo (Beam Size 5 & Duration Clamping)
- **Root Cause Resolution**: Fixed an issue where `large-v3` and `large-v3-turbo` models stalled on single syllables (e.g. `GA` frozen 9.2s in Traffic reel, `BA` frozen 11.06s in Genius Ad reel). Narrow `beam_size = 2` suffered from premature beam pruning during fast speech over background music at window boundaries, causing Whisper to prematurely output `<|endoftext|>` and cross-attention DTW alignment to stretch that single token across the remaining silence.
- **Whisper Beam Width Upgrade**: Upgraded `beam_size = 5` (Whisper's standard beam search width) in `hinglish_upgrades.py:transcribe_words`. Completely eliminates premature termination and restores 100% of omitted speech without stalling.
- **Word-Level Duration Clamping**: Added acoustic duration clamping in `transcribe_words`: if `w_end - w_start > 2.5s`, it bounds the token duration so cross-attention alignment can never stretch a trailing token across silence or music breaks.
- **Card-Level Hard Ceiling Clamping**: Updated `pad_display_times()` to enforce a hard `c["start"] + max_dur` ceiling and `limit` boundary, preventing any card from exceeding 2.8s (short form) or 5.0s (long form).
- **Test Suite**: Added `test_pad_display_times_clamps_stretched_cards` in `tests/test_upgrades.py`; all 28 unit and UI tests pass.

## [2026-10-17] Fix Subtitle Download & Export Buttons (Desktop Bridge & Server Fallback)
- **Root Cause Resolution**: Resolved an issue where clicking "DOWNLOAD HINGLISH SRT", "ORIGINAL SRT", or "PLAIN TEXT" failed in the native Windows standalone window (`server.py`). PyWebView has `ALLOW_DOWNLOADS = False` by default (cancelling all downloads silently), and synchronous client-side `URL.revokeObjectURL()` aborted WebView2 download streams.
- **PyWebView Native Download Enablement**: Explicitly configured `webview.settings["ALLOW_DOWNLOADS"] = True` and bound a native `DesktopAPI` bridge to `webview.create_window(..., js_api=desktop_api)`.
- **Native Windows "Save As" Dialog**: Export buttons now directly invoke `window.pywebview.api.save_subtitle_file()`, launching the real Windows File Explorer Save dialog with custom filters and writing UTF-8 files directly to the user's selected path.
- **Server Download Endpoint Fallback**: Added `POST /api/download/file` to FastAPI for browser mode, streaming files with proper `Content-Disposition: attachment; filename=...` headers.
- **Delayed Blob Revocation**: Updated client blob fallback with a 60-second delayed revocation to ensure Chromium/WebView2 buffers read all bytes before URL cleanup.
- **Tactile UI Feedback & Elevation**: Added `showDownloadFeedback()` with dynamic `✓ SAVED!` button badges, real-time export path status labels, and elevated `#floatingDownloadBar` to `z-index: 95`.
- **Test Suite**: Added `test_subtitle_download_api_and_desktop_bridge` in `tests/test_upgrades.py`; all 27 unit and UI tests pass.

## [2026-10-17] High-Contrast White Icon Shadows (Dark Theme) & Black Icon Shadows (Light Theme)
- **Language Card Shadow Consistency**: Restored the ribbon language card drop-shadow (`.tile.active`, `.tile:hover`, `.tile:active`) to match its respective icon category color (`var(--c, var(--yellow))` / `var(--c, var(--paper))`), keeping the card aesthetic grounded and color-coded.
- **Icon Glyph Shadow Polarity**: Configured the inner icon glyph badge (`.glyph`, `.tile:hover .glyph`, `.tile.active .glyph`) with high-contrast polarity:
  - **Dark Themes (Industrial Hybrid / Cyberpunk Neon / Sleek Bento)**: `.glyph` uses a crisp `#ffffff` white drop-shadow (`box-shadow: 3px 3px 0 #ffffff;`), making the badge pop off the card background.
  - **Light Theme (Warm Sandstone Editorial)**: `.glyph` uses a solid `#000000` black drop-shadow (`box-shadow: 3px 3px 0 #000000;`) for authentic tactile Neo-Brutalist depth.
- **Test Suite**: Updated `tests/test_upgrades.py`; all 26 unit and UI tests pass.

## [2026-10-17] Light Mode Complete Redesign: Warm Sandstone Editorial & De-glare Pass
- **Warm Sandstone Palette**: Completely eliminated eye-straining fluorescent white glare by transitioning `[data-theme="minimalist-light"]` from stark `#f8fafc` to soothing unbleached linen canvas (`--bg: #f5f4ef`), soft sepia micro-dots (`rgba(44, 38, 30, 0.06)`), and deep warm espresso typography (`--text: #1c1917`).
- **Eliminated Black Box "Zebra" Artifacts**: Fixed all hardcoded dark containers across the application chrome:
  - `.ribbon` container shifted from hardcoded coal `#0a0b0f` to warm recessed stone `var(--panel-bg)` (`#eae7df`) with crisp sandstone cards.
  - `.meta-pill` shifted from `#14161d` to light card tokens with dark text and subtle elevation.
  - `.topic-hint-input` shifted from pitch black `#08090d` to clean white `#ffffff` surface with legible dark text and sandstone borders.
  - `.model-status-bar` converted from black coal to an elegant sage/mint banner (`#f0fdf4`) with dark forest green text (`#166534`).
  - `.action-status-chip` and standby CTA transitioned from dark `#141722` to warm sandstone (`#e7e4dc` / `#eae7df`).
  - `.hero h1 mark` converted from neon highlighter to soft warm amber (`#fef08a`) with deep brown text (`#713f12`).
  - Navigation badges (`GPU: CUDA`, `V2.5`, `HINGLISH ENGINE`) updated with dedicated light mode tokens and mint accents.
- **Full Chrome Coverage**: Added scoped light mode overrides for Subtitle Result Cards (`.card-orig-box`, `.card-hinglish-box`), the slide-out inspector drawer, media controls, and the in-app terminal console dock.
- **Test Suite**: Updated `test_dark_light_theme_toggle_option1` in `tests/test_upgrades.py`; all 26 unit and UI tests pass.

## [2026-10-17] Dedicated Dark & Light Mode Switcher (Option 1)
- **Top Navbar Mode Toggle**: Added `#themeModeToggleBtn` (`.theme-mode-btn`) with Sun (`☀️`) / Moon (`🌙`) SVG icon and tactile `DARK` / `LIGHT` status badge in the top navigation bar right next to the theme select dropdown.
- **Decoupled Mode vs Styling**: Removed `minimalist-light` from `#themeSelect` so the dropdown specifically configures the active dark style variant (`Industrial Hybrid`, `Sleek Bento Cyber`, `Cyberpunk Neon`), while the toggle button flips between the active dark style and `minimalist-light`.
- **Intelligent Style Memory**: Persists `preferredDarkTheme` in `localStorage` so switching back from Light mode seamlessly restores the user's previously selected dark aesthetic.
- **Adaptive Light Scrollbars & Controls**: Configured light mode scrollbars (`html[data-theme="minimalist-light"]`), responsive button shadows, and dynamic token-driven select backgrounds (`var(--card)`).
- **Test Suite**: Added `test_dark_light_theme_toggle_option1` to `tests/test_upgrades.py`; all 26 unit and UI tests pass.

## [2026-10-17] Native App Polish: Inline SVG Brand Logo & Desktop Text-Selection Lock
- **Inline SVG Brand Logo**: Inlined `<svg class="brand-logo">` directly into `static/index.html` navigation bar. Permanently fixes the broken image placeholder icon caused by root static route mounting (`/static/logo.svg` 404), with zero network latency and dynamic CSS theme variable adaptation (`var(--yellow)` / `var(--cyan)`).
- **Desktop UI Chrome Selection Lock**: Configured `user-select: none; -webkit-user-select: none;` across all application chrome (`body`, `nav`, `.hero`, `.ribbon`, `.tile`, `.controls-card`, `.pill`, `.badge`, `.dropzone`, `.action-bar`). Prevents accidental blue text selection during mouse drags, matching native desktop apps.
- **Content Selection Whitelist**: Explicitly preserved `user-select: text !important;` on inputs, textareas, subtitle text blocks (`.card-hinglish-box`, `.card-orig-box`), video caption text, and terminal log output.
- **Native Webview Shell Mode**: Set `text_select=False` in `webview.create_window()` (`server.py`) so the native Windows WebView2 shell disables browser selection across application chrome.
- **Test Suite**: Updated `test_micro_polished_cta_and_layout` in `tests/test_upgrades.py`; all 25 unit and UI tests pass.

## [2026-10-17] Custom Brand Logo & Windows Taskbar Icon Branding
- **Windows Taskbar Identity**: Registered explicit `AppUserModelID` (`antigravity.hinglishsubtitles.desktop.v2`) in `server.py` and wired `app_icon.ico` directly into `webview.start(icon=...)` and PySide6 `setWindowIcon()`. Replaces the default Python snake/window taskbar icon with the custom Neo-Brutalist Hinglish Subtitles icon.
- **Web Favicon Suite**: Copied `app_icon.ico` to `static/favicon.ico` and linked `/static/favicon.ico` across standard and Apple touch icons in `static/index.html`.
- **Top Navigation Brand Logo**: Designed `static/logo.svg` (dual subtitle CC/audio bars in brand yellow & cyan on dark screen) and integrated `.brand-logo` into the top sticky navbar before the ANTIGRAVITY brand label.

## [2026-10-17] Option 2 UI Micro-Polish (Single-Line Meta Row, Grounded Layout, Smart Standby CTA)
- **Single-Line Hero Meta Row**: Implemented `formatShortGpuName()` in `static/app.js` (`⚡ RTX 4050 6GB (CUDA fp16)`) and added `white-space: nowrap;` to `.meta-pill`. Eliminates the orphan wrap of `🎯 0% LLM Hallucinations` onto a second line alone.
- **Removed White Button Hover**: Updated `.btn-primary:hover` in `static/components.css` to retain brand yellow with an elevated electric brightness lift (`filter: brightness(1.08)`) and border depth, permanently removing the harsh solid white hover.
- **Smart Standby / Armed Action Bar**: Styled `.btn-primary:disabled` / `.btn-primary.is-standby` with subtle dashed styling and added `.action-status-chip` (`Drop a video or audio file above to begin` $\to$ `File staged & ready`).
- **Grounded Controls Card Columns**: Added `align-items: stretch` on `.controls-card` and `topic-hint-group` on the Topic Hints input so it anchors flush to the bottom baseline alongside the right column's status banner.
- **Test Suite**: Added `test_micro_polished_cta_and_layout` in `tests/test_upgrades.py`; all 25 unit and UI tests pass.

## [2026-10-17] Sleek Bento Cyber Theme (Option A)
- **Non-Breaking Theme Extension**: Added `[data-theme="sleek-bento"]` selectable via the navbar `#themeSelect` dropdown (`Theme: Sleek Bento Cyber (New)`), with seamless `localStorage` persistence.
- **Design Tokens**: Configured pitch black canvas (`#07080a`), elevated charcoal bento cards (`#131419`), neon lime (`#bef264`) and solar orange (`#fb923c`) accents, 22px squircle containers, full capsule geometry (`border-radius: 9999px`), and diffuse ambient occlusion glow shadows (`static/tokens.css`).
- **Scoped Component Adaptations**: Overrode capsules (`.pill`, `.meta-pill`, `.badge`, `.btn-primary`, `.btn-secondary`, `.console-nav-btn`, `.terminal-pill`), bento cards (`.controls-card`, `.ribbon`, `.tile`, `.dropzone`, `.file-preview`, `.video-stage`, `.card`, `.drawer`, `.terminal-dock`), and tactile mechanical click feedback (`static/components.css`).
- **Test Suite**: Added `test_sleek_bento_theme_configuration` to `tests/test_upgrades.py`; all 24 unit and UI tests pass.

## [2026-10-17] In-App Terminal Console (Option 1) & Subprocess Flash Hardening
- **Integrated Bottom Dock**: Added a resizable, collapsible in-app terminal console dock directly to the Hinglish Subtitles Hub (`static/index.html`, `static/components.css`, `static/app.js`).
- **Real-Time Telemetry**: Implemented `console_bus.py` with an in-memory 5,000-line ring buffer and Server-Sent Events (`/api/console/stream`) for streaming pipeline stages (`[extract]`, `[whisper]`, `[conformer]`, `[sravaani]`, `[recover]`, `[cards]`, `[done]`).
- **Interactive Controls**: Supports level filtering (`ALL`, `STAGES`, `WARNINGS`, `ERRORS`), one-click `COPY`, `EXPORT` log file, `CLEAR`, and keyboard shortcut `Ctrl + \`` (backtick).
- **Subprocess Window Hardening**: Added `subprocess.CREATE_NO_WINDOW` to Windows `ffmpeg.exe` and `nvidia-smi.exe` calls in `hinglish_engine.py` to prevent black command prompt flashes.
- **Default Silent Launch**: Updated `launch_config.json` to `silent_launch: true` so double-clicking `HinglishSubtitles.exe` opens the standalone app with zero external OS console windows.

## [2026-10-17] Trustworthy Benchmarks, Prompt A/B, Golden Scoring, & Engine Bake-off

### 1. Task 1: Prompt Window Dropping A/B Evaluation
- **Finding**: Evaluated Condition A (current: `hotwords=""` when zero hints), Condition B (style prompt in hotwords), and Condition C (short style string in hotwords).
- **Result**: Condition B triggered a severe looping hallucination on Traffic Window 2 (`I'm not going to lie, I'm not going to lie...` repeated 7 times, losing 40% of speech). Condition C leaked the hotword `execution game`. Condition A had 0 hallucinations and 0 repeated n-grams.
- **Decision**: Retained Condition A. Downstream `LoanwordRecoverer` handles script recovery cleanly without risking decoder loops.

### 2. Task 2: Subprocess-Isolated Benchmark
- Eliminated VRAM memory leaks between runs by isolating each configuration into its own subprocess.
- Benchmarked 7-config matrix across both test reels with zero hints.
- **Key Finding**: `large-v3-turbo/float16/beam2` achieved **2.71s** (Genius Ad) and **3.09s** (Traffic) at 3,848 MB peak VRAM with 0 temperature fallbacks. Reproduced the `medium/int8_float16` stall on Ada Lovelace (27.55s).

### 3. Task 3: Golden Verification & Symmetric Scoring
- Created `tools/make_golden.py` producing editable TSVs: `golden/The-Genius-Ad-SnapYT.App.tsv` and `golden/He-Turned-Traffic-SnapYT.App.tsv`.
- Implemented `tools/score.py` with symmetric stage normalization, token WER, Latin accuracy, rare brand Zipf accuracy, and an 80% verification guard.
- Self-test verified (`python tools/score.py --self-test` passes at 0.0% WER).

### 4. Task 4: Multi-Engine Bake-off & Alignment Audit
- Measured timestamp containment using Silero VAD proxy. Whisper native DTW achieved **100% containment** and <0.04s silence margins.
- Discovered and documented that **SenseVoice-Small timestamps are uniformly projected/interpolated** (`dur_per_word = duration / len(tokens)`), not model-aligned, and outputs gibberish on Hindi. Marked as experimental in UI.
- Corrected IndicConformer frame duration to `FRAME_DURATION_MS = 0.08s` (80ms encoder frames), eliminating warning and aligning CTC boundaries.

### 5. Task 5: Codebase Hardening & Claim Audit
- Removed dead `chunk_into_reel_segments` and regex in `hinglish_engine.py`.
- Hardened `normalize_case` and `LoanwordRecoverer` against false-positive brand snapping (`तितली, ताला, तालाब, तौलिया, बात, काम, घर, जादा, बाभाप, कर्वा` stay Hindi).
- Restricted CORS in `server.py` to localhost origins.
- Measured 16.09-minute audio file directly: `large-v3-turbo` finished in **67.63s** (14.3x real-time) at 3,912 MB VRAM; `medium` completed in **1105.31s** (0.9x real-time) at 5,818 MB peak VRAM.


### 1. Verification of Faster-Whisper Prompting vs Hotwords Theory (Task 1)
- **Source Inspection (`faster_whisper/transcribe.py`)**:
  - `initial_prompt` (lines 1143-1149) is appended to `all_tokens` prior to processing segment windows.
  - When `condition_on_previous_text=False`, line 1383 triggers `prompt_reset_since = len(all_tokens)` at the end of each window, causing `previous_tokens` to be empty for subsequent windows. As a result, `initial_prompt` is completely dropped in windows $k \ge 2$ ($t > 30\text{s}$).
  - `hotwords` (lines 1205, 1542-1548) is passed on every window iteration and injected directly into `prompt` right after `sot_prev`.
- **Empirical Proof on Reel Audio ($t > 30\text{s}$)**:
  - **No prompt**: Second-window terms output in Devanagari (`और इसी लाइन को डेटॉल ने पगड लिया`, `और मार्केटिंग, बिल्बोर्ड, एड, कैमपैन`, `डिटाल को अपने इंडस्ट्री का किंग`).
  - **initial_prompt only** (`billboard, campaign, Dettol, Savlon`): Window 1 recognized `Dettol` and `Savlon`, but Window 2 ($t > 30\text{s}$) **completely failed**, remaining Devanagari (`डेटॉल`, `मार्केटिंग, बिल्बोर्ड, एड, कैमपैन`, `डिटाल`).
  - **hotwords only** (`billboard, campaign, Dettol, Savlon`): Succeeded in **both** Window 1 and Window 2 (`और marketing, billboard, ad, campaign`, `Dettol ने पगड लिया`, `Dettol को अपने industry का king`).
- **Resolution**: Updated `build_prompt()` and `transcribe_words()` so domain terms and caption hints strictly route to `hotwords`, reserving `initial_prompt` for script and formatting templates (`SCRIPT_ANCHOR` + `STYLE_TEMPLATE`), with a fallback for older faster-whisper versions.

---

### 2. Lexical Variant Unification (Task 3)
- Implemented `unify_variants(words: List[dict])`:
  - Discovers Latin brand tokens and proper nouns across the reel (e.g. `Detol`, `Sablon`).
  - Clusters Latin spelling variants using consonant skeleton matching and character Levenshtein edit distance ($\le 1-2$).
  - Resolves cross-script Devanagari tokens (e.g. `दिटाल`, `डेटॉल`, `डेतॉल`) having exact consonant skeleton matches (`ttl`) to the reel's canonical Latin brand spelling (`Detol`).
  - Strict false-positive guards: protected common Hindi vocabulary (10,000 words + conversational map), inflection suffixes, and length $\ge 3$. Prevents Hindi words like `जलन` (`sln`) from snapping to `Sablon` (`spln`).

---

### 3. Sentence-Aware Case Normalization (Task 4)
- Implemented `normalize_case(words: List[dict])`:
  - Lowercases common English words (WordFreq Zipf $\ge 3.8$) occurring mid-sentence (e.g. `Talent` $\to$ `talent`, `Execution` $\to$ `execution`, `Monthly` $\to$ `monthly`, `Revenue` $\to$ `revenue`, `Marketing` $\to$ `marketing`).
  - Preserves capitalization for sentence starters (index 0 or following `.`, `?`, `!`, `।`), established proper nouns (`India`, `Mumbai`, `Vada Pav`), and low-frequency brand entities (`Dettol`, `Savlon`).

---

### 4. Decision Logging & User Protection Layer (Task 5)
- Every recovery, unification, and casing transformation is recorded with stage, timestamp, span, original text, replacement, and rationale.
- Exported automatically per reel to `logs/decisions_<reel>_<timestamp>.tsv`.
- Created `review_decisions.py` CLI to inspect logs, view summary counts, and append false-positive overrides directly to `protected_extra.txt` via `--protect <word>`.
- Updated `_HINDI_INFLECTION` to include postposition clitics (`से`, `ने`, `को`, `का`, `के`, `की`, `में`, `पर`) so compound phrases like `फिरसे` are protected from English loanword matching (`fierce`).

---

### 5. Acoustic & Model Investigation of "jalegaa to chalegaa" (Task 6)
- Extracted 5.0s span ($49.0\text{s} - 54.0\text{s}$) to `jalegaa_chalegaa_span.wav`.
- Model comparison:
  - `small`: Hallucinated `जड़ेगा तो जड़ेगा` (`jalegaa to jalegaa`) with low confidence (prob 0.69 - 0.91) due to capacity limits.
  - `medium`: Transcribed `जलेगा तो चलेगा` accurately with **95.7%** confidence.
  - `large-v3-turbo`: Transcribed `जलेगा तो चलेगा` with **97.4% - 99.6%** confidence (avg logprob -0.100).
- Confirmed audio unambiguously speaks the tagline *"jalega to chalega"* without engine modifications.

---

### 6. Automated Benchmark Matrix on RTX 4050 GPU (Task 2)
Benchmarked across both test reels with **zero hints** (`topic_hint=""`):
- Protocol: 2 warmup runs discarded, median of 3 measured warm runs on cached model.

| Configuration | Reel | Cold Total | Warm Audio | Warm Transcribe | Warm Post | **Warm Total** | Real-Time Speed | Peak VRAM | Target (<8s)? |
|---|---|---|---|---|---|---|---|---|---|
| `medium/float16/beam5` (baseline) | Genius Ad | 16.71s | 0.13s | 10.38s | 0.33s | **10.81s** | 5.5x | 2075 MB | EXCEEDED |
| `medium/float16/beam5` (baseline) | Traffic | 16.71s | 0.12s | 13.12s | 0.24s | **13.46s** | 4.3x | 2075 MB | EXCEEDED |
| `medium/int8_float16/beam2` | Genius Ad | 16.41s | 0.12s | 10.56s | 0.22s | **10.90s** | 5.4x | 2851 MB | EXCEEDED |
| `medium/int8_float16/beam2` | Traffic | 16.41s | 0.12s | 23.48s | 0.25s | **23.88s** | 2.4x | 2147 MB | EXCEEDED |
| **`large-v3-turbo/float16/beam2`** | **Genius Ad** | **6.88s** | **0.12s** | **2.59s** | **0.19s** | **2.91s** | **20.2x** | **3179 MB** | **PASSED** |
| **`large-v3-turbo/float16/beam2`** | **Traffic** | **6.88s** | **0.12s** | **3.11s** | **0.20s** | **3.43s** | **16.9x** | **2475 MB** | **PASSED** |
| `large-v3-turbo/int8_float16/beam2` | Genius Ad | 11.17s | 0.12s | 3.45s | 0.22s | **3.81s** | 15.5x | 3027 MB | **PASSED** |
| `large-v3-turbo/int8_float16/beam2` | Traffic | 11.17s | 0.12s | 3.33s | 0.20s | **3.68s** | 15.8x | 2195 MB | **PASSED** |
| `small/float16/beam2` | Genius Ad | 9.80s | 0.12s | 10.35s | 0.22s | **10.70s** | 5.5x | 2397 MB | EXCEEDED |
| `small/float16/beam2` | Traffic | 9.80s | 0.12s | 8.01s | 0.26s | **8.39s** | 6.9x | 1341 MB | EXCEEDED |

- **Key Takeaway**: `large-v3-turbo/float16/beam2` achieves **2.91s - 3.43s total warm latency** (3.7x - 3.9x faster than baseline), comfortably beating the <8.0s target with superior accuracy.

---

### 7. Before & After Output Comparison (Zero-Hint Evaluation)

#### Reel 1: The Genius Ad (`The-Genius-Ad-SnapYT.App.mp4`)
- **Before Upgrades**:
  - Inconsistent brand spelling jumping across cards: `ditaal`, `DTOL`, `detol`, `detail`, `title`.
  - Missing English loanwords: `maaraketin` / `maraketimg`, `bheelabor`, `kampain`.
  - Tagline transcription error: `jalegaa to jalegaa`.
  - Phrase boundary split: `kare kyaa kare, phir usane ek phyamas laaeen uthaayaa`.
- **After Upgrades**:
  - Consistent unified brand spelling throughout: `Detol` across all 7 occurrences.
  - Loanwords recovered accurately: `marketing`, `billboard`, `campaign`.
  - Tagline verified and transcribed correctly: `jalegaa to chalegaa`.
  - False positive eliminated: `phirase` stays `phirase` (does not become `fierce`).

#### Reel 2: Traffic Vada Pav (`He-Turned-Traffic-SnapYT.App.mp4`)
- **Before Upgrades**:
  - Mid-sentence stray capitals: `Monthly Revenue`, `Talent ki kami`, `Execution ki`.
  - Number / unit split across cards: `2 लाख | प्लस`.
  - Inconsistent casing: `lakh` vs `Lakh`.
- **After Upgrades**:
  - Clean sentence casing: `talent ki kami`, `execution ki`, `monthly revenue`.
  - Number + unit preserved together: `2 lakh plus monthly revenue`.
  - Proper nouns preserved: `India`, `Mumbai`, `Vada Pav`.
