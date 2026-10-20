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
- **Supports All Model Sizes**: `tiny`, `base`, `small`, `medium`, and **`large-v3`**.
- **Two Ways to Use**: Modern Streamlit Web UI or direct command-line interface.

---

## 🚀 Quickstart

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
python hinglish_engine.py input_video.mp4 -d cpu -m base
```

#### CLI Flags:
| Flag | Description | Options | Default |
|---|---|---|---|
| `video_path` | Input video file path | Any video format | Required |
| `-o, --output` | Output `.srt` file path | Path string | `<video_name>_hinglish.srt` |
| `-d, --device` | Acceleration device | `auto`, `cuda`, `cpu` | `auto` |
| `-m, --model` | Whisper model size | `tiny`, `base`, `small`, `medium`, `large-v3` | `base` |
| `-l, --lang` | Language mode | `mixed`, `hi`, `en`, `auto` | `mixed` |
| `-c, --compute` | Precision type | `float16`, `int8_float16`, `int8` | Auto |

---

## 📁 Project Structure
```
hinglish_subtitles/
│── app.py                  # Streamlit Web UI (GPU-aware)
│── hinglish_engine.py      # Core ffmpeg + faster-whisper (CUDA/CPU) + SRT pipeline
│── transliteration.py      # Devanagari to conversational Hinglish transliteration engine
│── run_app.bat             # 1-click Windows launcher
└── README.md               # Documentation
```
