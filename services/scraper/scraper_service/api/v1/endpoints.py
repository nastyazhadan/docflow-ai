from fastapi import APIRouter, Depends

from scraper_service.core.config import get_settings
from scraper_service.models.dto import ScrapeResponse, FileContent
from scraper_service.services.file_reader import FileReader

router = APIRouter()


def get_file_reader() -> FileReader:
    settings = get_settings()
    # Можно ограничить расширения, если нужно, пока читаем всё
    return FileReader(root_dir=settings.scraper_root_dir)


@router.get("/scrape", response_model=ScrapeResponse)
def scrape(reader: FileReader = Depends(get_file_reader)) -> ScrapeResponse:
    files: list[FileContent] = reader.read_all()
    return ScrapeResponse(files=files, total_files=len(files))
