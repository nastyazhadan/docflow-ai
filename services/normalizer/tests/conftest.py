import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
base_str = str(BASE_DIR)

if base_str not in sys.path:
    sys.path.insert(0, base_str)
