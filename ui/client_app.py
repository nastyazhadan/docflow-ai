"""
FastAPI UI entrypoint.

Kept as `ui/client_app.py` so existing `uvicorn ui.client_app:app` keeps working,
but the implementation lives in `ui/app.py`.
"""

from ui.app import app  # noqa: F401


