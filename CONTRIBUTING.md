# Contributing to Hinglish Subtitles

Thank you for your interest in contributing to **Hinglish Subtitles**! We welcome community contributions, bug reports, and improvements.

---

## 🛠️ Development Setup

1. **Fork and clone** the repository:
   ```bash
   git clone https://github.com/Gauji-Boy/hinglish_subtitles.git
   cd hinglish_subtitles
   ```

2. **Ensure prerequisites** are installed:
   - Python 3.10+ (Python 3.12 or 3.13 recommended)
   - [FFmpeg](https://ffmpeg.org/download.html) installed and accessible on your system `PATH`
   - Node.js (for running front-end and safe-zone tests)

3. **Install dependencies in editable mode**:
   ```bash
   pip install -e . pytest httpx
   ```

---

## 🧪 Running Tests

Before submitting any pull request, ensure all test suites pass:

### 1. Python Pytest Suite
Runs 330+ unit and integration tests covering transcription normalization, subtitle styles, ASS syntax generation, diarization, and video burning:
```bash
python -m pytest tests -q
```

### 2. JavaScript Safe-Zone & UI Placement Tests
Validates 2026 short-form platform safe zones (Reels, Shorts), narrow-rail orientation, and positioning coordinates:
```bash
node tests/js/safe_zone_test.js
```

---

## 📋 Pull Request Guidelines

1. **Create a topic branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **Follow existing coding style**:
   - Keep changes concise and focused on the problem.
   - Preserve existing docstrings, tests, and comments.
3. **Add automated tests** for any new features or bug fixes.
4. **Ensure all tests pass** locally before submitting your PR.
5. **Licensing**: All contributions are licensed under the **GNU Affero General Public License v3 (AGPLv3)**.
