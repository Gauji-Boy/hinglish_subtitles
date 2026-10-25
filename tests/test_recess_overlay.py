"""
test_recess_overlay.py - Live-overlay geometry for the Recess preset.

The ASS renderer is pinned by tests/test_karaoke_ass.py. This runs the matching
browser-side checks in tests/js/recess_overlay_test.js under a dependency-free
DOM stub, so the live overlay cannot drift away from the burned-in output.

Run the script directly with:
  node tests/js/recess_overlay_test.js <resolved-recess-style.json>
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from caption_styles import resolve_style

ROOT = Path(__file__).resolve().parent.parent
TEST_SCRIPT = ROOT / "tests" / "js" / "recess_overlay_test.js"


def test_recess_overlay_geometry(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")

    assert TEST_SCRIPT.exists(), f"missing test script: {TEST_SCRIPT}"

    style_path = tmp_path / "recess.json"
    style_path.write_text(json.dumps(resolve_style("recess")), encoding="utf-8")

    result = subprocess.run(
        [node, str(TEST_SCRIPT), str(style_path)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )

    output = (result.stdout or "") + (result.stderr or "")
    assert result.returncode == 0, f"recess overlay regression:\n{output}"
    assert "All Recess overlay checks passed." in output
