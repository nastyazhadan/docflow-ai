python -m uvicorn services.scraper.scraper_service.main:scraper_app --reload

pytest

docker compose build scraper-service
docker compose up