from fastapi import FastAPI

from normalizer_service.models.dto import NormalizeRequest, NormalizeResponse
from normalizer_service.services.normalizer import Normalizer

normalizer_app = FastAPI(
    title="Normalizer Service",
    version="0.1.0",
)

_normalizer = Normalizer()


@normalizer_app.post("/normalize", response_model=NormalizeResponse)
def normalize_endpoint(request: NormalizeRequest) -> NormalizeResponse:
    documents = _normalizer.normalize(request.files)
    return NormalizeResponse(documents=documents)
