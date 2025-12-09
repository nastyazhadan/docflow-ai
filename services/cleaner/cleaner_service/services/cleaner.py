from typing import Iterable

from cleaner_service.models.dto import FilePayload


class TextCleaner:
    """
    Минимальный "чистильщик" текста.

    Сейчас ничего не делает, просто возвращает копию входных данных.
    Потом сюда можно будет добавить нормализацию переносов строк,
    обрезку лишних пробелов, фильтры и т.п.
    """

    def clean(self, files: Iterable[FilePayload]) -> list[FilePayload]:
        # На будущее тут можно добавить любую логику нормализации
        return [FilePayload(path=f.path, content=f.content) for f in files]
