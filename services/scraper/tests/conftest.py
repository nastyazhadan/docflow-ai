import sys
from pathlib import Path

# Папка services/scraper (где лежит scraper_service)
BASE_DIR = Path(__file__).resolve().parents[1]

# Добавляем её в sys.path, если ещё не добавлена
base_str = str(BASE_DIR)
if base_str not in sys.path:
    sys.path.insert(0, base_str)
