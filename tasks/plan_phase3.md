# Implementation Plan: Phase 3 — Speaker Diarization ([Speaker 1], [Speaker 2])

## Overview
Phase 3 introduces Speaker Diarization into the transcription pipeline. It automatically detects speaker turn-taking and labels dialogue cards with active speaker tags (e.g. `[Speaker 1]:`, `[Speaker 2]:`). 

Because `librosa`, `numpy`, `scipy`, and `sklearn` are all pre-installed locally, we can extract MFCC (Mel-Frequency Cepstral Coefficients) and pitch embeddings for each segment and cluster them using Agglomerative Clustering (or KMeans with silhouette optimization). This provides instantaneous, offline, zero-download speaker separation without requiring heavy Hugging Face tokens or 1GB PyAnnote weights!

---

## Technical Architecture & Dependency Graph

```
Whisper Word / Subtitle Cards ([{'start', 'end', 'text', ...}]) + Audio Waveform
                                  │
                                  ▼
               Speaker Diarizer (`diarization.py`)
                                  │
                  ┌───────────────┴───────────────┐
                  ▼                               ▼
       1. Acoustic Feature Extraction   2. Pause & Turn Boundary Analysis
       (MFCCs + Spectral Centroids)      (Long gaps > 0.4s between speakers)
                  │                               │
                  └───────────────┬───────────────┘
                                  ▼
         3. Unsupervised Clustering (`sklearn.cluster.AgglomerativeClustering`)
                                  │
                                  ▼
             Assign Segment Speaker IDs: `speaker_id: "Speaker 1"`, `"Speaker 2"`
                                  │
                                  ▼
              Card Formatter (`format_speaker_subtitles()`)
              - Updates `hinglish_text`: "[Speaker 1]: Aaj hum dekhenge..."
              - Updates `original_text`: "[Speaker 1]: आज हम देखेंगे..."
              - Updates `.srt`, `.vtt`, `.ass`
                                  │
                                  ▼
         Settings Toggle: `[ 👥 SPEAKER DIARIZATION: ON / OFF ]`
```

---

## Detailed Task Breakdown

### Task 1: Create Acoustic Speaker Diarizer (`diarization.py`)
- **Description:** Implement `diarization.py` to extract acoustic voice embeddings per segment and cluster speakers.
- **Acceptance Criteria:**
  - Extracts 13-dim MFCCs + delta coefficients for each segment's audio window.
  - Automatically determines the optimal number of speakers ($k \in [1, 4]$) via silhouette scoring, or accepts explicit `num_speakers` parameter.
  - Returns segments annotated with `"speaker"` (e.g. `"Speaker 1"`, `"Speaker 2"`).
  - Handles single-speaker audio gracefully without crashing or hallucinating extra speakers.
- **Files:** `c:\Users\susha\Documents\General\hinglish_subtitles\diarization.py`

### Task 2: Integrate Diarization in Subtitle Engines (`hinglish_engine.py` & `hindi_to_english_engine.py`)
- **Description:** Add optional `enable_diarization: bool = False` flag to `generate_subtitles()` and `generate_english_subtitles()`.
- **Acceptance Criteria:**
  - If `enable_diarization=True`, runs audio through `diarization.py` and prefixes subtitle lines with `[Speaker N]: ` (both for `.srt` and `.ass`).
  - If `enable_diarization=False` (default), preserves identical subtitle format without any regression.
- **Files:**
  - `c:\Users\susha\Documents\General\hinglish_subtitles\hinglish_engine.py`
  - `c:\Users\susha\Documents\General\hinglish_subtitles\hindi_to_english_engine.py`

### Task 3: API & Server Configuration Support (`server.py`)
- **Description:** Expose `enable_diarization` parameter in `POST /api/transcribe` and persist user preference in `launch_config.json`.
- **Acceptance Criteria:**
  - API accepts `enable_diarization` form parameter.
  - Persists preference in `launch_config.json` via `save_preferences_dict()`.
- **Files:** `c:\Users\susha\Documents\General\hinglish_subtitles\server.py`

### Task 4: Frontend UI Switch in Settings Drawer & Inspector (`index.html`, `app.js`)
- **Description:** Add a Diarization toggle switch in the Settings Drawer and display a speaker tag badge on each subtitle card.
- **Acceptance Criteria:**
  - Settings Drawer has `[ 👥 SPEAKER DIARIZATION: ENABLED / DISABLED ]` toggle pill.
  - Card rendering highlights the active speaker badge (`#Speaker 1`, `#Speaker 2`) in distinct theme colors.
- **Files:**
  - `c:\Users\susha\Documents\General\hinglish_subtitles\static\index.html`
  - `c:\Users\susha\Documents\General\hinglish_subtitles\static\app.js`

### Task 5: Automated Test Suite & Regression Verification
- **Description:** Write comprehensive unit tests in `tests/test_diarization.py` testing single-speaker, multi-speaker clustering, and API parameter handling.
- **Acceptance Criteria:**
  - All diarization unit tests pass.
  - Full test suite passes 100%.
- **Files:** `c:\Users\susha\Documents\General\hinglish_subtitles\tests\test_diarization.py`
