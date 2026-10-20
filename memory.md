# Project Memory & Long-Term Context

> **Workspace:** `c:\Users\susha\Documents\General` & `c:\Users\susha\Documents\General\hinglish_subtitles`  
> **Last Updated:** 2026-10-17  
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
  - **Industrial Hybrid (Default)**: Industrial Neo-Brutalist design language (matching `skills_library.html` tokens: strict 0px border-radius, 2px solid borders, `#000000` / `#ffffff` hard drop shadows, `#facc15` brand yellow, `#38bdf8` cyan accents, dark `#0c0d10` canvas).
  - **Sleek Bento Cyber (`[data-theme="sleek-bento"]`)**: Smooth squircle bento cards (`22px` radius), full capsule geometry (`border-radius: 9999px`), pitch black `#07080a` canvas with elevated charcoal `#131419` cards, vivid neon lime (`#bef264`) and solar orange (`#fb923c`) accents, soft ambient occlusion glow shadows, and preserved tactile press physics. Switchable in top navbar and persisted in `localStorage`.
  - **CTA & Hover Integrity**: The primary execution button (`.btn-primary`) must NEVER turn pure white on hover; it retains its signature brand yellow with a subtle electric brightness lift (`filter: brightness(1.08)`). In empty state, it remains in a dimmed standby state (`.is-standby`) with a status chip until media is staged.
  - **Hero Meta Row & Grounded Baseline**: The duplicate hero hardware pill was removed (the top sticky navbar's compact GPU pill already displays the active GPU and CUDA fp16 status), leaving the hero meta row clean with model info and zero-hallucinations. Controls card columns stretch with `align-items: stretch` and `topic-hint-group` to ground the left column flush with the right banner.
  - **Branding & Taskbar Identity**: Windows taskbar icon is set via explicit `AppUserModelID` (`antigravity.hinglishsubtitles.desktop.v2`) and `app_icon.ico` passed to `webview.start` / PySide6 `setWindowIcon()`. Web UI includes `favicon.ico` and a custom inline `.brand-logo` (`<svg class="brand-logo">`) in the top sticky navigation bar that dynamically inherits theme accents.
  - **Desktop Application Selection Ergonomics**: Chrome elements (`body`, `nav`, `.hero`, `.ribbon`, `.tile`, `.controls-card`, `.pill`, `.badge`, `.dropzone`, `.action-bar`) lock `user-select: none;` and `server.py` sets `text_select=False` to prevent browser drag-highlighting. Content areas (`input`, `textarea`, `.card-hinglish-box`, `.card-orig-box`, `.caption-text`, `.log-line`) strictly retain `user-select: text !important;`.
  - **Tile & Icon Glyph Shadow Polarity**: The outer language tile cards (`.tile`, `.tile.active`, `.tile:hover`, `.tile:active`) strictly retain hard offset drop shadows matching their respective icon accent color (`var(--c, var(--yellow))` / `var(--c, var(--paper))`). The inner icon glyph badge (`.glyph`, `.tile:hover .glyph`, `.tile.active .glyph`) carries a crisp, pure white `#ffffff` drop shadow in dark modes (`box-shadow: 3px 3px 0 #ffffff;`, `1px 1px 0 #ffffff` when hovered/active) and pure black `#000000` drop shadow in light mode (`box-shadow: 3px 3px 0 #000000;`, `1px 1px 0 #000000` when hovered/active), providing high-contrast punch to the icons while keeping card shadows harmonized with their category colors.
  - **Subtitle Export & Download Pipeline**: In standalone desktop window mode, pywebview runs with `webview.settings["ALLOW_DOWNLOADS"] = True` and binds a `DesktopAPI` (`window.pywebview.api.save_subtitle_file`) that launches the native Windows OS "Save As" file dialog (`webview.FileDialog.SAVE`) directly saving UTF-8 subtitle/text files. In browser mode, falls back to `POST /api/download/file` with `Content-Disposition: attachment` or delayed client-side Blob revocation (60s) to prevent WebView2/Chromium stream aborts. Floating download bar has `z-index: 95;` and provides dynamic `✓ SAVED!` button feedback.
  - **Karaoke Animated Subtitles (.ASS) & Word Timestamps (Phase 1)**: Integrated word-level animated subtitles. `karaoke_ass.py` outputs Advanced SubStation Alpha (`.ass` v4.00+) with `{\k<centiseconds>}` highlight tags for active words (Alex Hormozi / TikTok style with yellow fill `#FFC700`, black outline, and bottom safe zone margins). Engine endpoints (`generate_subtitles`, `generate_english_subtitles`, and `/api/export/ass`) attach individual word token timestamps `[{start, end, word, hinglish}]` to every segment, enabling both direct `.ass` karaoke exports and structured word timelines. Supported in the floating export bar via `🎤 KARAOKE (.ASS)` download action.
  - **Direct Video Burning Engine (Phase 2)**: Added high-speed local subtitle burn-in via FFmpeg (`video_burner.py`). Automatically utilizes Windows MediaFoundation H.264 hardware encoding (`h264_mf`) and libass filter with working directory path isolation to eliminate Windows colon/backslash path parsing issues. Exposes `POST /api/export/burn-video` and direct `🔥 BURN VIDEO (.MP4)` button in the floating export bar, producing ready-to-publish MP4 videos with permanently burned styled subtitles.
  - **Speaker Diarization Engine (Phase 3)**: Lightweight acoustic turn and multi-speaker diarizer (`diarization.py`) using 28-dimensional spectral features (13 MFCCs + spectral centroid mean & variance) with distance-thresholded Agglomerative Hierarchical Clustering. Requires 0 external downloads or Hugging Face tokens. Seamlessly integrates into `hinglish_engine.py`, `hindi_to_english_engine.py`, `server.py`, and the web UI with a toggle in the Settings Drawer and dynamic `#Speaker N` badges on subtitle cards.
  - **Top Navigation Bar & Floating Bottom Search Dock**: Top bar follows a clean 2-zone workbench layout (Brand identity with monospace `v2.5` badge on the left; compact single-line GPU pill, live terminal button, and unified segmented theme cluster on the right). Subtitle search is contextually consolidated into the center of the fixed bottom floating export dock (`#floatingSearchInput`), eliminating duplicate top and toolbar search inputs, and focused automatically via global <kbd>/</kbd> hotkey. The bottom bar includes a real-time subtitle match telemetry pill (`#floatingMatchPill` displaying `🎯 X / Y MATCHES`) and an instant `📋 COPY ALL` clipboard button (`#floatingCopyAllBtn`).
  - **Empty State Workbench (Pattern B: 2-Column Split Cockpit)**: Positioned below `.action-bar` to eliminate empty screen space before a file is loaded. Features a Web Video Link Importer powered by `yt-dlp` (`POST /api/import-url` and `/api/media/{filename}`) for YouTube, Instagram Reels, TikTok, and direct links, alongside a Recent Transcriptions & 1-Click Benchmark Reel shelf (`static/samples/traffic.mp4` and `genius_ad.mp4`). Both columns feature individual `✕ HIDE` buttons and persistent restore chips (`#workbenchRestoreBar`) allowing users to hide whichever feature they don't need while retaining a balanced responsive layout.
    - **Web Video Importer Media & Quality Controls (Option 1)**: Integrated two-tier Segmented Media Switcher (`🎬 Video + Audio` vs `🎵 Audio Only (Fastest ⚡)`) paired with dynamic Quality Dropdown (Video: `Source Best`, `720p Fast HD`, `480p`; Audio: `320k High`, `128k Standard`, `64k Speech/Fast`). Audio-only downloads download in ~2s and automatically activate the frontend Web Audio frequency visualizer (`renderAudioVisualizer()`). User selections persist across sessions in `localStorage`.
  - **Spoken Language Ribbon (5-Tile Architecture with Hindi ➔ English)**: Expanded `.ribbon` to 5 columns (`grid-template-columns: repeat(5, 1fr)`). Added 5th tile for **Hindi ➔ English** (`data-lang="hi-en"`, Solar Orange `--orange: #fb923c`, translation icon `文 ➔ A`). Directly triggers Whisper's native GPU `task="translate"` (with `language="hi"`), translating spoken Hindi audio into natural English captions with exact millisecond word timestamps at 14x–18x real-time speed on the RTX 4050 GPU. Downstream DP chunker chunks the English words into 1–2 line subtitle cards; UI updates card badges to `TRANSLATED ENGLISH` and export buttons to `DOWNLOAD ENGLISH SRT`. Selection is persisted across sessions in `launch_config.json`.
    - **Hero Layout & Tile Width Optimization**: Rebalanced the `.hero` container grid from `1.2fr 1fr` to `minmax(360px, 440px) 1fr`, giving the right-side ribbon over 850px+ of width (~155px per tile) and preventing tile cramming. Added `white-space: nowrap;` to `.tile` titles and descriptions, keeping labels on a single line with generous breathing room. Added `@media (max-width: 1120px)` breakpoint to stack gracefully without squeezing on compact screens.
  - **Slide-Over Settings Drawer (Option 1 Architecture)**: Secondary engine controls (Whisper/ASR model pills, CUDA vs CPU acceleration selectors, caption pacing profiles, and topic/brand vocabulary hotwords) have been relocated out of the main page flow into a slide-over inspector drawer (`#settingsDrawer`).
    - **Trigger**: Click `⚙️ SETTINGS` button (`#openSettingsBtn`) in top navbar, click the active GPU badge (`#hwBadge`), or press the global <kbd>,</kbd> (comma) hotkey.
    - **Dismiss**: Press <kbd>Esc</kbd>, click `#settingsDrawerCloseBtn`, click the blurred backdrop overlay (`#settingsDrawerOverlay`), or click `#saveAndCloseSettingsBtn`.
    - **Clean Main Canvas**: Eliminates ~300px of vertical clutter between the hero ribbon and upload dropzone. The landing screen flows directly: Top Navbar ➔ Spoken Language Ribbon ➔ Upload Dropzone / Cockpit!
    - **Ergonomics**: Media player and subtitle grid remain 100% visible in the background when configuring settings, allowing rapid iterative adjustments.
    - **Dynamic Pinned Controls & Permanent Main Window Topic Hints**:
      - **Topic / Brand Vocabulary Hints** is kept permanently in the main window directly above the dropzone so creators can type hotwords and brand names without opening settings; completely removed from the Settings Drawer.
      - Each major setting in the Settings Drawer (ASR Model Switcher, Hardware Acceleration, Caption Pacing) includes a dedicated `[ 📌 PIN TO MAIN ]` switch (`#pinModelSwitch`, `#pinHwSwitch`, `#pinPacingSwitch`).
      - Pinned controls render in the main window using the familiar **previous design layout** (`.controls-wrap` with `.controls-card` between the Language Ribbon and the Dropzone).
      - **Dynamic Layout Adaptation**:
        - **0 Pinned**: Main controls card renders as a sleek, full-width Topic Hints card (`.controls-card.cols-1`).
        - **Model Switcher Pinned**: Forms the exact previous 2-column layout (`.controls-card.cols-2`) with Topic Hints on the left and Model Switcher on the right.
        - **All Pinned**: Left column has Hardware + Pacing + Topic Hints; Right column has Model Switcher (exact original layout!).
      - **Bidirectional Synchronization**: Pill selections and cache/download statuses sync in real-time between the drawer and main window cards.
    - **Workbench Modules Visibility in Settings Drawer (Section 4)**:
      - Main window cards (`#workbenchImporterCard` and `#workbenchRecentsCard`) remain 100% clean with zero clutter buttons on their headers.
      - In the Settings Drawer, dedicated `[ SHOW ]` and `[ ✕ HIDE ]` toggle buttons allow hiding or showing either the Web Video Importer (`#settingsShowImporterBtn`, `#settingsHideImporterBtn`) or Recent Files & Samples (`#settingsShowRecentsBtn`, `#settingsHideRecentsBtn`).
      - When one module is hidden, the remaining module expands to 100% full width (`.full-width`). When both are hidden, the empty-state workbench collapses cleanly. Preferences persist across sessions in `localStorage`.
- **Proactive HTML Visualizations Directive:** Whenever discussing, designing, or altering any UI layouts or components, the agent must **always proactively create an interactive standalone HTML visualization file** (e.g. `c:\Users\susha\Documents\General\<name>_options.html`) with light/dark themes, clickable tabs/options, and side-by-side previews without waiting for the user to ask. Interactive prototype created: [`topic_hints_and_settings_visibility_options.html`](file:///c:/Users/susha/Documents/General/topic_hints_and_settings_visibility_options.html).
- **Sync Protocol:** Whenever skills in `C:\Users\susha\.gemini\config\skills` are changed, automatically run `python C:\Users\susha\Documents\General\sync_skills_library.py`.

---

## 2. Hardware Environment & Verified Telemetry

- **Primary GPU:** NVIDIA GeForce RTX 4050 Laptop GPU (6,141 MiB VRAM).
- **Acceleration Stack:** CUDA `float16` via `faster-whisper` (CTranslate2).
- **Measured Speeds & VRAM (Measured 2026-10-17)**:
  - `large-v3-turbo/float16/beam5`: **3.2s–4.1s** (Genius Ad & Traffic). Real-time factor: **14x–18x**. Peak VRAM: **3,850 MB**. Beam size 5 completely eliminates word freezes on fast speech over background music without increasing VRAM over beam 2.
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
       │
       ▼
[FFmpeg Audio Extraction] (extract_audio_numpy: 16kHz mono float32 PCM via pipe, CREATE_NO_WINDOW)
       │  └── emits [extract] telemetry to console_bus
       ▼
[Faster-Whisper Engine / Multi-ASR Pipeline]
       │  └── emits [whisper], [conformer], [sravaani] telemetry to console_bus
  ├── condition_on_previous_text=False (eliminates cascading repetition/hallucination loops)
  ├── vad_filter=True (Silero VAD threshold 400ms: prevents cutting mid-word)
  ├── initial_prompt: SCRIPT_ANCHOR + STYLE_TEMPLATE (Devanagari format anchor)
  └── hotwords: User topic hints + brands injected into every 30s window
       │
       ▼
[Flat Word-Level Timestamps] (word_timestamps=True)
       │
       ▼
[Cross-Window Word Seam Stitching] (stitches 'reve' + 'nu' across 30s boundaries)
       │
       ▼
[Global Unification & Cleaning]
  ├── unify_variants(): Clusters phonetic spelling variants (e.g. 'Detol' -> 'Dettol')
  ├── LoanwordRecoverer: CMUdict + phonetic map recovers loanwords (e.g. 'वीडियो' -> 'video')
  └── normalize_case(): Rule-based casing (proper nouns preserved, mid-sentence common words lowercased)
       │
       ▼
[Semantic DP Chunker] (semantic_chunk() + pad_display_times())
  ├── Short-Form Mode (Reels/Shorts): 1.0s–2.8s, 3–7 words, max 42 chars (prevents face blockage)
  └── Long-Form Mode (YouTube/16:9): 2.0s–5.0s, 8–14 words, max 76 chars (natural sentence clauses)
       │
       ▼
[Phonetic Transliteration] (Aksharamukha Devanagari -> Latin Hinglish)
       │
       ▼
[Subtitles & Real-Time Sync] (SRT, VTT, TXT, Card Grid + On-Video Reel Overlay)
```

---

## 4. Key Components & Implementation Details

| Component | File | Responsibilities |
|---|---|---|
| **FastAPI Backend** | [`server.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/server.py) | Endpoints: `/api/hardware`, `/api/models`, `/api/download_model`, `/api/transcribe` (supports `video`, `language`, `model_size`, `device`, `topic_hint`, `pacing`). Serves `/static`. |
| **Pipeline Core** | [`hinglish_engine.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/hinglish_engine.py) | `generate_subtitles()`, `extract_audio_numpy()`, hardware probe, SRT formatter. |
| **Translation Engine** | [`hindi_to_english_engine.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/hindi_to_english_engine.py) | Dedicated Hindi ➔ English translation engine (`generate_english_subtitles()`). Pure English prompt, no transliteration or loanword pollution. |
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
   - Dedicated Audio Mode card (680px × 200px) with animated `#facc15` equalizer visualizer.
   - Captions sync over the audio card in real time during playback.
4. **Caption Pacing & Format Selector**:
   - `📱 SHORT-FORM (REELS / SHORTS)`: 1.0s–2.8s card duration, 3–7 words, max 42 chars.
   - `📺 LONG-FORM (YOUTUBE / 16:9)`: 2.0s–5.0s card duration, 8–14 words, max 76 chars.
5. **Long Audio Reliability & UX**:
   - Progress bar features a live elapsed seconds ticker so users know GPU is active on 10–20 minute files.
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
   - Kept the clean Neo-Brutalist `#toggleGridBtn` (`▼ HIDE CARDS` / `▶ SHOW CARDS`) in the toolbar (removed the redundant `<select>` dropdown as requested).
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
   - Added `IndicConformer (AI4Bharat 600M)` button to `static/index.html` with dynamic `✓ CACHED ON DISK` status check.
   - Wired directly into `generate_subtitles` dispatch pipeline with automatic fallback and caching.
   - All 18 automated unit tests passing in `tests/test_upgrades.py`.
14. **ARTPARK-IISc SraVaani 1.0 (430M) Local Integration**:
   - Installed at `D:\Hinglish_subtitles\SraVaani-1.0` (908 MB model weights + tokenizer).
   - Installed `sentencepiece` and verified word-level timestamp generation on real audio.
   - Added `SraVaani 1.0 (ARTPARK-IISc)` button to `static/index.html` with dynamic `✓ CACHED ON DISK` status check.
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

22. **Dedicated Hindi ➔ English Translation Engine (`hindi_to_english_engine.py`)**:
   - **Root Cause of Hinglish-in-Translation Bug**: Whisper's `initial_prompt` was polluted with Devanagari Hindi text (`SCRIPT_ANCHOR` / `STYLE_TEMPLATE`), causing Whisper's decoder to ignore `task="translate"` and generate Devanagari Hindi, which then was transliterated into Latin Hinglish (`TUMHARE LIYE TRAFFIC...`).
   - **Root Cause of Large-V3-Turbo Outputting Hindi**: OpenAI distilled `whisper-large-v3-turbo` down to a 4-layer decoder specifically optimized for transcription. Its translation head was pruned during distillation, causing `task="translate"` to collapse back to source-language (Devanagari Hindi) transcription regardless of prompts. In contrast, full multilingual models (`large-v3`, `medium`, `small`) fully support cross-lingual translation.
   - **Fix Implemented**: 
     1. Created dedicated engine [`hindi_to_english_engine.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/hindi_to_english_engine.py) with English primer prompt (`"English subtitles with natural grammar, proper sentence capitalization, and punctuation."`).
     2. In `hindi_to_english_engine.py`: If `model_size == "large-v3-turbo"`, it automatically routes to the full cached `large-v3` on D: drive for studio-grade English translation. Acoustic-only models (`indic-conformer`, `sravaani`, `sensevoice`) route to `medium`.
     3. In `static/app.js`: When `selectedLanguage === "hi-en"` and `selectedModel === "large-v3-turbo"`, the status bar informs the user: `⚡ AUTO-ROUTED TO LARGE-V3: Large-v3-Turbo is distilled for transcription only. The translation pipeline automatically uses full Large-V3 (Studio) for English translation.`
   - In `server.py`:
     - Dispatches `if language == "hi-en": from hindi_to_english_engine import generate_english_subtitles`.
   - In `static/app.js`:
     - Dynamic button label updates: `#downloadHinglishBtn` displays `📥 DOWNLOAD ENGLISH SRT`, `#captionToggleGroup` displays `ENGLISH`, and `#generateBtn` displays `TRANSLATE TO ENGLISH`.
   - Validated end-to-end on both [`traffic.mp4`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/static/samples/traffic.mp4) and [`genius_ad.mp4`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/static/samples/genius_ad.mp4) producing natural English subtitles (`"How did an ad save Dettol while drowning? See, the market comes with a saebolon and the disadvantage of Dettol is that when we put Dettol on it, it gets a little burnt."`).
   - All 37 automated unit tests passing in `tests/test_upgrades.py`.

23. **Contextual Model Visibility Filtering (Auto-Hiding Incompatible Models)**:
   - **User Request**: Automatically hide models that do not support English / English translation when in English-oriented modes.
   - **Implementation**:
     - `ENGLISH_TRANSLATION_MODELS = ["small", "medium", "large-v3"]`
     - `ENGLISH_ASR_MODELS = ["small", "medium", "large-v3-turbo", "large-v3", "sensevoice-small"]`
     - When `Hindi ➔ English` (`selectedLanguage === "hi-en"`) is selected:
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
   - **User Reported Issue**: Selecting `Hindi ➔ English` (`data-lang="hi-en"`) and restarting the app reset back to pure Hindi/Mixed option with all hidden models unhidden.
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
   - Added `POST /api/export/ass` in `server.py` and `🎤 KARAOKE (.ASS)` export action in the UI.
   - 5 dedicated unit tests in `tests/test_karaoke_ass.py`.

27. **Direct Video Burning Engine (Phase 2)**:
   - Built [`video_burner.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/video_burner.py) wrapping local FFmpeg with Windows MediaFoundation hardware encoder (`h264_mf`) and relative path execution to prevent Windows colon/backslash escaping bugs in `libass`.
   - Exposes `POST /api/export/burn-video` in `server.py` streaming encoded MP4 directly to the client.
   - Added `🔥 BURN VIDEO (.MP4)` in the floating export bar with live indeterminate pulse progress.
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
   - **Test Suite**: **55/55 tests passing** in 9.68s. Git commits `d4ac5a6`, `0ba64c1`, and `d92f828`.
