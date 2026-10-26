"""
test_safe_zone.py - Caption placement and the 9:16 safe-zone guide.

Runs tests/js/safe_zone_test.js under the shared DOM stub. It pins the two
defects the POSITION slider shipped with: kinetic styles ignored the slider
(it wrote only `margin_v`), and the live bottom used a stage guess instead of
the video frame the burn draws into.

Run the script directly with:
  node tests/js/safe_zone_test.js
"""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TEST_SCRIPT = ROOT / "tests" / "js" / "safe_zone_test.js"


def test_caption_placement_and_safe_zones():
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
    assert result.returncode == 0, f"caption placement regression:\n{output}"
    assert "All caption placement and safe-zone checks passed." in output
