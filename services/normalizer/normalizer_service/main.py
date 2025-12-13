from fastapi import FastAPI

from normalizer_service.models.dto import NormalizeRequest, NormalizeResponse
from normalizer_service.services.normalizer import TextNormalizer

normalizer_app = FastAPI(title="Normalizer Service", version="0.1.0")

_normalizer = TextNormalizer()


@normalizer_app.post("/normalize", response_model=NormalizeResponse)
def normalize_endpoint(request: NormalizeRequest) -> NormalizeResponse:
    normalized_items = _normalizer.normalize(request.items)
    return NormalizeResponse(context=request.context, items=normalized_items)
