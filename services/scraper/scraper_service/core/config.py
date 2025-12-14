import os
from functools import lru_cache


class Settings:
    def __init__(self) -> None:
        self.http_timeout: float = float(os.getenv("SCRAPER_HTTP_TIMEOUT", "10.0"))
        self.http_max_connections: int = int(os.getenv("SCRAPER_HTTP_MAX_CONNECTIONS", "10"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
