"""
test_caption_sync.py - Regression test for on-video caption sync.

Bug: the overlay froze on one segment after a few seconds because
applyCaptionStyleToVideo() blanked the caption and re-rendered whichever card
was selected in the editor (activeSegmentIndex) instead of the segment under the
playhead.

The assertions live in tests/js/caption_sync_test.js, which drives app.js under a
dependency-free DOM stub. This wrapper makes the regression part of the normal
`python -m pytest tests` run.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TEST_SCRIPT = ROOT / "tests" / "js" / "caption_sync_test.js"


def test_caption_sync_follows_playhead():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")

    assert TEST_SCRIPT.exists(), f"missing test script: {TEST_SCRIPT}"

    result = subprocess.run(
        [node, str(TEST_SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )

    output = (result.stdout or "") + (result.stderr or "")
    assert result.returncode == 0, f"caption sync regression:\n{output}"
    assert "All caption sync checks passed." in output
