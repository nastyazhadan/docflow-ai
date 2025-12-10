from fastapi import FastAPI

from cleaner_service.models.dto import CleanRequest, CleanResponse
from cleaner_service.services.cleaner import TextCleaner

cleaner_app = FastAPI(
    title="Cleaner Service",
    version="0.1.0",
)

_cleaner = TextCleaner()


@cleaner_app.post("/clean", response_model=CleanResponse)
def clean_endpoint(request: CleanRequest) -> CleanResponse:
    """
    Принимает:
    {
      "items": [ { source, path, url, content } ]
    }

    Возвращает:
    {
      "items": [ { source, path, url, raw_content, cleaned_content } ]
    }
    """
    cleaned_items = _cleaner.clean(request.items)
    return CleanResponse(items=cleaned_items)
