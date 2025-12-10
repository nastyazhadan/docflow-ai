from typing import List, Optional

from pydantic import BaseModel, Field


class ItemBase(BaseModel):
    """
    Базовая модель элемента пайплайна (общие поля для всех стадий).
    """

    source: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1)
    url: Optional[str] = None


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
