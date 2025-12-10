from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class ItemBase(BaseModel):
    """
    Базовая модель элемента пайплайна (общие поля для всех стадий).

    Для файлов:
    - source = "file"
    - path обязателен
    - url может быть None

    Для HTTP:
    - source = "http"
    - url обязателен
    - path может быть None
    """

    source: str = Field(..., min_length=1)
    path: Optional[str] = Field(default=None)
    url: Optional[str] = None

    @model_validator(mode="after")
    def validate_location(self) -> "ItemBase":
        # Приводим source к нижнему регистру на всякий случай
        s = (self.source or "").lower()

        if s == "file" and not self.path:
            raise ValueError("path is required when source='file'")

        if s == "http" and not self.url:
            raise ValueError("url is required when source='http'")

        return self


class CleanItemIn(ItemBase):
    """
    Элемент на вход cleaner-service: сырое содержимое документа.
    """

    content: str = Field(default="")


class CleanItemOut(ItemBase):
    """
    Элемент на выход cleaner-service:
    - raw_content: оригинальный текст до очистки
    - cleaned_content: очищенный текст (без HTML, с нормализованными пробелами)
    """

    raw_content: str
    cleaned_content: str


class CleanRequest(BaseModel):
    """
    Запрос к /clean.

    Формат:
    {
      "items": [ { ... } ]
    }
    """

    items: List[CleanItemIn]


class CleanResponse(BaseModel):
    """
    Ответ от /clean.

    Формат:
    {
      "items": [ { ... } ]
    }
    """

    items: List[CleanItemOut]
