# Implementation Plan: Phase 2 — Direct Video Burning via Local FFmpeg

## Overview
Phase 2 enables creators to burn-in styled subtitles (either standard SRT/VTT or animated Bouncy Karaoke ASS from Phase 1) directly into exported `.mp4` video files using local FFmpeg. It leverages NVIDIA GPU hardware encoding (`h264_nvenc`) with seamless automatic CPU fallback, eliminating external editing tools like Premiere or CapCut for quick social media publishing.

---

## Technical Architecture & Dependency Graph

```
Original Uploaded Video / Media + Subtitle Script (.srt or .ass)
                          │
                          ▼
             Video Burner Helper (`video_burner.py`)
                          │
         ┌────────────────┴────────────────┐
         ▼                                 ▼
   GPU Hardware Encoding             CPU Software Encoding
  (`h264_nvenc` - fastest)          (`libx264 -preset ultrafast`)
         │                                 │
         └────────────────┬────────────────┘
                          ▼
            Temporary Rendered MP4 Output
                          │
                          ▼
          FastAPI Server (`/api/export/burn-video`)
                          │
                          ▼
          Frontend Export Button: `🔥 BURN VIDEO (.MP4)`
```

---

## Detailed Task Breakdown

### Task 1: Create Video Burner Core Engine (`video_burner.py`)
- **Description:** Implement a robust FFmpeg subtitle burn-in wrapper with automatic hardware detection (`h264_nvenc` vs `libx264`).
- **Acceptance Criteria:**
  - Handles Windows path escaping for FFmpeg filter syntax (`filename.replace('\\', '/').replace(':', '\\:')`).
  - Supports both `.ass` (animated karaoke) and `.srt` subtitle inputs.
  - Detects if NVIDIA NVENC is operational; automatically falls back to `libx264` if unavailable.
  - Streams or reports encoding progress cleanly without blocking.
- **Files:** `c:\Users\susha\Documents\General\hinglish_subtitles\video_burner.py`

### Task 2: Server API Endpoints (`server.py`)
- **Description:** Add `/api/export/burn-video` (and `/api/export/burn-video-file` for raw uploads) endpoint to accept a video file and subtitle payload/ASS script, burning them together and streaming back the rendered MP4.
- **Acceptance Criteria:**
  - Validates video and subtitle input formats.
  - Returns `video/mp4` with `Content-Disposition: attachment; filename="<base>_subtitled.mp4"`.
  - Cleans up all temporary files safely in a `finally` block.
- **Files:** `c:\Users\susha\Documents\General\hinglish_subtitles\server.py`

### Task 3: Desktop & Browser UI Download Trigger (`index.html`, `app.js`)
- **Description:** Add a prominent **`🔥 BURN VIDEO (.MP4)`** action button in the floating export dock.
- **Acceptance Criteria:**
  - Shows an active progress state on the button (`⏳ BURNING VIDEO...`) while FFmpeg encodes.
  - Triggers the file download dialog or downloads the burned `.mp4` file directly when finished.
  - Disables gracefully for audio-only uploads.
- **Files:**
  - `c:\Users\susha\Documents\General\hinglish_subtitles\static\index.html`
  - `c:\Users\susha\Documents\General\hinglish_subtitles\static\app.js`

### Task 4: Automated Testing & Verification
- **Description:** Create unit tests in `tests/test_video_burner.py` verifying command construction, path escaping, encoder fallback logic, and API response status codes.
- **Acceptance Criteria:**
  - All new tests pass.
  - Full suite (`python -m pytest tests -q`) remains 100% green.
- **Files:** `c:\Users\susha\Documents\General\hinglish_subtitles\tests\test_video_burner.py`
