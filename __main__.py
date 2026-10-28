"""
Entry point for python -m hinglish_subtitles.
"""
import os
import sys

_dir = os.path.dirname(os.path.abspath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

try:
    from .server import main
except (ImportError, ValueError):
    from server import main

if __name__ == "__main__":
    main()
