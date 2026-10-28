"""
hinglish_subtitles
~~~~~~~~~~~~~~~~~~
Conversational Hinglish ASR subtitle generator with synchronized kinetic karaoke,
2026 short-form safe zones, and local hardware-accelerated burning.
"""

import os
import sys

_dir = os.path.dirname(os.path.abspath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

__version__ = "1.0.0"
