from fastapi import FastAPI

from cleaner_service.models.dto import CleanRequest, CleanResponse
from cleaner_service.services.cleaner import TextCleaner

app = FastAPI(
    title="Cleaner Service",
    version="0.1.0",
)

_cleaner = TextCleaner()


@app.post("/clean", response_model=CleanResponse)
def clean_endpoint(request: CleanRequest) -> CleanResponse:
    cleaned_files = _cleaner.clean(request.files)
    return CleanResponse(files=cleaned_files)
