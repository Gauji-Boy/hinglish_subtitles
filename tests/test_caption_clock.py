"""
test_caption_clock.py - Regression test for the caption playback clock.

Bug: classic caption styles were painted only on the video's `timeupdate`
event (~4 Hz), so a card could appear up to 250 ms after its start time.

The assertions live in tests/js/caption_clock_test.js, which drives the frame
loop one tick at a time under the dependency-free DOM stub. This wrapper makes
the regression part of the normal `python -m pytest tests` run.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TEST_SCRIPT = ROOT / "tests" / "js" / "caption_clock_test.js"


def test_caption_clock_paints_on_frame():
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
    assert result.returncode == 0, f"caption clock regression:\n{output}"
    assert "All caption clock checks passed." in output
