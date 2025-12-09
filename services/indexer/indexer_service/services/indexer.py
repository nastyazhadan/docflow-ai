import logging
from typing import Sequence

from indexer_service.models.dto import Document

logger = logging.getLogger("indexer_service")
logger.setLevel(logging.INFO)


class Indexer:
    """
    Минимальный индексатор: вместо реального отправления в Core API
    пока просто логирует документы.
    """

    @staticmethod
    def index_documents(space_id: str, documents: Sequence[Document]) -> int:
        logger.info("Indexing %d documents into space '%s'", len(documents), space_id)
        for doc in documents:
            logger.info("DOC id=%s path=%s len=%d", doc.id, doc.path, len(doc.content))
        return len(documents)
