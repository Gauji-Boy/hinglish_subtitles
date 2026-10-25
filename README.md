# 🎬 Hinglish Subtitle Generator (GPU Accelerated)

A high-performance tool that generates **Hinglish subtitles** (Hindi written in English alphabet / Romanized Hindi) for videos with **NVIDIA GPU Acceleration**.

Supports:
- **Mixed / Code-Switched Speech** (Hindi + English in the same video or sentence)
- **Pure Hindi Speech** (converted to natural Latin-script Hinglish)
- **Pure English Speech** (preserved as clean English subtitles)

---

## ⚡ Key Highlights
- **🚀 GPU Accelerated (CUDA)**: Up to **25x real-time speed** using NVIDIA RTX GPUs (Tensor Cores in `float16`).
- **100% Offline & Free**: Powered by local `faster-whisper` and `aksharamukha`. Zero cloud costs or API keys.
- **Zero Hallucination / No LLM Required**: Deterministic phonetic mapping guarantees speech-to-text timing and synchronization never drift.
- **Smart Loanword & Schwa Normalization**: Automatically normalizes tech loanwords (`video`, `subscribe`, `channel`, `comment`, `like`) and deletes Sanskrit-style trailing schwas (`hama` → `hum`, `bata` → `baat`).
- **Supports All Model Sizes**: `small`, `medium`, **`large-v3-turbo`**, and **`large-v3`**.
- **Two Ways to Use**: Modern desktop app or direct command-line interface.

---

## 🚀 Quickstart

**Prerequisites:** Python 3.13, FFmpeg on `PATH`, then `pip install -r requirements.txt`.

### 1. Launch the Standalone Desktop Application
Double-click `run_app.bat` or run:
```bash
python server.py
```
It will automatically launch as a **standalone desktop window** (no browser tabs, no URL bar, independent taskbar icon) at `1380x880` resolution.

1. **Hardware Badge**: Verifies your detected NVIDIA GPU in the sidebar.
2. **Upload your video** (`.mp4`, `.mov`, `.mkv`, etc.).
3. **Select language mode**:
   - `Mixed (Hindi + English)` *(Recommended for Indian YouTube, reels, podcasts)*
   - `Hindi` *(For pure Hindi audio)*
   - `English` *(For pure English audio)*
   - `Auto-Detect`
4. Click **"Generate Hinglish Subtitles"**.
5. Preview synchronized subtitles and click **"Download Hinglish SRT"**.

---

### 2. Command-Line Usage (CLI)
Generate subtitles directly from the terminal with full hardware control:

```bash
# Auto-detects NVIDIA GPU (CUDA float16)
python hinglish_engine.py input_video.mp4

# High accuracy large-v3 on GPU
python hinglish_engine.py input_video.mp4 -m large-v3 -d cuda

# Force CPU execution (safe mode)
python hinglish_engine.py input_video.mp4 -d cpu -m small
```

#### CLI Flags:
| Flag | Description | Options | Default |
|---|---|---|---|
| `video_path` | Input video file path | Any video format | Required |
| `-o, --output` | Output `.srt` file path | Path string | `<video_name>_hinglish.srt` |
| `-d, --device` | Acceleration device | `auto`, `cuda`, `cpu` | `auto` |
| `-m, --model` | Whisper model size | `small`, `medium`, `large-v3-turbo`, `large-v3` | `small` |
| `-l, --lang` | Language mode | `mixed`, `hi`, `en`, `auto` | `mixed` |
| `-c, --compute` | Precision type | `float16`, `int8_float16`, `int8` | Auto |

---

## 🎨 Caption Styles & Burn-In

Styled karaoke captions can be exported as `.ass` or burned directly into the video. Word timing is unchanged; a style controls font, colours, outline/box, and position, plus an optional word-by-word motion.

### Built-in presets
| Preset | Look |
|---|---|
| **Hormozi Kinetic** | Impact, uppercase, yellow spoken-word highlight |
| **Vox Clean** | Segoe UI, cyan highlight, editorial pacing |
| **Cyber Lime** | Consolas, lime highlight, tech look |
| **Blackout Box** | Arial Black on a solid black line box |
| **Editorial Serif** | Georgia serif, restrained highlight |
| **Buzz** | Arial Black, lavender spoken-word highlight, soft shadow |
| **Medusa** | White caps with green highlight on a black box |
| **Cartwheel Black** | White caps with purple highlight on a black box |
| **Heat** | Heavy red lowercase with a hot orange highlight |
| **Neon** | Segoe UI with a pink glow-style spoken word |
| **Magazine** | White lowercase with a bold yellow highlight |
| **Techwave** | White caps, heavy black outline and shadow |
| **Minima** | Plain white lowercase, no outline |
| **123 Honey Punch** | Top-anchored kinetic reveal: heavy Arial, gold content words, oversized punch words, alternating flush sentence posters |
| **Recess** | Centred all-caps kinetic reveal: white type on a lime→periwinkle gradient pill, per-word spring |
| **Blank** | Neutral Segoe UI starting point |

