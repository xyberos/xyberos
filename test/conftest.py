"""Make the application source directory importable during pytest collection."""

import sys
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[1] / "xyberos"
sys.path.insert(0, str(SOURCE_ROOT))
