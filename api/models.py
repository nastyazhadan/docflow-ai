"""
Модели данных для Core API.

Определяют структуру запросов и ответов для endpoints:
- /spaces/{id}/ingest - индексация документов
- /spaces/{id}/query - RAG-запросы
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class Metadata(BaseModel):
    """
    Метаданные документа (чанка).
    
    Содержит информацию об источнике документа, его структуре
    и позиции чанка в исходном документе.
    Используется для отображения источников в ответах на запросы.
    """
    source: str = Field(..., min_length=1, description="Источник: 'file' или 'http'")
    path: str = Field(..., min_length=1, description="Путь к файлу или URL")
    url: Optional[str] = Field(None, description="URL (если источник HTTP)")
    title: str = Field(..., min_length=1, description="Заголовок документа")
    created_at: str = Field(..., min_length=1, description="Время создания (ISO формат)")
    chunk_index: int = Field(..., ge=0, description="Индекс чанка в документе (начиная с 0)")
    total_chunks: int = Field(..., ge=1, description="Общее количество чанков в документе")


class Document(BaseModel):
    """
    Документ для индексации (один чанк).
    
    Представляет один чанк документа после обработки через пайплайн:
    scraper → cleaner → normalizer → indexer → core API.
    
    Каждый документ - это один чанк текста с метаданными.
    """
    external_id: str = Field(..., min_length=1, description="Уникальный ID чанка (например, 'file:path.txt:0')")
    text: str = Field(..., min_length=1, description="Текст чанка для индексации")
    metadata: Metadata = Field(..., description="Метаданные чанка")


class IngestRequest(BaseModel):
    """
    Запрос на индексацию документов.
    
    Используется в endpoint POST /spaces/{space_id}/ingest.
    Принимает список документов (чанков) для добавления в векторное хранилище.
    """
    documents: List[Document] = Field(
        default_factory=list,
        description="Список документов (чанков) для индексации"
    )


class IngestResponse(BaseModel):
    """
    Ответ на запрос индексации.
    
    Возвращается из endpoint POST /spaces/{space_id}/ingest.
    Содержит количество успешно проиндексированных документов.
    """
    indexed: int = Field(
        ...,
        ge=0,
        description="Количество успешно проиндексированных документов"
    )


class QueryRequest(BaseModel):
    """
    Запрос на поиск (RAG-запрос).
    
    Используется в endpoint POST /spaces/{space_id}/query.
    Содержит текст вопроса пользователя и параметры поиска.
    
    Примечание: space_id передаётся в URL, а не в теле запроса.
    """
    query: str = Field(
        ...,
        min_length=1,
        description="Текст вопроса пользователя"
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Количество наиболее релевантных чанков для использования в ответе"
    )


class QueryResponse(BaseModel):
    """
    Ответ на RAG-запрос.
    
    Возвращается из endpoint POST /spaces/{space_id}/query.
    Содержит ответ LLM и список источников (чанков), использованных для генерации.
    """
    answer: str = Field(
        ...,
        description="Ответ LLM на основе найденных документов"
    )
    sources: List[dict] = Field(
        default_factory=list,
        description="Список источников (чанков) с метаданными, использованных для генерации ответа"
    )