The current spoken word uses the highlight colour; upcoming words use the base colour.

**123 Honey Punch** is a true motion preset, not a static caption block. It lays out the whole phrase first — line breaks, widths, and word positions are fixed — then reveals words in place as they are spoken. Hidden words keep their space, so nothing reflows or jumps mid-phrase. There is no pop or scale animation: the active word simply becomes visible and earlier words stay visible.

Phrases hold across Whisper cards: one **poster** stays on screen until the sentence really ends — a real pause over `phrase_gap_ms` (650 ms), the cap, or sentence-final punctuation (`.`, `?`, `!`, `।`, even behind a closing quote) **confirmed by the speaker stopping there**: a word gap of at least 200 ms or an ASR card that ends on the stop. The gate is measured, not assumed: in the reference clip both full stops sit at a 0.0 s gap because the delivery is continuous, while the smallest mid-sentence hesitation is 0.20 s. A card break alone is not a pause, so the reference's four-line block is never chopped when the transcriber starts a new card, and `The Sweet Spot? It's run by Emma` stays one block across the `?`. A short pause or a comma never splits a poster.

Posters alternate their flush edge: even posters sit 7% in from the right, odd ones 7% in from the left, matching the reference's ragged rhythm. Wall parity is one global poster index, so a new card does not reset it.

Two caps keep a poster readable. The word cap is 8 words on 9:16 and the preset's 10 on 16:9. The rendered-line budget is 5 lines on 9:16 and 4 on 16:9: a poster that would wrap past it is cut at the word boundary closest to an even split, so a 14-word run reads 5 + 4 + 5 rather than 8 + 6 or 8 + 1. A phrase is also broken after an interjection and after the question mark, plus a semantic break after `about` before `the`, so the reference sentence keeps its four-line and two-line shapes. A single word too wide for the line box (a long punch word on 9:16) is scaled down to fit rather than clipped.

Two independent attributes drive the look:

- **Gold (`accent`)** — interjections and content words; short function words such as `the`, `in`, `did`, `you`, `run` stay white. `by` is the one preposition the reference paints gold.
- **Punch (`punch`)** — roughly 1.5× size. `Hey,`, `bakery`, proper nouns, and the `The Sweet Spot?` title are punch; `hear` and `by` are gold but normal-sized.

The title line is detected from the first phrase and anchored slightly higher than the normal block. The live player, `.ass` export, and MP4 burn all use the same word timings and layout rules.

#### Layout calibration

The browser and libass measure Arial Bold differently, so the two paths are calibrated separately:

| | Live overlay | `.ass` / MP4 |
|---|---|---|
| Base size | `font_size` × video height / 1600 | `font_size` with Pillow metrics for wrapping |
| Anchor | `anchor_y` + 1.5% leading compensation | `anchor_y`, minus 4.5% for title phrases |
| Width | `max_width` − 4% in landscape | `max_width` |
| Emphasis | fixed punch size, no scaling | `\fs` calibrated by `_KINETIC_ASS_FONT_SCALE` (1.399) and `_KINETIC_ASS_NORMAL_SCALE` (0.95) |
| Aspect | — | `ScaleX` 90.5 to match browser width |

At 720p the export emits `\fs77` for normal words and `\fs122` for punch; at 1080p, `\fs114` and `\fs171`. Wrapping always uses the unscaled metrics, so only the emitted sizes are calibrated and line breaks stay browser-matched.

#### Recess

**Recess** is the second `word-pop` preset: a centred, all-caps kinetic reveal where the spoken word
sits inside a gradient pill that tracks it from word to word.

- **Grouping** — `kinetic_grouping: "punch"` isolates every punch word on its own card and keeps
  each run of connective words together: `HEY` / `DID YOU HEAR ABOUT THE` / `BAKERY` / `IN` /
  `WILLOW` / `CREEK` / `THE` / `SWEET` / `SPOT?` / `IT'S RUN BY` / `EMMA` / `?`.
- **Type** — Arial Black, uppercase, no outline, no shadow. Punch words are 2.03× the normal em
  (`accent_scale: 203`). The block is centred on the video's midline (`\an5` in ASS).
- **Pill** — a rounded rectangle behind every word: radius `0.26 × 0.775 × typeEm`, filled with a
  lime→periwinkle gradient at 58 % alpha. It slides between words on the same line and fades
  between lines. Padding and radius are authored in the *normal* em, so a punch word keeps the
  same frame thickness.
- **Reveal** — each word fades in while springing from 110 % to 100 % over 130 ms.

The gradient is the one place the two renderers use different machinery. libass has no gradient
fill, so [`karaoke_ass.py`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/karaoke_ass.py)
emits the pill as cosine-spaced horizontal bands (dense at the corners, ~16 px through the middle),
one drawing event per band; the live overlay uses a CSS `linear-gradient(180deg, …)`. Both sample
the same two preset colours, so banding only shows on a very large pill.

