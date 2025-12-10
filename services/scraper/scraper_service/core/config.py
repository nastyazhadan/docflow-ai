import os
from functools import lru_cache
from pathlib import Path


class Settings:
    """Application settings (KISS, но с заделом под SOLID)."""

    def __init__(self) -> None:
        root_dir = os.getenv("SCRAPER_ROOT_DIR", "/data/docs")
        self.scraper_root_dir: Path = Path(root_dir).resolve()

        # Настройки HTTP-скачивания
        self.http_timeout: float = float(
            os.getenv("SCRAPER_HTTP_TIMEOUT", "10.0")
        )
        self.http_max_connections: int = int(
            os.getenv("SCRAPER_HTTP_MAX_CONNECTIONS", "10")
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Кэшируем, чтобы не пересоздавать объект на каждый запрос
    return Settings()
