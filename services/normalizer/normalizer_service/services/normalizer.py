from typing import Iterable

from normalizer_service.models.dto import FilePayload, Document


class Normalizer:
    """
    Минимальный нормализатор: по одному документу на файл.
    Потом сюда можно будет добавить разбиение на чанки, языковые фильтры и т.п.
    """

    def normalize(self, files: Iterable[FilePayload]) -> list[Document]:
        documents: list[Document] = []
        for f in files:
            # Сейчас id = path, дальше можно сменить на uuid
            documents.append(
                Document(
                    id=f.path,
                    path=f.path,
                    content=f.content,
                )
            )
        return documents
