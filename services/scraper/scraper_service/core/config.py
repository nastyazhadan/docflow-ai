import os
from functools import lru_cache
from pathlib import Path


class Settings:
    """Application settings (KISS, но с заделом под SOLID)."""

    def __init__(self) -> None:
        root_dir = os.getenv("SCRAPER_ROOT_DIR", "/data/docs")
        self.scraper_root_dir: Path = Path(root_dir).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Кэшируем, чтобы не пересоздавать объект на каждый запрос
    return Settings()
