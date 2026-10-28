# Project Memory & Long-Term Context

> **Workspace:** `c:\Users\susha\Documents\General` & `c:\Users\susha\Documents\General\hinglish_subtitles`  
> **Last Updated:** 2026-10-22
> **Purpose:** Persistent cross-session knowledge base tracking architectural decisions, user preferences, hardware configuration, and project evolution.

---

## 1. User Preferences & Global Rules

- **Interaction Style:** Ponytail mode (lazy senior dev: minimal new code, no boilerplate, zero over-engineering, honest risk and skipped-item summary).
- **Conversational Modes:**
  - `[ask]` / `[chat]`: Pure discussion mode. Never edit files or run modifying commands.
  - `[discuss]` / `[review]`: Design evaluation and trade-offs before touching files.
  - `[plan]`: Create an implementation plan artifact and wait for approval before editing code.
  - `[code]` / `[apply]`: Direct execution mode.
- **Design Aesthetic:** 
  - **Independent Resizable Subtitle Studio Window Panel**:
    - The Subtitle Editor is mounted as a persistent, dedicated left window panel (`position: fixed; top: 54px; left: 0; bottom: var(--dock-height, 76px); width: var(--editor-width, 420px); height: auto; max-height: calc(100vh - 54px - var(--dock-height, 76px))`), stopping cleanly above the bottom action dock with 0px overlap across all screen sizes.
    - Features its own independent scroll container (`.subtitle-editor-body` and `.editor-inspector-scroll`), completely isolated from the main window. Scrolling over the media stage, video player, or subtitle cards does not scroll or affect the editor panel.
    - Draggable splitter handle (`#editorResizer` / `.editor-resizer`) stays perfectly aligned at `left: var(--editor-width, 420px)`, dynamically resizing between `320px` and `800px`, persisting user preference in `localStorage.getItem("subtitle_editor_width")`. Hidden on touch/mobile screens (`<= 900px`).
    - Collapsible into a slim 58px rail (`#editorRail`) via the `<` / `>` toggle button (`#editorCollapseBtn` and `#editorExpandBtn`) or the <kbd>Esc</kbd> key. Defaults to collapsed on mobile viewports (`<= 900px`) so media player and cards are immediately visible.
    - Captions & styles are completely and exclusively integrated into the Left Subtitle Editor's **`STYLE`** tab (presets including the **"123 Honey Punch"** kinetic style from `123effect`, live video player styling, font selection, sizes, colors, outlines, box toggles, and JSON import/export). Section 3c Caption Style was removed from the Settings drawer.
    - **Studio Workspace Layout (Option 1 + 3 Architecture)**:
      - When subtitles generate and `body.editor-open` is active, the marketing Hero (`<h1>Hinglish subtitles</h1>`) and initial Controls Card automatically collapse into a sleek 36px **Studio Breadcrumb Bar** (`#studioBreadcrumbBar`) above the media player displaying: `ðŸŽ¬ [Filename]`, `[Language Mode]`, `[Model â€¢ N Segments]`, and an interactive `[âš™ï¸ SETUP / RE-RUN]` toggle button.
      - Clicking `[âš™ï¸ SETUP / RE-RUN]` toggles `body.setup-expanded`, sliding the language ribbon and Whisper model cards smoothly into view whenever needed without refreshing or losing place.
      - The main stage (`.workspace-shell`) has physical `margin-left: var(--editor-width, 420px); width: calc(100vw - var(--editor-width, 420px));` (and `58px` when collapsed to rail) down to 900px, completely preventing cards from sliding under the editor panel.
      - **2-Column Grid at 1280px**: Results `.grid` uses `grid-template-columns: repeat(auto-fill, minmax(min(350px, 100%), 1fr))` ensuring the Video Player and Subtitle Cards fit side-by-side in 2 clean columns on standard 1280px screens.
      - **Live Video Caption Styling Engine**: Caption style presets (*Hormozi Kinetic*, *Vox Clean*, *Cyber Lime*, *Blackout Box*, etc.) and custom parameters (font, size, color, outline text-shadow, uppercase, box) directly drive the live on-video subtitle overlay on the video player in real time. The old toy preview card (`#editorStyleSample`) has been removed from the DOM and JS source.
      - **Clean Bottom Action Dock**: The bottom fixed dock is now a crisp, uncluttered toolbar: the left cluster contains the segment match count badge and keyboard-accessible search bar, while the right cluster hosts export actions (`COPY ALL`, `DOWNLOAD HINGLISH SRT`, `KARAOKE .ASS`, `BURN VIDEO .MP4`, `ORIGINAL SRT`, `PLAIN TEXT`) with horizontal scroll (`scrollbar-width: none`). The row starts from its first action when space is tight, so the primary download is visible immediately and every action remains reachable by scrolling.
      - **Mobile Viewport Restraint**: Navbar hides verbose GPU badges and text labels on screens `<= 540px`, and `html, body` enforce `max-width: 100vw; overflow-x: hidden`, eliminating horizontal overflow on 390px mobile viewports.
  - **Industrial Hybrid (Default)**: Industrial Neo-Brutalist design language (matching `skills_library.html` tokens: strict 0px border-radius, 2px solid borders, `#000000` / `#ffffff` hard drop shadows, `#facc15` brand yellow, `#38bdf8` cyan accents, dark `#0c0d10` canvas).
  - **Sleek Bento Cyber (`[data-theme="sleek-bento"]`)**: Smooth squircle bento cards (`22px` radius), full capsule geometry (`border-radius: 9999px`), pitch black `#07080a` canvas with elevated charcoal `#131419` cards, vivid neon lime (`#bef264`) and solar orange (`#fb923c`) accents, soft ambient occlusion glow shadows, and preserved tactile press physics. Switchable in top navbar and persisted in `localStorage`.
  - **CTA & Hover Integrity**: The primary execution button (`.btn-primary`) must NEVER turn pure white on hover; it retains its signature brand yellow with a subtle electric brightness lift (`filter: brightness(1.08)`). In empty state, it remains in a dimmed standby state (`.is-standby`) with a status chip until media is staged.
  - **Hero Meta Row & Grounded Baseline**: The duplicate hero hardware pill was removed (the top sticky navbar's compact GPU pill already displays the active GPU and CUDA fp16 status), leaving the hero meta row clean with model info and zero-hallucinations. Controls card columns stretch with `align-items: stretch` and `topic-hint-group` to ground the left column flush with the right banner.
  - **Branding & Taskbar Identity**: Windows taskbar icon is set via explicit `AppUserModelID` (`antigravity.hinglishsubtitles.desktop.v2`) and `app_icon.ico` passed to `webview.start` / PySide6 `setWindowIcon()`. Web UI includes `favicon.ico` and a custom inline `.brand-logo` (`<svg class="brand-logo">`) in the top sticky navigation bar that dynamically inherits theme accents.
  - **Desktop Application Selection Ergonomics**: Chrome elements (`body`, `nav`, `.hero`, `.ribbon`, `.tile`, `.controls-card`, `.pill`, `.badge`, `.dropzone`, `.action-bar`) lock `user-select: none;` and `server.py` sets `text_select=False` to prevent browser drag-highlighting. Content areas (`input`, `textarea`, `.card-hinglish-box`, `.card-orig-box`, `.caption-text`, `.log-line`) strictly retain `user-select: text !important;`.
  - **Tile & Icon Glyph Shadow Polarity**: The outer language tile cards (`.tile`, `.tile.active`, `.tile:hover`, `.tile:active`) strictly retain hard offset drop shadows matching their respective icon accent color (`var(--c, var(--yellow))` / `var(--c, var(--paper))`). The inner icon glyph badge (`.glyph`, `.tile:hover .glyph`, `.tile.active .glyph`) carries a crisp, pure white `#ffffff` drop shadow in dark modes (`box-shadow: 3px 3px 0 #ffffff;`, `1px 1px 0 #ffffff` when hovered/active) and pure black `#000000` drop shadow in light mode (`box-shadow: 3px 3px 0 #000000;`, `1px 1px 0 #000000` when hovered/active), providing high-contrast punch to the icons while keeping card shadows harmonized with their category colors.
  - **Subtitle Export & Download Pipeline**: In standalone desktop window mode, pywebview runs with `webview.settings["ALLOW_DOWNLOADS"] = True` and binds a `DesktopAPI` (`window.pywebview.api.save_subtitle_file`) that launches the native Windows OS "Save As" file dialog (`webview.FileDialog.SAVE`) directly saving UTF-8 subtitle/text files. In browser mode, falls back to `POST /api/download/file` with `Content-Disposition: attachment` or delayed client-side Blob revocation (60s) to prevent WebView2/Chromium stream aborts. Floating download bar has `z-index: 95;` and provides dynamic `âœ“ SAVED!` button feedback.
  - **Karaoke Animated Subtitles (.ASS) & Word Timestamps (Phase 1)**: Integrated word-level animated subtitles. `karaoke_ass.py` outputs Advanced SubStation Alpha (`.ass` v4.00+) with `{\k<centiseconds>}` highlight tags for active words (Alex Hormozi / TikTok style with yellow fill `#FFC700`, black outline, and bottom safe zone margins). Engine endpoints (`generate_subtitles`, `generate_english_subtitles`, and `/api/export/ass`) attach individual word token timestamps `[{start, end, word, hinglish}]` to every segment, enabling both direct `.ass` karaoke exports and structured word timelines. Supported in the floating export bar via `ðŸŽ¤ KARAOKE (.ASS)` download action.
  - **Direct Video Burning Engine (Phase 2)**: Added high-speed local subtitle burn-in via FFmpeg (`video_burner.py`). Automatically utilizes Windows MediaFoundation H.264 hardware encoding (`h264_mf`) and libass filter with working directory path isolation to eliminate Windows colon/backslash path parsing issues. Exposes `POST /api/export/burn-video` and direct `ðŸ”¥ BURN VIDEO (.MP4)` button in the floating export bar, producing ready-to-publish MP4 videos with permanently burned styled subtitles.
  - **Speaker Diarization Engine (Phase 3)**: Lightweight acoustic turn and multi-speaker diarizer (`diarization.py`) using 28-dimensional spectral features (13 MFCCs + spectral centroid mean & variance) with distance-thresholded Agglomerative Hierarchical Clustering. Requires 0 external downloads or Hugging Face tokens. Seamlessly integrates into `hinglish_engine.py`, `hindi_to_english_engine.py`, `server.py`, and the web UI with a toggle in the Settings Drawer and dynamic `#Speaker N` badges on subtitle cards.
  - **Top Navigation Bar & Floating Bottom Search Dock**: Top bar follows a clean 2-zone workbench layout (Brand identity with monospace `v2.5` badge on the left; compact single-line GPU pill, live terminal button, and unified segmented theme cluster on the right). Subtitle search is contextually consolidated into the center of the fixed bottom floating export dock (`#floatingSearchInput`), eliminating duplicate top and toolbar search inputs, and focused automatically via global <kbd>/</kbd> hotkey. The bottom bar includes a real-time subtitle match telemetry pill (`#floatingMatchPill` displaying `ðŸŽ¯ X / Y MATCHES`) and an instant `ðŸ“‹ COPY ALL` clipboard button (`#floatingCopyAllBtn`).
  - **Empty State Workbench (Pattern B: 2-Column Split Cockpit)**: Positioned below `.action-bar` to eliminate empty screen space before a file is loaded. Features a Web Video Link Importer powered by `yt-dlp` (`POST /api/import-url` and `/api/media/{filename}`) for YouTube, Instagram Reels, TikTok, and direct links, alongside a Recent Transcriptions & 1-Click Benchmark Reel shelf (`static/samples/traffic.mp4` and `genius_ad.mp4`). Both columns feature individual `âœ• HIDE` buttons and persistent restore chips (`#workbenchRestoreBar`) allowing users to hide whichever feature they don't need while retaining a balanced responsive layout.
    - **Web Video Importer Media & Quality Controls (Option 1)**: Integrated two-tier Segmented Media Switcher (`ðŸŽ¬ Video + Audio` vs `ðŸŽµ Audio Only (Fastest âš¡)`) paired with dynamic Quality Dropdown (Video: `Source Best`, `720p Fast HD`, `480p`; Audio: `320k High`, `128k Standard`, `64k Speech/Fast`). Audio-only downloads download in ~2s and automatically activate the frontend Web Audio frequency visualizer (`renderAudioVisualizer()`). User selections persist across sessions in `localStorage`.
  - **Spoken Language Ribbon (5-Tile Architecture with Hindi âž” English)**: Expanded `.ribbon` to 5 columns (`grid-template-columns: repeat(5, 1fr)`). Added 5th tile for **Hindi âž” English** (`data-lang="hi-en"`, Solar Orange `--orange: #fb923c`, translation icon `æ–‡ âž” A`). Directly triggers Whisper's native GPU `task="translate"` (with `language="hi"`), translating spoken Hindi audio into natural English captions with exact millisecond word timestamps at 14xâ€“18x real-time speed on the RTX 4050 GPU. Downstream DP chunker chunks the English words into 1â€“2 line subtitle cards; UI updates card badges to `TRANSLATED ENGLISH` and export buttons to `DOWNLOAD ENGLISH SRT`. Selection is persisted across sessions in `launch_config.json`.
    - **Hero Layout & Tile Width Optimization**: Rebalanced the `.hero` container grid from `1.2fr 1fr` to `minmax(360px, 440px) 1fr`, giving the right-side ribbon over 850px+ of width (~155px per tile) and preventing tile cramming. Added `white-space: nowrap;` to `.tile` titles and descriptions, keeping labels on a single line with generous breathing room. Added `@media (max-width: 1120px)` breakpoint to stack gracefully without squeezing on compact screens.
  - **Slide-Over Settings Drawer (Option 1 Architecture)**: Secondary engine controls (Whisper/ASR model pills, CUDA vs CPU acceleration selectors, caption pacing profiles, and topic/brand vocabulary hotwords) have been relocated out of the main page flow into a slide-over inspector drawer (`#settingsDrawer`).
    - **Trigger**: Click `âš™ï¸ SETTINGS` button (`#openSettingsBtn`) in top navbar, click the active GPU badge (`#hwBadge`), or press the global <kbd>,</kbd> (comma) hotkey.
    - **Dismiss**: Press <kbd>Esc</kbd>, click `#settingsDrawerCloseBtn`, click the blurred backdrop overlay (`#settingsDrawerOverlay`), or click `#saveAndCloseSettingsBtn`.
    - **Clean Main Canvas**: Eliminates ~300px of vertical clutter between the hero ribbon and upload dropzone. The landing screen flows directly: Top Navbar âž” Spoken Language Ribbon âž” Upload Dropzone / Cockpit!
    - **Ergonomics**: Media player and subtitle grid remain 100% visible in the background when configuring settings, allowing rapid iterative adjustments.
    - **Dynamic Pinned Controls & Permanent Main Window Topic Hints**:
      - **Topic / Brand Vocabulary Hints** is kept permanently in the main window directly above the dropzone so creators can type hotwords and brand names without opening settings; completely removed from the Settings Drawer.
      - Each major setting in the Settings Drawer (ASR Model Switcher, Hardware Acceleration, Caption Pacing, Caption Style, and Speaker Diarization) includes a dedicated `[ ðŸ“Œ PIN TO MAIN ]` switch (`#pinModelSwitch`, `#pinHwSwitch`, `#pinPacingSwitch`, `#pinStyleSwitch`, `#pinDiarizeSwitch`).
      - Pinned controls render in the main window using the familiar **previous design layout** (`.controls-wrap` with `.controls-card` between the Language Ribbon and the Dropzone).
      - **Dynamic Layout Adaptation**:
        - **0 Pinned**: Main controls card renders as a sleek, full-width Topic Hints card (`.controls-card.cols-1`).
        - **Model Switcher Pinned**: Forms the exact previous 2-column layout (`.controls-card.cols-2`) with Topic Hints on the left and Model Switcher on the right.
        - **All Pinned**: Left column has Hardware + Pacing + Topic Hints; Right column has Model Switcher (exact original layout!).
      - **Bidirectional Synchronization**: Pill selections and cache/download statuses sync in real-time between the drawer and main window cards.
    - **Workbench Modules Visibility in Settings Drawer (Section 4)**:
      - Main window cards (`#workbenchImporterCard` and `#workbenchRecentsCard`) remain 100% clean with zero clutter buttons on their headers.
      - In the Settings Drawer, dedicated `[ SHOW ]` and `[ âœ• HIDE ]` toggle buttons allow hiding or showing either the Web Video Importer (`#settingsShowImporterBtn`, `#settingsHideImporterBtn`) or Recent Files & Samples (`#settingsShowRecentsBtn`, `#settingsHideRecentsBtn`).
      - When one module is hidden, the remaining module expands to 100% full width (`.full-width`). When both are hidden, the empty-state workbench collapses cleanly. Preferences persist across sessions in `localStorage`.
- **Proactive HTML Visualizations Directive:** Whenever discussing, designing, or altering any UI layouts or components, the agent must **always proactively create an interactive standalone HTML visualization file** (e.g. `c:\Users\susha\Documents\General\<name>_options.html`) with light/dark themes, clickable tabs/options, and side-by-side previews without waiting for the user to ask. Interactive prototype created: [`topic_hints_and_settings_visibility_options.html`](file:///c:/Users/susha/Documents/General/topic_hints_and_settings_visibility_options.html).
- **Sync Protocol:** Whenever skills in `C:\Users\susha\.gemini\config\skills` are changed, automatically run `python C:\Users\susha\Documents\General\sync_skills_library.py`.

---

## 2. Hardware Environment & Verified Telemetry

- **Primary GPU:** NVIDIA GeForce RTX 4050 Laptop GPU (6,141 MiB VRAM).
- **Acceleration Stack:** CUDA `float16` via `faster-whisper` (CTranslate2).
- **Measured Speeds & VRAM (Measured 2026-10-17)**:
  - `large-v3-turbo/float16/beam5`: **3.2sâ€“4.1s** (Genius Ad & Traffic). Real-time factor: **14xâ€“18x**. Peak VRAM: **3,850 MB**. Beam size 5 completely eliminates word freezes on fast speech over background music without increasing VRAM over beam 2.
  - `large-v3-turbo` on 16.09-minute file: **67.63s** total transcribe (14.3x real-time), **3,912 MB peak VRAM**.
  - `medium/float16/beam2`: 10.12s (Genius Ad), 11.11s (Traffic). Peak VRAM: 2,752 MB.
  - `medium/float16` on 16.09-minute file: **1,105.31s** (0.9x real-time) with 5,818 MB peak VRAM.
  - `medium/int8_float16`: **27.55s** on Traffic reel due to Ada Lovelace dequantization overhead.
  - Non-Whisper engines (IndicConformer ONNX, SraVaani TorchScript, SenseVoice FunASR) execute on CPU (`torch 2.7.0+cpu`).
- **Prompt & Beam Search Strategy**:
  - `beam_size = 5`: Default beam width for Whisper inference. At `beam_size = 2`, `large-v3` and `large-v3-turbo` suffered from premature beam pruning during energetic Hindi speech mixed with background music, cutting off tokens and outputting single-syllable stalls (e.g. `GA`, `BA`).
  - Word-level clamping (`w_end - w_start > 2.5s` clamped) and card-level hard ceilings (`pad_display_times` clamped to `max_dur` <= 2.8s short / 5.0s long) prevent DTW cross-attention or chunk padding from freezing subtitles across silence/music.
  - Retain `hotwords=""` when no caption hints are provided. Injecting style text into hotwords caused severe repeating hallucinations (e.g. Traffic Window 2). Loanword script recovery is handled downstream by `LoanwordRecoverer`.

---

## 3. Hinglish Subtitle Generator System Architecture

### Core Pipeline
```
[Video / Audio File] (.mp4, .mov, .mkv, .webm, .avi, .mp3, .wav, .m4a, .flac, .ogg)
       â”‚
       â–¼
[FFmpeg Audio Extraction] (extract_audio_numpy: 16kHz mono float32 PCM via pipe, CREATE_NO_WINDOW)
       â”‚  â””â”€â”€ emits [extract] telemetry to console_bus
       â–¼
[Faster-Whisper Engine / Multi-ASR Pipeline]
       â”‚  â””â”€â”€ emits [whisper], [conformer], [sravaani] telemetry to console_bus
  â”œâ”€â”€ condition_on_previous_text=False (eliminates cascading repetition/hallucination loops)
  â”œâ”€â”€ vad_filter=True (Silero VAD threshold 400ms: prevents cutting mid-word)
  â”œâ”€â”€ initial_prompt: SCRIPT_ANCHOR + STYLE_TEMPLATE (Devanagari format anchor)
  â””â”€â”€ hotwords: User topic hints + brands injected into every 30s window
       â”‚
       â–¼
[Flat Word-Level Timestamps] (word_timestamps=True)
       â”‚
       â–¼
[Cross-Window Word Seam Stitching] (stitches 'reve' + 'nu' across 30s boundaries)
       â”‚
       â–¼
[Global Unification & Cleaning]
  â”œâ”€â”€ unify_variants(): Clusters phonetic spelling variants (e.g. 'Detol' -> 'Dettol')
  â”œâ”€â”€ LoanwordRecoverer: CMUdict + phonetic map recovers loanwords (e.g. 'à¤µà¥€à¤¡à¤¿à¤¯à¥‹' -> 'video')
  â””â”€â”€ normalize_case(): Rule-based casing (proper nouns preserved, mid-sentence common words lowercased)
       â”‚
       â–¼
[Semantic DP Chunker] (semantic_chunk() + pad_display_times())
  â”œâ”€â”€ Short-Form Mode (Reels/Shorts): 1.0sâ€“2.8s, 3â€“7 words, max 42 chars (prevents face blockage)
  â””â”€â”€ Long-Form Mode (YouTube/16:9): 2.0sâ€“5.0s, 8â€“14 words, max 76 chars (natural sentence clauses)
       â”‚
       â–¼
[Phonetic Transliteration] (Aksharamukha Devanagari -> Latin Hinglish)
       â”‚
       â–¼
[Subtitles & Real-Time Sync] (SRT, VTT, TXT, Card Grid + On-Video Reel Overlay)
```

---

## 4. Key Components & Implementation Details

| Component | File | Responsibilities |
|---|---|---|
| **FastAPI Backend** | [`server.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/server.py) | Endpoints: `/api/hardware`, `/api/models`, `/api/download_model`, `/api/transcribe` (supports `video`, `language`, `model_size`, `device`, `topic_hint`, `pacing`). Serves `/static`. |
| **Pipeline Core** | [`hinglish_engine.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/hinglish_engine.py) | `generate_subtitles()`, `extract_audio_numpy()`, hardware probe, SRT formatter. |
| **Translation Engine** | [`hindi_to_english_engine.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/hindi_to_english_engine.py) | Dedicated Hindi âž” English translation engine (`generate_english_subtitles()`). Pure English prompt, no transliteration or loanword pollution. |
| **Upgrade Engine** | [`hinglish_upgrades.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/hinglish_upgrades.py) | Dynamic programming chunker (`semantic_chunk`), variant clustering (`unify_variants`), casing normalizer (`normalize_case`), loanword recoverer. |
| **Transliteration** | [`transliteration.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/transliteration.py) | Aksharamukha Devanagari to Latin transliteration with English loanword whitelist. |
| **Web UI Template** | [`static/index.html`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/static/index.html) | Neo-Brutalist dashboard: language ribbon, hardware & pacing pills, drag-and-drop dropzone, adaptive video/audio stage, live caption overlay, subtitle inspector drawer. |
| **Component Styles** | [`static/components.css`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/static/components.css) | Adaptive viewer (`.video-portrait`, `.video-landscape`, `.media-audio`), animated equalizer bars (`.audio-equalizer-bars`), on-video reel caption overlay (`.video-caption-overlay`). |
| **Client Controller** | [`static/app.js`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/static/app.js) | Drag-and-drop handler, orientation & media detector, live timestamp caption sync engine (`timeupdate`), caption mode switcher (`HINGLISH`/`ORIGINAL`/`OFF`), live drawer sync. |
| **Launcher** | [`run_app.bat`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/run_app.bat) | Starts standalone window (`python server.py`). |

---

## 5. Recent Feature Additions & Bug Fixes

1. **Aspect-Ratio Adaptive Video Viewer**:
   - Replaced static `width: 100%; max-height: 380px;` with content-aware sizing.
   - 9:16 vertical reels scale up to `height: min(600px, 72vh)` with zero black letterbox wings.
   - 16:9 widescreen centers as a clean 860px max-width theater window.
2. **On-Video Reel-Style Live Captions**:
   - High-contrast yellow/white lower-third overlay (`pointer-events: none`).
   - Syncs to `videoPlayer.currentTime` and hides during pauses.
   - Interactive pill switcher: `[HINGLISH]`, `[ORIGINAL]`, or `[OFF]`.
   - Editing any text in the inspector drawer updates the on-screen caption immediately.
3. **Universal Audio Format Support**:
   - Added native support for MP3, WAV, M4A, AAC, FLAC, OGG, OPUS, and WMA.
   - Dedicated Audio Mode card (680px Ã— 200px) with animated `#facc15` equalizer visualizer.
   - Captions sync over the audio card in real time during playback.
4. **Caption Pacing & Format Selector**:
   - `ðŸ“± SHORT-FORM (REELS / SHORTS)`: 1.0sâ€“2.8s card duration, 3â€“7 words, max 42 chars.
   - `ðŸ“º LONG-FORM (YOUTUBE / 16:9)`: 2.0sâ€“5.0s card duration, 8â€“14 words, max 76 chars.
5. **Long Audio Reliability & UX**:
   - Progress bar features a live elapsed seconds ticker so users know GPU is active on 10â€“20 minute files.
6. **Custom Neo-Brutalist Media Controls Dock**:
   - Replaced default browser Chromium media player widget with a bespoke industrial dock docked seamlessly inside `.video-stage`:
     - Play/pause button in iconic `#facc15` yellow face with crisp white drop shadow (`box-shadow: 2px 2px 0 #ffffff`) and stage click-to-toggle.
     - JetBrains Mono timestamp display (`00:05 / 16:05` or `hh:mm:ss`) with active digits in `#facc15` yellow.
     - Interactive scrubber range slider with yellow playhead thumb (`#facc15`) casting a crisp white drop shadow (`box-shadow: 1px 1px 0 #ffffff`) and filled progress in yellow.
     - Volume mute toggle and slider.
     - Fullscreen toggle on `.video-stage` keeping captions and controls visible in fullscreen.
7. **Icon-Matched Glyph Shadows & Tile Coordination**:
   - Replaced generic white shadows on `.glyph` with each tile's distinct accent color (`box-shadow: 3px 3px 0 var(--c)`):
     - Mixed Hinglish: `#facc15` (Neon Yellow)
     - Pure Hindi: `#38bdf8` (Cyan)
     - English: `#4ade80` (Emerald Green)
     - Auto-Detect: `#c084fc` (Purple)
   - `.tile.active` coordinates with `border-color: var(--c)` and `box-shadow: 4px 4px 0 var(--c)`.
8. **Stepped Digital Sound Wave Equalizer (Sample 3)**:
   - Upgraded `#audioTrackBanner` with `#audioVisualizerCanvas` rendering 32 columns of segmented discrete LED blocks:
     - Low frequencies in neon yellow (`#facc15`), mid frequencies in cyan (`#38bdf8`), peak registers in green (`#4ade80`).
     - Driven by real-time Web Audio API `AudioContext` & `AnalyserNode` during playback, with smooth adaptive harmonic oscillation fallback.
9. **Collapsible Subtitle Segments (Quick Toggle Button)**:
   - Kept the clean Neo-Brutalist `#toggleGridBtn` (`â–¼ HIDE CARDS` / `â–¶ SHOW CARDS`) in the toolbar (removed the redundant `<select>` dropdown as requested).
   - Allows collapsing 400+ subtitle cards with one click to focus on the video/audio player or download options.
   - Displays `#segmentsCollapsedCard` when hidden; typing in the search box automatically expands the grid to display filtered matches.
10. **Native Windows Launcher (`HinglishSubtitles.exe`) & In-UI Terminal Toggle**:
   - Built [`HinglishSubtitles.exe`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/HinglishSubtitles.exe) (compiled with `gcc -mwindows` with embedded `app_icon.ico` resource).
   - Flagged with Windows GUI subsystem (`IMAGE_SUBSYSTEM_WINDOWS_GUI`), so Windows allocates **zero console window** at launch.
   - Can be pinned directly to the Windows Taskbar and Start Menu.
   - Removed redundant pills from the settings card as requested; terminal visibility is managed cleanly via the navigation bar dropdown (`#launchModeSelect`), persisting to `launch_config.json`.
   - `run_app.bat`, `run_app_no_terminal.vbs`, and `stop_app.bat` remain available for full portable control.
   - 18 automated unit tests passing in `tests/test_upgrades.py`.
11. **D: Drive Model Storage & Base Model Removal**:
   - Relocated model cache to `D:\Hinglish_subtitles\models\huggingface\hub`, freeing up space on C: drive (C: has 31+ GB free, D: has 41+ GB free).
   - `HF_HOME` is systematically configured in `launch_config.json`, `hinglish_engine.py`, `server.py`, `run_app.bat`, and compiled into `HinglishSubtitles.exe`.
   - Removed obsolete `base` model from `static/index.html`, `app.py`, `hinglish_engine.py`, and `MODEL_SPECS`.
   - `large-v3-turbo` is cached and active on D: drive as the primary high-accuracy model.
12. **Model Fleet Stocked on D: Drive (Ready for Optimization)**:
   - Full Whisper suite cached on D: `tiny`, `small`, `medium`, `large-v3-turbo`, `large-v3`.
   - Candidate models downloaded:
     - `FunAudioLLM/SenseVoiceSmall` (~1.1 GB) at `D:\Hinglish_subtitles\models\huggingface\hub\models--FunAudioLLM--SenseVoiceSmall`
     - `parthiv11/indic_whisper_hi_multi_gpu` (~960 MB) at `D:\Hinglish_subtitles\models\huggingface\hub\models--parthiv11--indic_whisper_hi_multi_gpu`
   - Ready for next phase: fine-tuning `small` model parameters (quantization, VAD, Hinglish `initial_prompt`), and hooking up the alternative inference backends.
13. **AI4Bharat IndicConformer (600M) Local Integration**:
   - Manually installed and verified at `D:\Hinglish_subtitles\indic-conformer` (403 files, 2.49 GB).
   - Validated ONNX runtime inference (29 sessions loaded, CTC decoding + word-level timestamps tested and verified on real audio).
   - Added `IndicConformer (AI4Bharat 600M)` button to `static/index.html` with dynamic `âœ“ CACHED ON DISK` status check.
   - Wired directly into `generate_subtitles` dispatch pipeline with automatic fallback and caching.
   - All 18 automated unit tests passing in `tests/test_upgrades.py`.
14. **ARTPARK-IISc SraVaani 1.0 (430M) Local Integration**:
   - Installed at `D:\Hinglish_subtitles\SraVaani-1.0` (908 MB model weights + tokenizer).
   - Installed `sentencepiece` and verified word-level timestamp generation on real audio.
   - Added `SraVaani 1.0 (ARTPARK-IISc)` button to `static/index.html` with dynamic `âœ“ CACHED ON DISK` status check.
   - Wired into `generate_subtitles` execution pipeline with lazy caching.
15. **Alibaba SenseVoice-Small Local Integration**:
   - Cached at `D:\Hinglish_subtitles\models\huggingface\hub\models--FunAudioLLM--SenseVoiceSmall` (~1.1 GB).
   - Powered by `funasr` 1.4.16 + `kaldi-native-fbank` 1.22.3 on CUDA with ~0.38s forward-pass speed.
   - Strips audio event emojis (`rich_transcription_postprocess`) and maps word-level timing across the audio timeline into the DP semantic chunker and LoanwordRecoverer.
   - Wired into `generate_subtitles()` and verified on real audio fixtures.
   - All 19 automated unit tests passing in `tests/test_upgrades.py`.
16. **Stealth Industrial Mechanical Scrollbar (Option 1)**:
   - Applied global styling in `static/tokens.css` replacing default OS 17px grey rounded scrollbars with strict `border-radius: 0px`, 8px mechanical rails.
   - Inset `#08090d` track with 1px border; `#282c3c` thumb transitioning to `#475569` on hover and crisp `#ffffff` on active drag.
   - Fully cross-browser (`scrollbar-width: thin; scrollbar-color: ...` + `::-webkit-scrollbar*` rules).
   - Unit tested in `tests/test_upgrades.py`.
17. **PySide6 Standalone Native Application Window (Zero Browser Dependency)**:
   - Upgraded `server.py` to embed Chromium directly via `PySide6.QtWebEngineWidgets.QWebEngineView` in a native `QMainWindow`.
   - Complete detachment from external browser executables (`msedge.exe` / `chrome.exe`).
   - Features native Windows dark titlebar (`DwmSetWindowAttribute`), custom `app_icon.ico`, and centered geometry.
   - Fully deterministic rendering: custom 8px mechanical scrollbar renders with 100% precision without Edge OS Fluent scrollbar interference.
   - Clean background daemon thread for FastAPI with seamless termination on window close.
18. **Instant Native Window Launch Optimization (< 0.3s Appearance)**:
   - Eliminated blocking `urllib` polling loop in `server.py`: window is centered and presented to the user on frame 1 (~0.2s) while Uvicorn server boots concurrently in background thread.
   - Replaced slow `download_model(local_files_only=True)` calls in `is_model_cached()` with instantaneous directory checks on D: drive hub cache.
   - Cached `nvidia-smi` hardware detection query in `get_hardware_info()` to avoid repeated subprocess execution.
19. **Native Desktop Window with Full H.264/MP4 Video Codec Support (`pywebview` / Windows WebView2)**:
   - Replaced PySide6 QtWebEngine with native Windows WebView2 via `pywebview` as the primary desktop runner.
   - Root Cause: Precompiled PySide6 binary wheels on PyPI exclude proprietary H.264/AAC codecs (`canPlayType` returned `""`), causing black video screens and 00:00 duration on `.mp4` uploads while open-source audio worked.
   - Windows WebView2 provides 100% native hardware-accelerated H.264/MP4/AAC media decoding, full audio support, instant launch, and pixel-perfect custom 8px mechanical scrollbars with zero browser chrome or dependency.
   - Automatic cascade fallback: `pywebview` -> `PySide6` -> `browser window`.
20. **Synchronous Server-Side Preference Injection & Anti-Caching**:
   - **Root Cause of Model Resetting Bug**:
     1. `index.html` had hardcoded `class="pill active"` on `medium`.
     2. In WebView2/pywebview, static assets like `app.js` were aggressively cached without version busting, meaning frontend changes to the saved-preferences fetch were skipped on reload.
     3. An async network race condition occurred in `initApp()`: `fetchModelStatuses()` was awaited before `fetchSavedPreferences()`, causing `updateModelStatusUI()` to execute with default `selectedModel = "medium"` and flash the Medium model.
     4. `pywebview` process termination left orphaned daemon processes on port 8501, causing subsequent launches to bind to port 8502 where origin-partitioned `localStorage` was empty.
   - **Fix Implemented**:
     1. **Synchronous Injection**: In `server.py`, `read_root()` reads `launch_config.json` and injects `window.__INITIAL_CONFIG__ = {...}` directly into `<head>`, dynamically marks the saved model's pill with `class="pill active"`, updates the `#modelMetaPill` text, and appends a timestamp cache-buster (`app.js?v={mtime}`).
     2. **Immediate Client Hydration**: In `static/app.js`, `selectedModel` and selectors initialize synchronously from `window.__INITIAL_CONFIG__` before any network calls, eliminating layout shift and async race conditions completely.
     3. **Anti-Caching Headers**: Added middleware enforcing `Cache-Control: no-cache, no-store, must-revalidate, max-age=0` on all `.js`, `.css`, and `.html` requests.
     4. **Clean Process Lifecycle**: `stop_app.bat` now explicitly releases ports 8501 and 8502, and `server.py` invokes `os._exit(0)` on window close so no lingering background server threads remain.
     5. Verified end-to-end with unit tests and headless Playwright browser automation tests.











21. **Tiny Model Deprecation & Removal**:
   - Removed 	iny from MODEL_SPECS in hinglish_engine.py.
   - Removed 	iny button pill from static/index.html and MODEL_DISPLAY_NAMES in server.py.
   - Updated CLI parser in hinglish_engine.py and unit tests in 	ests/test_upgrades.py (19 passing).

22. **Dedicated Hindi âž” English Translation Engine (`hindi_to_english_engine.py`)**:
   - **Root Cause of Hinglish-in-Translation Bug**: Whisper's `initial_prompt` was polluted with Devanagari Hindi text (`SCRIPT_ANCHOR` / `STYLE_TEMPLATE`), causing Whisper's decoder to ignore `task="translate"` and generate Devanagari Hindi, which then was transliterated into Latin Hinglish (`TUMHARE LIYE TRAFFIC...`).
   - **Root Cause of Large-V3-Turbo Outputting Hindi**: OpenAI distilled `whisper-large-v3-turbo` down to a 4-layer decoder specifically optimized for transcription. Its translation head was pruned during distillation, causing `task="translate"` to collapse back to source-language (Devanagari Hindi) transcription regardless of prompts. In contrast, full multilingual models (`large-v3`, `medium`, `small`) fully support cross-lingual translation.
   - **Fix Implemented**: 
     1. Created dedicated engine [`hindi_to_english_engine.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/hindi_to_english_engine.py) with English primer prompt (`"English subtitles with natural grammar, proper sentence capitalization, and punctuation."`).
     2. In `hindi_to_english_engine.py`: If `model_size == "large-v3-turbo"`, it automatically routes to the full cached `large-v3` on D: drive for studio-grade English translation. Acoustic-only models (`indic-conformer`, `sravaani`, `sensevoice`) route to `medium`.
     3. In `static/app.js`: When `selectedLanguage === "hi-en"` and `selectedModel === "large-v3-turbo"`, the status bar informs the user: `âš¡ AUTO-ROUTED TO LARGE-V3: Large-v3-Turbo is distilled for transcription only. The translation pipeline automatically uses full Large-V3 (Studio) for English translation.`
   - In `server.py`:
     - Dispatches `if language == "hi-en": from hindi_to_english_engine import generate_english_subtitles`.
   - In `static/app.js`:
     - Dynamic button label updates: `#downloadHinglishBtn` displays `ðŸ“¥ DOWNLOAD ENGLISH SRT`, `#captionToggleGroup` displays `ENGLISH`, and `#generateBtn` displays `TRANSLATE TO ENGLISH`.
   - Validated end-to-end on both [`traffic.mp4`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/static/samples/traffic.mp4) and [`genius_ad.mp4`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/static/samples/genius_ad.mp4) producing natural English subtitles (`"How did an ad save Dettol while drowning? See, the market comes with a saebolon and the disadvantage of Dettol is that when we put Dettol on it, it gets a little burnt."`).
   - All 37 automated unit tests passing in `tests/test_upgrades.py`.

23. **Contextual Model Visibility Filtering (Auto-Hiding Incompatible Models)**:
   - **User Request**: Automatically hide models that do not support English / English translation when in English-oriented modes.
   - **Implementation**:
     - `ENGLISH_TRANSLATION_MODELS = ["small", "medium", "large-v3"]`
     - `ENGLISH_ASR_MODELS = ["small", "medium", "large-v3-turbo", "large-v3", "sensevoice-small"]`
     - When `Hindi âž” English` (`selectedLanguage === "hi-en"`) is selected:
       - Auto-hides `large-v3-turbo` (transcription-only distilled model), `indic-conformer`, `sravaani-1.0`, and `sensevoice-small`.
       - Only supported multilingual translation models (`small`, `medium`, `large-v3`) remain visible in both the Settings Drawer (`#modelPills`) and the Main Window pinned card (`#mainModelPills`).
       - If the user was on an incompatible model, automatically switches to `large-v3` (from turbo) or `medium`.
     - When `English` (`selectedLanguage === "en"`) is selected:
       - Auto-hides Hindi-only acoustic models (`indic-conformer`, `sravaani-1.0`).
     - When switching back to `mixed`, `hi`, or `auto`:
       - All models automatically unhide.
     - Synchronous initial HTML injection in `server.py` (`replace_model_pill`) renders with `style="display: none;"` on initial page load if saved language is `hi-en`, preventing any layout flash.
   - All 38 automated unit tests passing in `tests/test_upgrades.py`.

24. **Language & Model Preference Persistence Across App Restarts**:
   - **User Reported Issue**: Selecting `Hindi âž” English` (`data-lang="hi-en"`) and restarting the app reset back to pure Hindi/Mixed option with all hidden models unhidden.
   - **Root Cause Analysis (RCA)**:
     1. In [`server.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/server.py): `read_root()` was updating model pills, but **completely omitted updating language ribbon tiles** (`<button class="tile ... data-lang="...">`), device pills, and pacing pills in HTML. As a result, the server always sent HTML with `class="tile active"` on `mixed` (or previous tile).
     2. In [`server.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/server.py): Cache buster `html.replace('src="app.js"', ...)` failed to match because [`static/index.html`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/static/index.html) had `src="app.js?v=3.2"`. WebView2 served cached `app.js` which did not support `window.__INITIAL_CONFIG__`.
     3. In [`static/app.js`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/static/app.js): `saveBackendPreference` only sent one isolated key (`selected_language`), leaving `selected_model` missing from [`launch_config.json`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/launch_config.json).
     4. In [`tests/test_upgrades.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/tests/test_upgrades.py): `test_preferences_persistence` was posting `"selected_language": "hi"` and overwriting `launch_config.json` on disk without restoring it.
   - **Fix Implemented**:
     1. In `server.py`: Added attribute-order-agnostic regex replacement in `read_root()` for language tiles (`data-lang`), model pills (`data-model`), device pills (`data-device`), and pacing pills (`data-pacing`), plus regex-based cache buster `src="app.js?v={v_time}"`.
     2. In `server.py`: Passed explicit isolated `storage_path` (`.webview_cache`) to `webview.start` so pywebview persists localStorage and cookies across restarts.
     3. In `static/app.js`: Updated `saveBackendPreference` to always send the complete preferences bundle (`selected_language`, `selected_model`, `selected_device`, `selected_pacing`) so `launch_config.json` is always complete. Reordered initialization so language selection runs first, ensuring model visibility filtering is established before model selection is finalized.
     4. In `static/index.html`: Cleaned script tag to `<script src="app.js"></script>`.
     5. In `tests/test_upgrades.py`: Updated `test_preferences_persistence` to test `hi-en` language persistence, model hiding, and restore the original `launch_config.json` in a `finally:` block.
   - All 38 automated unit tests passing in `tests/test_upgrades.py`.

25. **Hero Heading Copy Cleanup**:
   - Removed legacy tagline `"One terminal"` and applied Option 1 hero structure in [`static/index.html`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/static/index.html#L171):
     `<h1>Hinglish<br><mark>subtitles</mark>.</h1>`
   - Bold yellow badge block now highlights `subtitles`.
   - All 38 automated unit tests passing.

26. **Karaoke / Animated Word Subtitles (Phase 1)**:
   - Added [`karaoke_ass.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/karaoke_ass.py) producing `.ass` scripts with `{\k<centiseconds>}` tags formatted in high-contrast Alex Hormozi / TikTok style.
   - Word token timelines `[{start, end, word, hinglish}]` attached to all segment results in [`hinglish_engine.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/hinglish_engine.py) and [`hindi_to_english_engine.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/hindi_to_english_engine.py).
   - Added `POST /api/export/ass` in `server.py` and `ðŸŽ¤ KARAOKE (.ASS)` export action in the UI.
   - 5 dedicated unit tests in `tests/test_karaoke_ass.py`.

27. **Direct Video Burning Engine (Phase 2)**:
   - Built [`video_burner.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/video_burner.py) wrapping local FFmpeg with Windows MediaFoundation hardware encoder (`h264_mf`) and relative path execution to prevent Windows colon/backslash escaping bugs in `libass`.
   - Exposes `POST /api/export/burn-video` in `server.py` streaming encoded MP4 directly to the client.
   - Added `ðŸ”¥ BURN VIDEO (.MP4)` in the floating export bar with live indeterminate pulse progress.
   - 3 dedicated unit tests in `tests/test_video_burner.py`.

28. **Offline Acoustic Speaker Diarization (Phase 3)**:
   - Built [`diarization.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/diarization.py) extracting 28-dimensional acoustic features (13 MFCCs + spectral centroid mean & std) per segment and clustering with `AgglomerativeClustering`.
   - Euclidean distance thresholding (< 60.0) ensures single-speaker audio is never artificially split into multiple speakers.
   - Integrated `enable_diarization` flag into `hinglish_engine.py`, `hindi_to_english_engine.py`, and `server.py` `/api/transcribe`.
   - Added UI toggle in the Settings Drawer and rendered `#Speaker N` badges on cards in [`static/app.js`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/static/app.js) and [`static/components.css`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/static/components.css).
   - 5 dedicated unit tests in `tests/test_diarization.py`.
   - Regression suite: **51/51 tests passing**.

29. **Ponytail Code Audit & Lean Hardening (11 Findings Applied)**:
   - **Burned MP4 RAM Spike Fixed**: [`server.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/server.py) returns `FileResponse` streamed from disk with `BackgroundTask` deleting the temporary working directory after client download completes, eliminating full `f.read()` heap allocations.
   - **FFmpeg Console Window Flashing Fixed**: Added `creationflags=_NO_WINDOW` (`CREATE_NO_WINDOW`) to all `subprocess.run` calls in [`video_burner.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/video_burner.py).
   - **Diarization Configuration Sync**: `"enable_diarization"` added to default `prefs` and injected into `window.__INITIAL_CONFIG__` in `read_root()`.
   - **Storage Hygiene Sweeps**: Added startup sweeps in `server.py` cleaning `temp_media/` clips older than 7 days and sweeping orphaned `hburn_*` directories left by aborted sessions.
   - **Encoder Capability Cached**: Probe runs once per process and caches in `_CACHED_ENCODER`.
   - **Dead Code & Redundant Calls Deleted**: Deleted dead Streamlit prototype `app.py` (-268 lines), removed redundant `fetchSavedPreferences()` from [`static/app.js`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/static/app.js) (-16 lines), and purged unused `models_dir` from [`launch_config.json`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/launch_config.json).
   - **Log Rotation**: `console_bus.py` rotates `logs/app.log` to `app.log.old` when it exceeds 2 MB at startup.
   - **Docs & Test Suite**: Corrected CLI model options in `README.md`, added 3 failure/cache unit tests in `tests/test_video_burner.py`.
   - **Pinned Dependencies**: Added [`requirements.txt`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/requirements.txt) with 18 pinned packages (FastAPI, PyWebView, Faster-Whisper, Aksharamukha, Librosa, Scikit-learn, CUDA 12 DLLs, Pytest, etc.).
   - **Test Suite**: **55/55 tests passing** in 9.68s. Git commits `d4ac5a6`, `0ba64c1`, `d92f828`, and `16ff60d`.

30. **Caption Templates, Custom Style Studio & True libass Preview (Phase 4)**:
   - **Style Schema & Presets**: Created [`caption_styles.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/caption_styles.py) housing 6 validated presets (`hormozi`, `vox`, `cyber`, `blackout`, `editorial`, `blank`), RGBâ†’ABGR color conversion, and canvas profiles for `9:16` (1080Ã—1920), `16:9` (1920Ã—1080), and `1:1` (1080Ã—1080).
   - **Canvas-Aware ASS Generator**: Upgraded [`karaoke_ass.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/karaoke_ass.py) to dynamically scale `PlayRes`, fonts, line-entry animations, and margins based on source aspect ratio and selected template.
   - **True libass Preview Renderer**: Added [`preview_renderer.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/preview_renderer.py) and `GET /api/preview-style` serving a cached 2.5s MP4 rendered with FFmpeg on a synthetic gradient backdrop in <150ms.
   - **UI Studio & Disarmed Export Trap**: Added Caption Style picker to Settings Drawer with instant CSS preview, "Verify Render" true preview, duplicate-to-custom cloning, and JSON import/export. Fixed export/burn handlers in [`static/app.js`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/static/app.js) to always generate fresh ASS with active style.
   - **Stock Windows Fonts**: Relies on 100% deterministic native Windows fonts (`Impact`, `Arial Black`, `Segoe UI`, `Georgia`, `Consolas`), eliminating silent font fallback.
   - **Test Suite**: Added 27 new tests across `test_caption_styles.py`, `test_caption_api.py`, and `test_preview_renderer.py`. **82/82 tests passing**. All 9 matrix burns verified.

31. **Pinned Caption Style & Speaker Diarization (3-Zone Bento Cockpit)**:
   - **Dynamic Pinning**: Added `[ ðŸ“Œ PIN TO MAIN ]` switches for both **Caption Style** (`#pinStyleSwitch`) and **Speaker Diarization** (`#pinDiarizeSwitch`) in the Settings Drawer.
   - **Adaptive 3-Zone Bento Grid**: Controls container above dropzone reflows dynamically across `cols-1`, `cols-2`, and `cols-3`:
     - *Left Column*: Topic Hints + Pinned Hardware/Pacing + Pinned Speaker Diarization (`OFF` vs `MULTI-SPEAKER`).
     - *Middle Column*: Pinned ASR Model Switcher (`#mainModelPills`).
     - *Right Column*: Pinned Caption Style presets (`#mainStylePresetGroup`) with compact live visual sample chip.
   - **Bidirectional Sync & Persistence**: Main-window preset and diarization clicks immediately sync with drawer components, save to `launch_config.json` and `localStorage`, and reload cleanly.
   - **Bugfix (Diarization State Reset)**: Fixed bug where diarization reset to OFF on reload because server default `enable_diarization: false` overrode stored client state.
   - **Test Suite**: Extended pin-switch UI tests in `tests/test_upgrades.py`; all **82/82 tests passing**.

32. **Studio UI Regression Pass (2026-10-21)**:
   - While setup is expanded, `[HIDE SETUP]` is lifted to a fixed top-right control so it cannot fall behind the export dock. On phones it becomes a compact `X` in the same corner.
   - When setup is expanded, the language ribbon switches to 2 columns at `<= 1080px`, preventing the five-tile row from being clipped in the narrower editor-offset workspace. It stays 5 columns at wider widths where it fits.
   - The export action row uses start alignment with an auto left margin: when it fits it stays right-aligned, and when it overflows the first action and primary download remain visible while the remaining actions scroll horizontally.
   - Resizing a desktop window below `900px` automatically collapses the editor to its 58px rail without persisting that automatic state, preserving the user's desktop editor-width/collapse preference.
   - Style JSON import now sends one preference POST and reports `IMPORTED`; export, import, and the editor resizer were browser-verified. **83/83 tests passing**.

33. **Live Karaoke Highlight Fix (2026-10-21)**:
   - The live video overlay previously painted every word in `base_color`; `highlight_color` was only used by `.ASS` exports and the style samples.
   - [`static/app.js`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/static/app.js) now builds per-word spans when a segment's `words` timings align with the displayed text, and switches words whose start time has passed to `highlight_color`.
   - Style edits recolor existing word spans immediately, so changing the highlight colour updates the paused video without seeking.
   - Verified against the `He-Turned-Traffic` source with the saved custom style; the spoken words render mustard while upcoming words stay red, matching the libass `\k` export. **83/83 tests passing**.

34. **Local Captions.ai Template Lookalikes (2026-10-21)**:
   - Added 8 local presets inspired by the Captions.ai / Mirage gallery: **Buzz**, **Medusa**, **Cartwheel Black**, **Heat**, **Neon**, **Magazine**, **Techwave**, and **Minima** (14 presets total including Blank).
   - The gallery only publishes template IDs and preview MP4s, not font/colour parameters, so these are hand-tuned local approximations â€” no Mirage API key, upload, or cloud transcription is involved.
   - [`caption_styles.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/caption_styles.py) stores the new presets in display order; [`static/app.js`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/static/app.js) adds compact names and now honours `outline_width: 0` while rendering the schema's `shadow` value. Box presets use an 8px live radius.
   - Browser-verified actual preset clicks, live spoken-word recolouring, `.ASS` style lines, and MP4 burns for Medusa, Buzz, and Techwave. **85/85 tests passing**.

35. **123 Honey Punch Kinetic Word-Pop (2026-10-22)**:
   - Replaced the static `123 Honey Punch` look with a real word-by-word kinetic preset matching `Videos/123effect`: top-anchored at 20% frame height, alternating right/left phrase anchors, gold content words, white connectives, a 155% active-word pop, and a 135% settled accent size.
   - [`caption_styles.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/caption_styles.py) now carries `motion: "word-pop"`, `kinetic_layout: "alternate"`, `accent_mode: "content"`, anchor/width/gap/pop/settle fields, and resolves/clamps them for custom styles.
   - [`karaoke_ass.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/karaoke_ass.py) emits per-frame ASS Dialogue events (~30 fps) with static per-word colours and sizes, explicit wrapped `\N` lines, `\an9`/`\an7` anchors, and no `\k`. Phrase grouping uses a 650 ms gap; the opening interjection is forced onto its own line.
   - [`static/app.js`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/static/app.js) mirrors the same rules in the live overlay with a rAF playback loop, flex word spans, alternating justification, a forced break after the opening interjection, and play/pause/ended hooks. [`static/components.css`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/static/components.css) supplies the kinetic layout.
   - Portrait frames use a 0.70 base-size factor and a wider wrap allowance so a three-word punch phrase does not collapse to one word per line; landscape keeps the reference 8% cap height.
   - Verified with Playwright live previews at 16:9, generated 16:9 preview frames, and a real `h264_mf` MP4 burn with `video_burner.py`. **94/94 tests passing**; changes remain uncommitted.

36. **123 Honey Punch Kinetic Phrase Overflow Fix (2026-10-22)**:
   - **Root Cause**: Previously, phrase grouping in [`static/app.js`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/static/app.js) and [`karaoke_ass.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/karaoke_ass.py) solely relied on audio silence gaps (`> 650ms`). In rapid, continuous speech (e.g. 24-word Whisper sentences with no 650ms pauses), words accumulated infinitely into a single phrase, forming a massive 10–17 line text wall that filled 80% of the video and completely obscured the speaker on vertical 9:16 reels.
   - **Adaptive Phrase Chunking**: Introduced word-limit caps (`max_words`: 3 on portrait, 6 on landscape) and punctuation-boundary splits (`,`, `.`, `?`, `!`, `;`, `—`, `-` when phrase has $\ge 2$ words). This guarantees compact 2–4 word bursts that alternate left and right dynamically.
   - **Portrait Video Fitting**: In [`static/app.js`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/static/app.js) and [`static/components.css`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/static/components.css), increased portrait container width allowance from 70% to 78%–88% and calibrated portrait base factor to 0.65, ensuring phrases fit comfortably across 1–2 clean lines.
   - **Backend ASS Export Parity**: Synchronized `_group_phrases()` in [`karaoke_ass.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/karaoke_ass.py) with the same chunking constraints, ensuring downloaded `.ass` and burned MP4 video match the on-video live preview.
   - **Verification & Test Suite**: Added dedicated regression test `test_kinetic_long_utterance_splits_into_compact_chunks()` in [`tests/test_karaoke_ass.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/tests/test_karaoke_ass.py). Created interactive comparison prototype at [`honeypunch_caption_options.html`](file:///c:/Users/susha/Documents/General/honeypunch_caption_options.html). Full test suite: **95/95 tests passing**.

37. **123 Honey Punch Pre-Layout Rewrite (2026-10-23)**:
   - **Behaviour Change**: Replaced the reflowing word-pop with a pre-laid-out reveal. The whole phrase now reserves its final line breaks, widths, and word positions up front; spoken words become visible in place while future words stay invisible but keep their space. Nothing reflows or jumps mid-phrase.
   - **No Scaling**: Removed active-word pop/settle entirely. `accent` now means gold only, and `punch` (a separate attribute) means roughly 1.5× size. `Hey,`, `bakery`, proper nouns, and the `The Sweet Spot?` title are punch; `hear` and `by` are gold but normal-sized. `by` was added to the accent sets in both renderers.
   - **Phrase Integrity**: Phrases end on a card boundary or the 10-word cap. Punctuation never splits a phrase, but an interjection break and a post-question-mark break are forced, plus a semantic break after `about` before `the`. The reference shapes are four lines (`Hey,` / `did you hear about` / `the bakery in` / `Willow Creek,`) and two lines (`The Sweet Spot?` / `It's run by Emma`).
   - **Right Alignment**: Both blocks are right-aligned at ~80% width. Style `max_width` is `55`; live landscape uses `max_width - 4` = 51%.
   - **Typography**: Honey Punch uses `Arial` at `font_size` 128, `anchor_y` 22. The title phrase anchors 4.5% higher. Live adds 1.5% leading compensation (23.5% normal / 19% title) because the browser and libass distribute first-line leading differently. Live line-height is 1.2 with a 9px landscape row gap and 6px portrait gap.
   - **ASS Calibration**: The export wraps with unscaled Pillow metrics so line breaks stay browser-matched, then calibrates only the emitted `\fs` values: `_KINETIC_ASS_FONT_SCALE = 1.399`, `_KINETIC_ASS_NORMAL_SCALE = 0.95`, and `ScaleX` 90.5. At 720p normal words emit `\fs77` and punch `\fs122`; at 1080p, `\fs114` and `\fs180`. Anchors are `\pos(1024,158)` / `(1024,126)` at 720p and `\pos(1536,238)` / `(1536,189)` at 1080p.
   - **Verification**: Live overlay measured at 860×480 — phrase 1 rows at y≈114/195/253/328 with right edge 686.8, phrase 2 title at y≈92.4. ASS frames and a real `h264_mf` burn through `video_burner.py` both match the reference layout. **95/95 tests passing**; changes remain uncommitted.

38. **Recess Caption Preset & On-Video Freeze Fix (2026-10-23)**:
   - **New preset**: Added **Recess** (16 presets total) — a centred, all-caps kinetic reveal where the spoken word sits in a lime→periwinkle gradient pill that slides word-to-word. Punch words are 2.03× and occupy their own card (`kinetic_grouping: "punch"`): `HEY` / `DID YOU HEAR ABOUT THE` / `BAKERY` / `IN` / `WILLOW` / `CREEK` / `THE` / `SWEET` / `SPOT?` / `IT'S RUN BY` / `EMMA` / `?`.
   - **Schema**: [`caption_styles.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/caption_styles.py) gains `pill`, `pill_gradient_start/end`, `pill_pad_x/y`, `pill_radius`, `pill_alpha`, `pill_fade_ms`, `pill_slide_ms`, `reveal_fade_ms`, `reveal_spring_ms`, `kinetic_size_scale`, and `kinetic_grouping`; the `accent_scale` clamp widens to 210 for the measured 2.03× punch ratio.
   - **ASS renderer**: [`karaoke_ass.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/karaoke_ass.py) emits one layer-0 event per gradient band (libass merges multiple `\p1` blocks inside a single event), per-word layer-1 events with explicit `\an5\pos`, and uses a 0.640 ink / 0.652 advance / 0.520 cap calibration. At 1080p the emitted em is `\fs197`; the pill is 58 % alpha with a `0.26` em radius.
   - **Live overlay**: [`static/app.js`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/static/app.js) mirrors the layout with `RECESS_LIVE_EM = 0.652`, layout-coordinate pill placement (`offsetLeft`/`offsetTop`, never `getBoundingClientRect`, which the reveal transform moves), per-card re-anchoring on the video's midline minus the 0.035 em cap lift, punch-grouped phrases, and a WAAPI spring. [`static/components.css`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/static/components.css) adds the `.kinetic.recess` stack and `#captionPill`; row spacing is a `--recess-row` px custom property with `row-gap: 0`, because a forced flex break is a zero-height line and `row-gap` would be charged twice.
   - **Freeze bug**: On-video captions froze after a few seconds because `applyCaptionStyleToVideo()` blanked the overlay and re-rendered the *editor-selected* card instead of the card under the playhead. The playhead is now the single source of truth; regression coverage lives in [`tests/js/caption_sync_test.js`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/tests/js/caption_sync_test.js) + [`tests/test_caption_sync.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/tests/test_caption_sync.py).
   - **Live tests**: [`tests/js/dom_stub.js`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/tests/js/dom_stub.js) now models `className`/`classList`, `style.setProperty/getPropertyValue/removeProperty`, element offsets, class selectors, and canvas `measureText`. [`tests/js/recess_overlay_test.js`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/tests/js/recess_overlay_test.js) + [`tests/test_recess_overlay.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/tests/test_recess_overlay.py) pin the pill geometry (17.59 px radius at 860×480, cap centre, row gap) and assert Honey Punch is untouched.
   - **Verification**: **112/112 tests passing**, `node --check static/app.js` clean. `h264_mf` burn at 1080p: `BAKERY` ink 1181×203 / pill 1225×307 vs reference 1130×215 / 1181×313; pill boxes and centres within 4 % / 3 px, with the ink error being the documented Arial Black substitution. `launch_config.json` restored; nothing committed or pushed.


39. **Caption Timing Engine Fix — All Styles (2026-10-25)**:
   - **Measured first**: Two 58 s clips through the shipping pipeline, word starts vs acoustic energy onsets (10 ms frames). Whisper was already fine (median −30 ms / +65 ms, p10–p90 ≈ ±200 ms, no drift r = 0.11) and the burned file was exact (0 ms audio offset, `\k` chain within 40 ms for 188/189 words). The defect was the **live preview**: classic styles were painted only on `timeupdate` (~4 Hz), so a card could appear **90–140 ms late (p90 220 ms)** plus a 150 ms CSS fade.
   - **One clock**: [`static/app.js`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/static/app.js) adds `startCaptionLoop` / `stopCaptionLoop` / `captionTick` on `requestVideoFrameCallback` (rAF fallback), `activeCardIndexAt()` binary search, and a `captionRenderKey` dirty check; `timeupdate` is now only a correction event, with `seeking` / `seeked` / `ratechange` / `play` / `pause` / `ended` handled. The kinetic loop was folded into the same clock.
   - **Cheap frames**: `renderCaptionText` still builds the card's spans, but the per-frame path is only `applyCaptionWordColors`; `applyCaptionStyleToVideo()` no longer rebuilds spans (callers that need a repaint call `updateVideoCaption(true)`), and the classic fade is a `--caption-fade` variable defaulting to **80 ms**.
   - **Parity**: `karaoke_ass.py` now emits a `\k` gap for **every** intra-card silence (previously only word 0 got a lead), and `format_ass_time` carries `cs >= 100` instead of clamping to 99. Measured `\k` chain error is now **0 ms for 189/189 words** (was one word at −340 ms).
   - **Sync nudge**: `#captionSync` in [`static/index.html`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/static/index.html) (±20 ms steps, ±500 ms, persisted in `localStorage("hinglish.captionOffsetMs")`). It shifts `currentSegments` from an untouched `captionBaseSegments`, so the live overlay, `rebuildSrt`, `/api/export/ass` and the burn all inherit one number; `captureCaptionBase()` re-derives the base after an editor edit so a nudge cannot undo it.
   - **Timestamp hardening**: shared `clamp_word_span()` (used by `transcribe_words` and `hindi_to_english_engine.py`, duplicate block deleted) returns a `tail`; `pad_display_times` holds the card over up to `TAIL_HOLD_MAX = 1.5 s` of it and never into the next card; `merge_split_words` preserves the tail.
   - **Tooling**: [`tools/measure_timing.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/tools/measure_timing.py) reproduces all of the above (read-only, opt-in). New coverage: [`tests/js/caption_clock_test.js`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/tests/js/caption_clock_test.js) (frame painting, no rebuild, colours, gap hide, pause, force repaint, nudge maths), [`tests/test_caption_clock.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/tests/test_caption_clock.py), [`tests/test_timing_contract.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/tests/test_timing_contract.py), plus `\k`-gap and `format_ass_time` carry tests in `tests/test_karaoke_ass.py`.
   - **Verification**: **122/122 tests passing**, `node --check static/app.js` clean. Burn check with a classic style (Hormozi): `h264_mf` success, audio offset **0 ms**, 58.096 s → 58.096 s, and the intra-card pause highlighted on the first frame after the word start (10.017 s for a word at 9.98 s, i.e. within 1 frame; the old chain would have been 220 ms early). Nothing committed; `launch_config.json` untouched.

40. **Transcribe Payload Slimming & Transliteration Token Cache (2026-10-25)**:
   - **Dead payload removed**: every transcription built a full karaoke `.ass` and shipped it as `ass_karaoke`, but nothing read it — the client, tests, and burn path all work from `segments`, and [`server.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/server.py) `/api/export/ass` plus [`preview_renderer.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/preview_renderer.py) already call `generate_karaoke_ass()` on demand. The key and the build block are gone from [`hinglish_engine.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/hinglish_engine.py) and [`hindi_to_english_engine.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/hindi_to_english_engine.py) (the 20-line `ass_cards` adapter in the English engine went with it).
   - **Measured saving** on the 30-card / 137-word reference clip: classic **0.3 ms / 4.2 KiB**, Recess **96 ms / 460 KiB** per job. The audit's earlier "1–2 s / ~2 MB" holds only for long Recess reels (13,775 events), not for typical clips.
   - **Token cache**: [`transliteration.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/transliteration.py) wraps `_transliterate_hindi_word` / `_transliterate_urdu_word` around renamed `*_uncached` bodies and caches the finished Latin form per raw token in `_TOKEN_CACHE` (bounded at 8192, cleared wholesale when full — a clip's working set is a few hundred tokens, so LRU bookkeeping buys nothing). `aksharamukha` was the whole cost and spoken Hinglish repeats a small vocabulary.
   - **Measured**: 81 real Devanagari tokens cycled to 400 per-word calls → **0.180 s → 0.040 s (4.5×)**; a single 400-word call is 0.035 s cold vs 0.001 s warm; cached and uncached output byte-identical. The audit's "3.9 s → 0.16 s" estimate did not reproduce and is superseded in [`tasks/todo_timing.md`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/tasks/todo_timing.md).
   - **Coverage**: `TestTransliterationCache` in [`tests/test_upgrades.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/tests/test_upgrades.py) pins cached-vs-uncached equality for Devanagari and Urdu, cross-call idempotence of `convert_to_hinglish`, and correctness after the cache overflows. **126/126 tests passing**; nothing committed, `launch_config.json` untouched.

41. **Kinetic Word List Cache (2026-10-25)**:
   - **Why**: [`static/app.js`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/static/app.js) `kineticStateAt()` rebuilt the whole word list on every frame of a `word-pop` style — 160 words, each classified twice by Unicode-property regexes, plus a sort and three passes.
   - **Cache**: `kineticWordsCache` keyed on `currentSegments` identity plus caption mode, `accent_mode`, `phrase_gap_ms`, `max_words_per_phrase`, `kinetic_grouping` and the portrait flag. The style/read inputs are in the key, so preset changes need no invalidation; the two `currentSegments` reassignments (nudge, load) change identity by themselves.
   - **The one invalidation**: `saveEditorSegment()` mutates cards **in place** (`seg.hinglish_text`, `seg.start`, `seg.end`), so `captureCaptionBase()` — already called from `refreshResultsAfterEditorChange()` — clears `kineticWordsCache.segments`.
   - **Measured** (Node, 160 words / 64 phrases, [`%TEMP%\opencode\bench_flatten.js`]): rebuild **0.58 ms/call**, cache hit **0.00 ms**. The audit's 7.2 ms/frame did not reproduce; that figure most likely included the forced layout from `getBoundingClientRect()`, which `kineticBaseSize` / `kineticMaxWidthPercent` still call every frame.
   - **Coverage**: new "kinetic word cache" case in [`tests/js/caption_clock_test.js`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/tests/js/caption_clock_test.js) (array reused on the second call; rebuild after `captureCaptionBase()`, caption-mode change, accent-mode change and a new segment array), with `flattenKineticWords` / `captureCaptionBase` exposed through the [`tests/js/dom_stub.js`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/tests/js/dom_stub.js) hooks. **126/126 pytest**, all three JS suites green, `node --check` clean; nothing committed.



42. **Honey Punch Typography Calibration Against the Resolve Frames (2026-10-25)**:
   - **Method**: the reference PNGs are crops (`ref_phrase1_complete.png` 710x460, `ref_phrase2_complete.png` 860x360), so absolute positions cannot be compared. Each still was split into line bands and then into word components, and **same-letter heights** were compared across tiers (`b` in *bakery* vs `d` in *did*). That measure is independent of glyph shape and of the crop.
   - **Measured, and it contradicts the earlier estimate**: punch/connective is **1.50x**, not 2.0-2.1x (ref ascender 78 px vs 52 px; x-height 58 vs 37; ours 74 vs 49). Gold words that are not punch (`hear`, `by`) sit at **1.0x** — the frames have **no middle tier**. The earlier "2.0x" and "1.3x middle tier" came from band heights, where a punch word and a connective word share one band, and from descenders (`by` is 63 px tall because of its `y`, not because it is larger).
   - **Implication**: the shipped `accent_scale: 150` was already correct. The real deltas were justification and a clipped word, so nothing was inflated.
   - **Justification**: `kinetic_layout: "alternate"` is now real — `\an9` at 93% for even phrases, `\an7` at 7% for odd ones, via `_KINETIC_ALTERNATE_MARGIN = 0.07`. `"right"` keeps the old 80% anchor for saved custom styles. The live overlay mirrors it in pixels, not CSS percentages, because `#captionOverlay` is inset 10 px from the video on each side.
   - **Middle tier is generic, not per-preset**: `accent_size_scale` (100-210, default 100) multiplies gold-non-punch words in both renderers and the overlay; Honey Punch sets 100 to match the frames. `_KINETIC_ASS_NORMAL_SCALE` now applies to **every** tier, so `accent_scale` means the true ratio to a connective word (punch `\fs171`, connective `\fs114` at 1080p; it was 180 before).
   - **Clipped word fixed**: the burn showed `parheshaanee` running past the left edge on 9:16. `_kinetic_lines` now shrinks a single word wider than the line box to fit, and the overlay does the same with advance-width measurement (`kineticAdvance`), so preview and burn agree.
   - **Verification**: **128/128 pytest**, all three JS suites, `node --check` clean. Preview frame at 9:16: phrase 1 right at 7.2%, phrase 2 left at 7.0%. Real burn (`h264_mf -b:v 3M`, 58 s, 1080x1920): anchors alternate `1004/76`, caption box right-flush 7.8% and left-flush 7.8% (7% anchor + side bearing), the long punch word now fits (left edge 15.3%). Nothing committed; `launch_config.json` untouched.
   - **Still open (Step 2)**: the reference stacks lines **downward across Whisper cards** (`Hey,` / `did you hear about` / `the bakery in` / `Willow`) instead of clearing the poster at every card, and the reference's last line is flush left while the lines above it are flush right. That is grouping, not typography: accumulate until sentence punctuation, a >650 ms gap, or 12 words.

43. **Honey Punch Poster Grouping (2026-10-25)**:
   - **Why**: the reference holds one block while the speaker works through a sentence (`The Sweet Spot? It's run by Emma` stays on screen with only `It's run` spoken). Every other kinetic style cleared the block at each Whisper card, so the same 137-word clip drew 35 flashes averaging 3.9 words.
   - **Rule**: new `kinetic_grouping: "poster"` on the Honey Punch preset (all other presets stay `"flow"`, pinned by a test). Poster mode ignores punch words; a run ends at a real word gap over `phrase_gap_ms` (650 ms), at the cap, or at sentence-final punctuation (`.`, `?`, `!`, `।`, including a closing quote/bracket) **only when the speaker confirms it** — see the gate below. The cap is applied **after** grouping, per sentence, so a long run splits evenly instead of leaving a one-word tail. `_ends_sentence` / `kineticEndsSentence` are mirrored in both renderers.
   - **Punctuation needs evidence that the sentence ended**: measured on the burn fixture, both full stops sit at a **0.0 s** word gap (continuous delivery: `...kar rahaa hai. jab log...`), while the smallest mid-sentence hesitation is **0.20 s** (`[0.2, 0.22, 0.34, 0.73]` on unpunctuated words). So `_KINETIC_SENTENCE_PAUSE_SEC = 0.20` / `KINETIC_SENTENCE_PAUSE_SEC = 0.2` gates the split — no split when the speaker runs through the mark, split when they breathe. That restores the reference frame 108120 block (`The Sweet Spot? It's run by Emma` stays one poster while only `It's run` is spoken).
   - **Card end is the second witness**: a pause-only gate glued `hai. jab` into one poster, because Whisper packs sentence ends at 0 ms (`card_end_delta = 0.04`, next-word gap 0.0) and marks the boundary by closing the card. So the condition is `pause >= 0.20 s OR word["card_start"] != previous["card_start"]` — the same stop mid-card with continuous delivery still holds (`The Sweet Spot?` in the test fixture), while a stop at a block end splits.
   - **Caps are measured, not guessed**: the earlier plan (8 portrait / 12 landscape words) produced seven-line portrait posters and six-line landscape Hinglish posters whose last line clipped. `_KINETIC_POSTER_MAX_WORDS = (8, 12)` is now paired with `_KINETIC_POSTER_MAX_LINES = (5, 4)` (portrait/landscape); the splitter cuts at the word boundary closest to an even split among the candidates that fit both limits, so 14 words at an 8-word cap reads 5 + 4 + 5, not 8 + 6.
   - **Measured**: 9:16 goes **35 posters (3.9 words avg) → 22 (6.2 avg, min 4, max 8)**, max **5 lines** ending at 70% of frame height; 16:9 goes **14 → 16 posters (8.6 avg, min 7, max 10)**, max **4 lines** ending at 86%. Flow vs poster at cap 10 on 16:9 is 14 vs 15, so pauses dominate grouping there. Wall parity uses the global poster index, which is why the pinned pair is `["1786","134"]`, not three anchors.
   - **Reference case verified on pixels**: a still at 108120's moment (`hp_spot_run.png`, 16:9) shows line 1 `The Sweet Spot?` fully gold while only `It's run` on line 2 is spoken — the block now holds across the `?`, matching the frame instead of splitting into two posters.
   - **Verification**: **134/134 pytest**, all four JS suites (new `tests/js/poster_grouping_test.js`), `node --check` clean, real `h264_mf` burn at 1080x1920 (16 MB) with anchors alternating `1004/76`. Stills on black: 9:16 five-line block spans x 30-94%, y 23-70%; 16:9 four-line block x 34-93%, y 24-86% — no clipping. Nothing committed; `launch_config.json` untouched.

44. **Burn Output Is Now Faststart (2026-10-25)**:
   - **Why**: burned exports were written `ftyp → mdat → moov`, so a `<video>` element or previewer could not seek until the whole file arrived. The app plays the burned file back through the same page, which makes that visible on any export longer than a few seconds.
   - **Change**: `-movflags +faststart` in `video_burner.py`'s ffmpeg command, after `-c:a copy`. The muxer rewrites the container after encoding, so nothing is re-encoded.
   - **Verified, atom-walked not trusted**: `%TEMP%\opencode\faststart_check.py` walks the top-level boxes of the produced file. 320x240 probe: `ftyp → moov → free → mdat`, moov at byte 32, mdat at 3921. Real 1080x1920 Honey Punch burn: same order, moov at byte 32 and mdat at 25569 of 16,558,313 bytes — the exact same byte count and `1004/76` anchor timeline as the pre-flag burn, so the flag reorders atoms without touching pixels. A `-ss 2.5` decode of the tail returns clean, which is the check that the moov rewrite did not truncate the mdat.
   - **Not done, on purpose**: static-asset `Cache-Control` and `index.html` memoization stay off the list for a single local user on localhost; the win is unmeasurable and the invalidation is a real cost.

45. **One Transcription Job at a Time (2026-10-25)**:
   - **Why**: `_MODELS.clear()` in `get_model` did not evict anything. A run that had already called `get_model` held its model in a local name, so the clear only dropped the dict slot and the next request loaded a second model beside it. `api_transcribe` is a sync `def`, so Starlette runs each request on the worker pool with no project lock; a second window on the same `127.0.0.1:<port>` reaches the same cache.
   - **Reproduced before fixing** (`%TEMP%\opencode\model_cache_race.py`, stubbed `WhisperModel` with a slow ctor): (A) a different size's load emptied the cache and the other size was rebuilt — `['medium', 'large-v3', 'medium']` built, two resident; (B) two threads missing the same key both constructed it and got **two distinct objects**; (C) a switch between `key not in _MODELS` and `return _MODELS[key]` raised **KeyError** — a 500 with a healthy GPU. Old code under four concurrent cold misses: **4 models built, 4 concurrent ctors**. Same script against the new code: **1 build, 1 ctor**.
   - **Fix**: `_MODEL_LOCK` around the whole check-construct-insert in `get_model` (kills B and C), plus `_JOB_LOCK` with a `single_job` decorator on `generate_subtitles` and `generate_english_subtitles` (kills A by making "one model at a time" true: when `get_model` swaps the slot, no other job can hold a model). `_JOB_LOCK` is an `RLock` so a nested entry-point call nests instead of hanging.
   - **The second request answers instead of parking**: `_single_job_endpoint` in `server.py` claims the same slot non-blocking through `claim_job_slot()`, so `/api/transcribe` returns **409** `"Another transcription is already running. Wait for it to finish, then try again."` while a job runs. The request thread re-enters the RLock, so the engine inside is not blocked by its own guard, and the slot is released in `finally`. The browser already renders `detail` through its `throw new Error(errData.detail)` path and re-enables the button, so no front-end change was needed. Verified over ASGI: free slot → the request proceeds (500 on a bogus file), held slot → 409, after release → proceeds again.
   - **Tests**: new `tests/test_model_cache.py` (9 cases) pins one build per key, no exception while another size loads, single-slot cache, job serialisation (`start/end/start/end`), `__wrapped__` on both engine entry points, the **409** for a busy slot, and that a failed job releases the slot. Verified the assertions discriminate: the old body fails them with 4 models / 4 objects.
   - **Not fixed, on purpose**: `get_model` called outside a job (benchmark scripts) still cannot be protected by the job lock. They are single-threaded processes; the app path is the one that raced.

46. **Turbo Is the Default ASR Model (2026-10-26)**:
   - **Why switch**: the reported "wrong Hinglish" was assumed to be a model problem. A four-clip benchmark (fifa 54 s, fashion, kaashvi 879 s, legion 1327 s) says turbo is both more accurate and much cheaper: best word accuracy on fifa and fashion, and the most complete transcript on the long files (**kaashvi slice 189 words vs medium 146; legion 3819 vs 3512** — medium drops whole clauses), at **3–5×** the speed (fifa end to end **14.1 s / 3.85×**).
   - **`compute_type` stays `float16`**: `int8_float16` fixed turbo's dropped `uuid` but lost the English passage on the kaashvi slice, so it is not a clean win.
   - **`large-v3` rejected as default**: 4× slower and it still drops a clause on `traffic.mp4` in *both* compute types.
   - **The prompt stays**: the app's `SCRIPT_ANCHOR` + `STYLE_TEMPLATE` hint was tested by removal and degraded output badly (110 words only, Cyrillic garbage, `Levi's` → `लिवाइस`).
   - **Changed**: `large-v3-turbo` in [`server.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/server.py) (all three `selected_model` defaults), `hinglish_engine.generate_subtitles`, `static/app.js`. The server already rewrites the model pill's `active` class from the saved pref, so the UI stays consistent; `MODEL_DISPLAY_NAMES` already had turbo.

47. **The Recoverer Was Quietly Rewriting Correct Hindi (2026-10-26)**:
   - **The dominant defect was not the model**. [`hinglish_upgrades.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/hinglish_upgrades.py) `LoanwordRecoverer.merge_split_words` joined neighbouring tokens whenever the join looked like an English word, with no check on `protected`, `curated` or the inflection list. It also logged nothing (only `apply()` records decisions), which is why the first diagnosis wrongly called it dead weight.
   - **Danda was the second half of it**: U+0964/U+0965 sit *inside* the Devanagari block, so "keep only Devanagari" kept them and `'है।'` never matched the dictionary. `_deva_core()` now strips them, and all five core extractions use it.
   - **New merge rule**: joining the pieces must explain the audio **better than either piece alone** (`_best_distance`). The one genuine heal still passes — `रेवे`+`न्यू` scores 0.086 against 0.100 for either half. Measured wrong rewrites: **fifa 7 → 0**, kaashvi **32 → 0**, legion **33 → 1**.
   - **`sanitize_words()`** is step 0 of `words_to_cards`: strips U+FFFD and zero-width/bidi marks, drops words left empty. Whisper had emitted a lone U+FFFD as a 0.1 s token at 0.917 probability and it reached a burned caption.
   - **Verified**: fifa e2e `dekho ye stadium`, `bolta hai ki agar aap`, `white kapde se tight band diya`, `uske Levi's ka logo mein`, `bana ke daal diya`.

48. **Hinglish Naturalisation, and ज़/फ़ Are Not English (2026-10-26)**:
   - **The transliteration was a correct *spelling*, not spoken Hinglish**: ISO keeps every inherent vowel and long final, so `आपको` → `aapako`, `होना` → `honaa`, `पिछले` → `pichhhale`. [`transliteration.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/transliteration.py) now runs `_naturalise_hinglish()`: one medial schwa (rightmost, only after an open syllable — `चला` must not become `chla`), final `aa/ee/oo` shortened (`आ` alone excepted), `ie$`→`iye`, `aay`→`ay` **only after a consonant** (`आया` stays `aaya`), `men$`→`mein`, and a single-pass `ch`/`c` map that killed `pichhhale`.
   - **Flaps**: ड़/ढ़ are /ɽ/, written `d`/`dh`. ISO renders them `ṛ`, which the NFKD strip turned into plain `r` — the source of `kapare`, `karor`, `larakee`, `parhanaa`. `_flatten_flaps()` maps both encodings (U+095C/095D and stop+nukta, which is what ASR emits) to the retroflex stop first.
   - **The trailing-`ha` exemption was wrong**: it left `कुछ`→`kuchha`, `साथ`→`saatha`, `देख`→`dekha` — 40 words on four clips. `यह`/`वह` moved into the curated map instead.
   - **ज़/फ़ were treated as an English spelling signal**, which skipped `protected` and allowed the lenient threshold: `ज़रूर`→`server`, `ज़्यादा`→`shadow`, `चीज़`→`cheese`, `इज़त`→`issued`, `बॉलिवुड`→`believed`. They are ordinary Hindi consonants. Removed them; `accept_with_signal` **0.34 → 0.20** (every *correct* signal recovery measures ≤0.136, the wrong ones start at 0.15; **0.15 is too tight** — it costs `कॉलिटी`→quality and `टॉपलेट`→tablet). Measured on both clips: **11 wrong rewrites gone**, `जज़`→`jaz` (neutral), `नोटीस`→`notice` gained. Fallbacks are correct Hinglish: `zaroor`, `zyaada`, `cheez`.
   - **Corpus diff**: 1,144 distinct Devanagari words over 5 clips → **488 changed, 1,564 of 4,909 tokens (32%)**, every changed word reviewed, not averaged.
   - **What is left, and why it is the floor for this approach**: ~18% of single-token recoveries are still wrong (`पॉइंट`→paint, `रिव्यूज`→refuge, `नेक्स`→knicks, `टेस्टिंग`→tasting). These are homophones — phonetic distance cannot tell *next* from *knicks*. Fixing them needs context (an n-gram/LM rescoring pass), not another threshold.
   - **Verified**: **245 tests**, `node --check static/app.js` clean, real `h264_mf` burn of `uuid.mp4` (29 cards, **0** dialogue events with Devanagari left, no U+FFFD, 16 MB) — frames read `VO THODA SA LAGTA HAI`. Nothing committed; `launch_config.json` deliberately left out (it is user state).

49. **Four Transliteration Warts: Two Rules, Two Word Lists (2026-10-26)**:
   - **Anusvara is a rule, not a word**: ं/ँ before a consonant sound `n` in Hinglish, and `m` only before a labial (प फ ब भ म व). ISO writes both marks as `m` and the old cleanup only fixed the *last* letter, so every medial one leaked — `zimdagi`, `amdaaj`, `imsaam`, `ramgeen`, `mahamgaai`. `_assimilate_nasals()` now substitutes the nasal *consonant* before transliterating (`ज़िंदगी`→`ज़िन्दगी`), which leaves a genuine म alone: `कमरा`→`kamra`, `नमक`→`namak` still work. **202 distinct words / 824 running tokens** on the 5-clip corpus.
   - **`men$`→`mein` was over-firing**: it was unguarded, so `रमेन`→`ramein` and `अमेन`→`amein`. It now runs only when the *Devanagari* ends in ं/ँ (`उसमें`→`usmein`, `में`→`mein`, `रमेन`→`ramen`). One word on the corpus (`वुमेन`), but the old rule was wrong for every non-nasal `-men`.
   - **फ and व each spell two Hinglish sounds, so they need lists** — this is not tuning, it is missing information in the script. फ is /pʰ/ (`phir`, `phool`, `phal`) or /f/ (`saaf`, `kaafi`, `taraf`), and ASR drops the nukta that would tell them apart; `F_WORDS` holds the /f/ words, native /pʰ/ words stay `ph`. व is `w` in native words and `v` in English loans; `W_WORDS` holds `wala/wali/wale/walon`, `wo`, `wahi`, `wahin`, `wahaan`, `wapas`, `wajah`, `waqt`, `warna`, `wada`, `waah`, `sawaal`, `wagera`. A blanket `ph`→`f` or `v`→`w` was measured and rejected: it turns `phir`→`fir`, `phool`→`fool`, `video`→`wideo`, `divaais`→`diwaais`, `inwestigetars` (**187 v-changes, most of them loanwords**).
   - **Measured on the 5-clip corpus**, counted correctly (6,632 tokens / 2,087 distinct, one ASR run per clip — see entry 52): the anusvara + व + फ rules together change **150 distinct / 354 running tokens (5.3%)**. Of those running tokens, 198 contain anusvara/ँ, 123 contain व, 59 contain फ (buckets overlap; a word can carry two rules). At caption level **179 of 425 sentences (42.1%)** change; no regression found in the review — `मंत्री` even stops being `monthly`.
   - **Cost**: none measurable — cold transliteration over 2,150 distinct strings (all runs, including the 995 the shipped corpus never uses) goes **937 ms → 934 ms** (aksharamukha dominates; the per-word scan is O(len) and cached).
   - **Not in scope, on purpose**: English /f/ loanwords are a different class and were left alone here (`फोन`→`phon`, `फेमस`→`phemas`). They are not Persian /f/ words, so they do not belong in `F_WORDS`; see the next entry.
   - **Verified**: **308 tests** (63 new: `TestAnusvara`, `TestFAndW`, `TestNasalFinal`), real `large-v3-turbo` end-to-end on `uuid.mp4` (29 cards, `iska fayda`, `detail wale`, `wo itna achha`, `usmein` intact, 0 Devanagari left).

50. **English /f/ Loanwords Belong in COMMON_LOANWORDS (2026-10-26)**:
   - **The list is evidence, not intuition**: the five clips contain **51 distinct tokens with फ/फ़, 99 running** (corrected count, entry 52). The proposed shortlist (`फिल्म`, `फिल्में`, `फेल`, `फोकस`, `फ्री`, `फंड`, `फैक्ट`, `फैक्टर`) covers **zero** of them — those words never occur — while the real offenders were `फिर` 16, `काफी` 9, `साफ` 6, `ओफ` 3, `परफॉर्मेंस` 3, `फोन` 2, `फैमिली` 2.
   - **Selection rule**: the Devanagari spelling occurs ≥2 times, identifies exactly one English word, has no native homograph (`फुल` full vs `फूल` phool stay distinct). **39 entries added, 27 running tokens** on the corrected stream, 18 of the spellings actually occur — `phon`→`phone`, `phemas`→`famous`, `phul`→`full`, `aaph`→`off`, `laaiph`→`life`, `phaail`→`file`.
   - **Why not the recoverer**: `LoanwordRecoverer` returns `None` for every one of these because they sit in `protected` (they are frequent Hindi tokens). Loosening `protected` for फ words would re-open the `ज़रूर`→server class of rewrite; an exact table cannot.
   - **What a table cannot fix, and the real next step**: the *misspelled* long tail — ten ASR spellings of `performance` (`परफॉमेस`, `पर्फॉमैस`, `पर्फॉर्मेंस` …) — because each utterance invents its own spelling. That needs a recovery exemption for English-shaped source spellings, measured on the corpus, not another word.
   - **Verified**: **308 tests**, corpus diff **150 distinct / 354 running tokens (5.3%)** since the pre-`277823c` baseline (corrected count, entry 52), e2e `uuid.mp4` now reads `phir usne ek famous laain uthaya`.

51. **Delete-2 Skeleton Index: the Misspelled Tail Was One Family (2026-10-26)**:
   - **The bottleneck was candidate recall, not the distance gate**: `पर्फॉमेस` has skeleton `prpms`, `performance` has `prprmns`. The old index only covered *one* dropped consonant (`self.dele`), so `performance` was never a candidate and `promise` won at 0.155 (inside the 0.20 signal limit). Adding `self.dele2` (candidate has two extra consonants) is the whole fix.
   - **Measured before changing anything** (k1 vs k2 side by side over every distinct token of the chosen runs, 2,087): **0 new recoveries, 0 lost, 4 switched** — `पर्फॉमेस` ×5, `परफॉमेस` ×2, `पर्फॉमैस` ×1 (`promise`→`performance`), `पर्फॉमेज` ×1 (`performs`→`performance`). That is **9 running tokens, all in legion's `medium` run**, and **0 in the shipped `large-v3-turbo` run** — turbo writes the misspelled spellings zero times (only `परफॉर्मेंस` ×3, `पर्फॉर्मेंस` ×1, both already recovered correctly). So k=2 is recall insurance for a tail the shipped model does not currently produce; it is not what fixed today's captions. My first report of "18 running tokens / 10 of 1,115 cards" came from scanning the raw JSON, which holds two runs and repeats the text in `segments` (entry 52).
   - **The reverse direction was measured and rejected**: letting the *query* have two extra consonants turned `हाटब्रेकिंग` ('heartbreaking') into **`outbreak`** — one wrong word for zero gain. Keep recall one-directional: ASR drops consonants, it rarely invents them.
   - **Cost, measured on the path `recover()` actually takes** (not the raw index): 847 of the 2,150 candidate-reaching strings reach candidate lookup, scorings go **103,674 → 169,715 (+64%)**, cold recover **1.04 s → 2.17 s**. The raw `_candidates` count is not the right number — short/protected/curated tokens exit before candidates, so a raw max pool of 2,204 never gets scored.
   - **Pipeline check, not just `recover()`**: on the `medium` runs, `words_to_cards` gives 1,062 cards with **13 diffs** — 11 `performance` fixes plus a **card-split shift** (591→592 in legion; the word is 4 characters longer and splitting is a character budget). On the shipped runs: 1,127 cards, **0 diffs**.
   - **Verified**: **320 tests** (2 new, pinning both the recovery and the false-positive guard), full-pipeline diff above, 0 lost recoveries.

52. **Probed Loanwords + the Corpus Census Correction (2026-10-26)**:
   - **What the census actually is**: `asr_diag_out/*.json` holds **several ASR runs per clip** (`medium` *and* `large-v3-turbo`) and each run repeats its text in `segments`; `traffic_largev3.json` / `uuid_largev3.json` are byte-identical duplicates. Scanning the raw JSON counted every token ~3.6×. The honest denominator is **one run per clip — the one `pipeline_model` names** (else turbo → large-v3 → medium): **6,632 tokens / 2,087 distinct** across 6 clips (fashion 105, fifa 135, kaashvi 2,330, legion 3,819, traffic 106, uuid 137). Every count in entries 49–51 has been restated on it.
   - **What that changes**: no conclusion about *which* words are wrong survives differently, only their size. Entries 49–51 previously claimed 23,938 tokens, 1,434 changed running tokens (6.0%), 149 /f/ running tokens, and 18 `performance` rescues; the measured numbers are **6,632 tokens, 354 changed (5.3%), 27 /f/ running, 9 `performance` rescues in the medium run / 0 in the shipped one**.
   - **Where the seven entries came from**: the `hinglish-tts` repo (IndicF5 TTS — the *inverse* direction, Roman→Devanagari for synthesis) is not usable code here (Python ≤3.11 + CUDA torch + HF gating + research-only licence, and this box is 3.13.3 / torch 2.7.0+cpu / 6,141 MiB). Its 30-sentence eval set is a decent **probe**: run each Devanagari sentence through our shipped path and check the misses against our own corpus. It found `इवेंट`, `रिप्लाई`, `रिव्यू`, `रिव्यूज`, `मेसेज`, `क्लोज़`; the last is 0-occurrence and `क्लोज़` is a `clause`/`close` homograph, so it stayed out.
   - **Committed**: `इवेंट`→event, `नेक्स`→next, `रिप्लाई`→reply, `रिव्यू`→review, `रिव्यूज`→reviews (1 occurrence each, 5 cards), plus two coherence guards that change **no** card — `मेसेज` (3× in kaashvi's medium run only; twin of the covered `मैसेज`) and `फ़ोन` (never occurs; nukta twin of the covered `फोन`, which must not leak `fon`).
   - **Why a table, not the Zipf prior**: `रिव्यूज` *is* a perfect 0.067 tie (refuge/reviews) and a prior would fix it, but `नेक्स` is not a tie at all — `next` scores 0.210 against `knicks` 0.037, past both the 0.07 plain and 0.20 signal gates, so a prior inside ε=0.03 would pick `knox` and stay wrong. An exact entry is deterministic and cannot re-rank a word nobody inspected.
   - **Verified**: **329 tests**, pipeline diff over the shipped runs **1,127 cards compared, 5 changed**, word level **5 distinct / 5 running of 6,632**, recoverer bypassed for all seven (`curated`).

53. **One POSITION Slider, and a 9:16 Safe-Zone Guide (2026-10-26)**:
   - **The POSITION slider only wrote `margin_v`**: kinetic presets read `anchor_y`, so Honey Punch and Recess ignored it forever ("can't change the position"). One % slider now writes `anchor_y` for `motion: "word-pop"` and `margin_v` for classic styles, converted through the same aspect profile the burn uses (`9:16 1920/1.0`, `16:9 1080/0.375`, `1:1 1080/0.46`). Kinetic 22 → 40 moved the overlay to 40% of the *picture* and the burn emitted `\pos(540,768)` for 1920.
   - **The classic half of the slider was dead above ~53%**: `resolve_style` clamped `margin_v` at 900. Raised to **1600**, so 9:16 reaches **16.7%** from the top (16:9 **44.4%**, 1:1 **31.9%**). `margin_v=1600` burns with ink at **14.3–16.6%**, not clipped. The slider min/max is now set per style+aspect, and `updateVideoOrientation` re-syncs it: measured **16.7 → 44.4** after swapping a 540x960 clip for a 640x360 one.
   - **Live and burn disagreed because live measured the stage**: the stage also holds the ~54 px control bar, and classic bottom used a `margin_v*0.28` guess. Both now come from `videoFrameRect()` (the video's own box, padding-box coords). Honey Punch `anchor_y=40`: libass preview ink **41.9%**, real 540x960 burn **41.4%**. Vox `margin_v=170` → 53.1 px above the picture bottom, matching the burn's 53.1.
   - **Recess followed neither**: its centre was pinned to the video midline. `recessCentreTop(em, style, state)` now puts the `\an5` centre on `anchor_y` (minus the 0.035 em cap lift; title phrases −4.5%). `anchor_y=35`: preview and burn ink centre both **35.8%**.
   - **Two smaller live/burn mismatches**: the kinetic right layout margin was 8% portrait vs the burn's 20% (`_kinetic_event_anchor`, 80% width) → flat 20%; the live anchor clamp `6..80` is gone, so the slider can reach the pixel the burn draws.
   - **The 9:16 guide** (portrait only, "9:16" button in the player) marks the top **10%**, bottom **25%** and right **15%** of the *picture*, with a collision warning read from the painted words (hidden kinetic words skipped). The action rail is bounded between the top and bottom rails, so a top-right or bottom-right caption is not reported twice. Constants, not measurements — the bands are labelled.
   - **The overlay box is the picture, not the stage**: portrait pins `left/right` to the picture (+10 px classic, +0 kinetic); when the picture fills the stage width it clears the pins so the stylesheet's landscape 20 px inset survives (verified on 640x360).
   - **Layout re-anchoring**: a `ResizeObserver` on the stage replaces the window resize hook (it also catches the editor-panel drag), and a viewport resize re-anchored the overlay to picture+10 px. No console errors or observer loops.
   - **Deleted**: the pre-existing dead legacy style panel (`#styleFont` … `#styleBox` do not exist in `index.html`; `readStyleEditor`/`queueStyleSave`/`styleSaveTimer` came with it).
   - **Deliberately not done**: the burn is not auto-inset to the 15% rail (it would silently change existing reel exports; the guide warns instead), and the live kinetic wrap width (+26 portrait) still differs from ASS (+18).
   - **Verified**: **332 tests**, `node --check static/app.js`, four browser sweeps (kinetic, classic, Recess, guide, aspect swap), and three real `h264_mf` burns measured above.

54. **2026 Safe-Zone Calibration, Auto-On for Portrait, & Sweet-Spot Placement (2026-10-26)**:
   - **Discoverability fix**: The safe-zone guide previously required clicking an ambiguous `9:16` button that initialized to `false` and looked like a static aspect ratio tag. Button is now clearly labeled `🛡️ SAFE ZONE` with active golden highlighting, and automatically initializes to `true` whenever a vertical 9:16 clip (`video-portrait`) is loaded.
   - **Calibrated to 2026 platform reality (BlitzCut guide)**: Dead space percentages in `app.js` and `components.css` were updated from rough guesses (10% / 25% / 15%) to BlitzCut cross-platform universal safe zone measurements:
     - `SAFE_ZONE_TOP = 11.5%` (~220 px on 1080×1920, clears Instagram/TikTok search headers and following tabs).
     - `SAFE_ZONE_BOTTOM = 23.5%` (~450 px, clears Reels' late-2025 expanded audio attribution bar and TikTok sound row).
     - `SAFE_ZONE_RIGHT = 15.2%` (~164 px, clears TikTok's Jan 2026 expanded action rail with the new "Add to Playlist" button).
   - **One-click "Sweet Spot" positioning snap**: Added 4 quick preset chips under the POSITION slider (`Top 20%`, `Center 50%`, `Sweet Spot 68%`, `Bottom 80%`). Clicking `Sweet Spot 68%` snaps both kinetic (`anchor_y`) and classic (`margin_v`) into the optimal lower-middle third ($Y=1200\text{--}1550\text{px}$) clearing speaker faces and bottom chrome.
   - **Verified**: **332 pytest tests pass**, `node hinglish_subtitles/tests/js/safe_zone_test.js` 100% green with calibrated constants, clean syntax via `node --check`.

55. **Uncluttered Floating Safe-Zone Toolbar & Multi-Platform Presets (2026-10-26)**:
   - **Clutter Elimination**: Removed the wide text button from `.custom-media-controls`. The playback transport bar (play, timecode, scrubber, volume slider, fullscreen) now has full breathing room and zero text truncation.
   - **Option 1 Floating Stage Toolbar**: Added `#stageSafePill` inside `#videoStage` at the top-right corner (`top: 10px; right: 10px; z-index: 15`). Styled with frosted-glass backdrop blur (`rgba(14, 18, 27, 0.84)`, `backdrop-filter: blur(12px)`), high contrast mono chips, and smooth transitions. Only displayed on portrait video.
   - **Platform Presets (TikTok Removed per User Direction)**: Added 1-click platform switching chips:
     - `ALL` (Universal Cross-Platform: Top 11.5%, Bottom 23.5%, Right 15.2%).
     - `REELS` (Instagram Reels: Top 11.5%, Bottom 23.4% [450 px audio bar], Right 11.1%).
     - `SHORTS` (YouTube Shorts: Top 6.3%, Bottom 15.6%, Right 4.4% [48 px rail]).
     - `OFF` (Disables guides and collision warnings).
   - **Dynamic Collision & Geometry**: `safeZoneCollisions()` and band styles dynamically read from `SAFE_ZONE_PRESETS[currentSafeZonePreset]`, with collision alerts adapting instantly to the active platform's margins.
   - **Verified**: **332 pytest tests pass**, `node hinglish_subtitles/tests/js/safe_zone_test.js` 100% green with platform preset checks and Shorts tolerance tests, clean syntax via `node --check`.

56. **Safe-Zone Pill Verified in a Real Browser + Narrow-Rail Label (2026-10-26)**:
   - **Playwright run on the real app** (`540x960` portrait clip, viewport `1440x1000`): pill visible on portrait at 197x27 px, 12 px inside the stage border (10 px + the 2 px border), above the transport bar; hidden on the `640x360` landscape clip; no console errors.
   - **Preset math measured from the DOM bands, not just the constants**: ALL 11.5 / 23.5 / 15.2 %, REELS 11.5 / 23.4 / 11.1 %, SHORTS 6.3 / 15.6 / 4.4 % of the picture box; the guide stays pinned to the video frame, not the stage.
   - **User-off is honest**: `OFF` hides the bands and the collision warning, the pill stays reachable, and loading a landscape clip then a portrait clip does **not** resurrect the guide (`currentSafeZonePreset === "off"` wins over the auto-enable write).
   - **Fixed**: on SHORTS the 4.4 % rail is 23 px wide, so the 8 px "ACTION RAIL" label spilled left over the picture; `.video-safe-zones.is-narrow` now sets it `writing-mode: vertical-rl`, toggled when `preset.right < 8`.
   - **Fixed**: chip tooltips now quote the measured percentages instead of the blog's "900x1400 universal" claim, which contradicts its own 450 px Reels figure. Chips also expose `aria-pressed`.
   - **Verified**: 332 pytest, `safe_zone_test.js` green (6 new preset/band/narrow-label checks), `verify_safe_pill.py` 34/34 browser checks.

57. **Public GitHub Release & GNU AGPLv3 Licensing (2026-10-28)**:
   - **Repository Published**: Pushed to GitHub at `https://github.com/Gauji-Boy/hinglish_subtitles` on branch `main`.
   - **License Configured**: Added GNU Affero General Public License v3.0 (`LICENSE`), providing strong copyleft protection against closed-source proprietary forks while keeping code open for the community.
   - **Disclaimers**: Added third-party downloader notice (`yt-dlp` Unlicense notice + Fair Use guidance) to `README.md`.

58. **PyPI Package Specification & Build (2026-10-28)**:
   - **Modern Packaging Architecture**: Built standard `pyproject.toml` (PEP 517/518/621) targeting PyPI distribution under name `hinglish-subtitles`. Configured with SPDX license expression `AGPL-3.0-or-later`, complete metadata, authors, dependencies, and classifiers.
   - **Namespace & Asset Preservation**: Setuptools packages under `hinglish_subtitles` namespace, preserving root files for backward compatibility with `HinglishSubtitles.exe` and `run_app.bat`. Configured `MANIFEST.in` and `[tool.setuptools.package-data]` so all UI assets (`static/` HTML/CSS/JS/icons) and `launch_config.json` are bundled into the distribution wheel.
   - **Entry Points**: Wrapped `server.py` startup logic in `def main():` and registered CLI console script `hinglish-subtitles = "hinglish_subtitles.server:main"`, plus `__main__.py` enabling `python -m hinglish_subtitles`. Added automatic `sys.path` registration for reliable resolution of sibling modules in both local dev and installed wheel environments.
   - **Build Validation**: Built with `uv build` -> produced `hinglish_subtitles-1.0.0.tar.gz` (6.78 MB) and `hinglish_subtitles-1.0.0-py3-none-any.whl` (6.75 MB).
   - **Verification**: **332/332 pytest pass**, all JS safe zone tests pass. Build artifacts (`dist/`, `build/`, `*.egg-info/`) added to `.gitignore`.
