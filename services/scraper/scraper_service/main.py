from fastapi import FastAPI

from scraper_service.api.v1.endpoints import router as v1_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Scraper Service",
        version="0.1.0",
    )
    app.include_router(v1_router, prefix="/api/v1")
    return app


scraper_app = create_app()