##### Recess calibration

libass sizes Arial Black at roughly 0.72× the nominal `\fs` that Pillow reports, so the emitted em
is deliberately larger than the nominal one:

| | Live overlay | `.ass` / MP4 |
|---|---|---|
| Normal em | `font_size` × video height / 1600 × `kinetic_size_scale` | `\fs ≈ 197` at 1080p (0.652 advance ratio) |
| Pill padding | `0.16` / `0.32 × 0.775 × typeEm` | `0.16` / `0.32` em of the emitted `\fs` |
| Pill radius | `0.26 × 0.775 × typeEm` | `0.26` em |
| Cap centre | row top + 0.535 em | `\an5`, `pos_y = line centre − 0.025 em` |
| Row pitch | 1 em box + 0.29 em margin | 0.915 em |

At 1080p the burned `BAKERY` card is 1181 × 203 px of ink inside a 1225 × 307 px pill; the
reference is 1130 × 215 and 1181 × 313. The pill matches within 4 % and its centre within 2 px.
The ink box carries the Arial Black substitution error (+4–7 % wide, −3–6 % short); bundling a
narrower geometric heavy sans (Phase 5 in [`tasks/plan.md`](file:///c:/Users/susha/Documents/General/hinglish_subtitles/tasks/plan.md))
is the way to close that gap.

### Custom styles
Open the **Left Subtitle Editor → Style** tab:

1. Select a preset.
2. Click **Edit Style** to change font, size, base/highlight colour, outline, vertical position, uppercase, and box.
3. Editing a built-in creates a saved **Custom** style. Built-ins stay read-only.
4. **Reset** returns to the default preset.
5. **Export JSON** / **Import JSON** to back up or share a style.

Custom styles are stored separately from the active preset, so previewing another preset does not erase them.

### Pin to main window
The Settings drawer can pin **Caption Style**, **Speaker Diarization**, ASR Model, Hardware, and Pacing to the landing screen:

- A pinned **Caption Style** shows compact preset pills plus a small live sample; full editing stays in the drawer.
- A pinned **Speaker Diarization** shows the OFF / MULTI-SPEAKER toggle.
- Pin state is stored per browser in `localStorage` and the layout is restored on reload.

### True preview
**Verify Render** produces a short silent MP4 through the same FFmpeg + libass path used for the final burn, on a dark gradient at the target canvas. Renders are cached by style and canvas in the system temp folder. The CSS sample above it is only an approximation.

### Export and burn
- The canvas is detected from the source video: **16:9**, **9:16**, or **1:1**.
- ASS export and burn-in always regenerate from the active style.
- Burning uses FFmpeg with hardware H.264 (`h264_mf`) when available.

### Timing and sync

Every style is driven by one playback clock. The overlay reads `video.currentTime`
on `requestVideoFrameCallback` (rAF fallback), so a card is painted on the frame
its start time passes; `timeupdate`, `seeking`, `seeked` and `ratechange` only
force a correction. The card's spans are built once and afterwards only recoloured,
which is what makes a per-frame tick cheap, and the classic fade is 80 ms instead
of 150 ms. Kinetic styles use the same loop.

Word timings themselves come from the ASR and are **not** shifted by default. The
`.ASS` karaoke chain emits a `\k` gap for every pause inside a card, so the burned
highlight follows absolute word starts instead of a running sum, and the live
overlay uses the same absolute starts.

If a clip is genuinely offset, use the **SYNC −/+** control next to the caption
mode pills: 20 ms steps, ±500 ms, remembered per browser. The shift is applied once
to the working timeline, so the preview, the `.SRT` download, the `.ASS` export and
the burn all move together — nothing is applied twice.

To re-measure a clip (read-only, opt-in, not part of the test suite):

```bash
python tools/measure_timing.py path/to/clip.mp4
```

It reports ASR word starts vs acoustic onsets, card starts vs onsets, the `\k`
chain drift, the `format_ass_time` round-trip error, and the paint delay the old
`timeupdate`-only overlay would have had.

---

## 📁 Project Structure
```
hinglish_subtitles/
│── server.py               # FastAPI server + desktop window (pywebview)
│── hinglish_engine.py      # Core ffmpeg + faster-whisper (CUDA/CPU) + SRT pipeline
│── transliteration.py      # Devanagari to conversational Hinglish transliteration engine
│── caption_styles.py       # Preset schema, fifteen styles, aspect profiles
│── karaoke_ass.py          # Styled ASS karaoke generator
│── preview_renderer.py     # Cached true libass style previews
│── video_burner.py         # FFmpeg burn-in (hardware H.264)
│── run_app.bat             # 1-click Windows launcher
│── tools/measure_timing.py # Opt-in timing measurement (read-only)
└── README.md               # Documentation
```
