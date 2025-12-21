from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

from ui.api.core_api import core_request_json, get_core_api_base_url
from ui.html.pages import LOGIN_HTML, SPACES_HTML, SOURCES_HTML, chat_html

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

app = FastAPI(title="DocFlow UI (test)")


def _get_token(request: Request) -> Optional[str]:
    token = request.cookies.get("access_token")
    return token or None


@app.on_event("startup")
async def _startup() -> None:
    logger.info("UI startup. CORE_API_BASE_URL=%s", get_core_api_base_url())


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def root(request: Request) -> Response:
    if _get_token(request):
        return RedirectResponse(url="/spaces", status_code=302)
    return RedirectResponse(url="/login", status_code=302)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> Response:
    if _get_token(request):
        return RedirectResponse(url="/spaces", status_code=302)
    return HTMLResponse(content=LOGIN_HTML)


@app.get("/spaces", response_class=HTMLResponse)
async def spaces_page(request: Request) -> HTMLResponse:
    if not _get_token(request):
        return RedirectResponse(url="/login", status_code=302)
    return HTMLResponse(content=SPACES_HTML)


@app.get("/chat/{space_id}", response_class=HTMLResponse)
async def chat_page(space_id: str, request: Request) -> HTMLResponse:
    if not _get_token(request):
        return RedirectResponse(url="/login", status_code=302)
    return HTMLResponse(content=chat_html(space_id))


@app.get("/sources", response_class=HTMLResponse)
async def sources_page(request: Request) -> HTMLResponse:
    if not _get_token(request):
        return RedirectResponse(url="/login", status_code=302)
    return HTMLResponse(content=SOURCES_HTML)


class LoginPayload(BaseModel):
    tenant_slug: str = "default"
    email: str
    password: str


@app.post("/api/login")
async def api_login(payload: LoginPayload) -> JSONResponse:
    ts = datetime.utcnow().isoformat() + "Z"
    base = get_core_api_base_url()
    url = f"{base}/api/v1/auth/login"
    logger.info("[UI][LOGIN] ts=%s tenant_slug=%s email=%s core_url=%s", ts, payload.tenant_slug, payload.email, url)

    try:
        status_code, body_text, data = await core_request_json(
            "POST",
            url,
            json_body={
                "tenant_slug": payload.tenant_slug,
                "email": payload.email,
                "password": payload.password,
            },
            timeout_s=30.0,
        )
    except Exception:
        logger.exception("[UI][LOGIN] Core API request failed")
        raise HTTPException(status_code=502, detail="Failed to call Core API")

    if status_code >= 400:
        logger.info("[UI][LOGIN] Core API status=%s body_preview=%s", status_code, (body_text or "")[:500])
        raise HTTPException(status_code=status_code, detail=(data or body_text))

    token = (data or {}).get("access_token")
    if not token:
        raise HTTPException(status_code=502, detail="Core API returned no access_token")

    resp = JSONResponse(content={"status": "ok"})
    # httpOnly cookie to avoid leaking token to JS
    resp.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,  # local/dev
        path="/",
    )
    return resp


class RegisterPayload(BaseModel):
    tenant_slug: str = "default"
    tenant_name: str = "Default"
    email: str
    password: str
    role: str = "editor"


@app.post("/api/register")
async def api_register(payload: RegisterPayload) -> JSONResponse:
    ts = datetime.utcnow().isoformat() + "Z"
    base = get_core_api_base_url()
    url = f"{base}/api/v1/auth/register"
    logger.info(
        "[UI][REGISTER] ts=%s tenant_slug=%s email=%s core_url=%s",
        ts,
        payload.tenant_slug,
        payload.email,
        url,
    )

    try:
        status_code, body_text, data = await core_request_json(
            "POST",
            url,
            json_body={
                "tenant_slug": payload.tenant_slug,
                "tenant_name": payload.tenant_name,
                "email": payload.email,
                "password": payload.password,
                "role": payload.role,
            },
            timeout_s=30.0,
        )
    except Exception:
        logger.exception("[UI][REGISTER] Core API request failed")
        raise HTTPException(status_code=502, detail="Failed to call Core API")

    if status_code >= 400:
        logger.info("[UI][REGISTER] Core API status=%s body_preview=%s", status_code, (body_text or "")[:500])
        raise HTTPException(status_code=status_code, detail=(data or body_text))

    token = (data or {}).get("access_token")
    if not token:
        raise HTTPException(status_code=502, detail="Core API returned no access_token")

    resp = JSONResponse(content={"status": "ok"})
    resp.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )
    return resp


@app.post("/api/logout")
async def api_logout() -> JSONResponse:
    resp = JSONResponse(content={"status": "ok"})
    resp.delete_cookie("access_token", path="/")
    return resp


@app.get("/api/me")
async def api_me(request: Request) -> JSONResponse:
    ts = datetime.utcnow().isoformat() + "Z"
    token = _get_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    base = get_core_api_base_url()
    url = f"{base}/api/v1/auth/me"
    logger.info("[UI][ME] ts=%s core_url=%s", ts, url)

    try:
        status_code, body_text, data = await core_request_json("GET", url, token=token, timeout_s=30.0)
    except Exception:
        logger.exception("[UI][ME] Core API request failed")
        raise HTTPException(status_code=502, detail="Failed to call Core API")

    if status_code >= 400:
        logger.info("[UI][ME] Core API status=%s body_preview=%s", status_code, (body_text or "")[:500])
        raise HTTPException(status_code=status_code, detail=(data or body_text))

    return JSONResponse(content=data, status_code=status_code)


@app.get("/api/spaces")
async def api_list_spaces(request: Request) -> JSONResponse:
    ts = datetime.utcnow().isoformat() + "Z"
    token = _get_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    base = get_core_api_base_url()
    url = f"{base}/api/v1/spaces"
    logger.info("[UI][SPACES][LIST] ts=%s core_url=%s", ts, url)

    try:
        status_code, body_text, data = await core_request_json("GET", url, token=token, timeout_s=30.0)
    except Exception:
        logger.exception("[UI][SPACES][LIST] Core API request failed")
        raise HTTPException(status_code=502, detail="Failed to call Core API")

    if status_code >= 400:
        logger.info("[UI][SPACES][LIST] Core API status=%s body_preview=%s", status_code, (body_text or "")[:500])
        raise HTTPException(status_code=status_code, detail=(data or body_text))

    return JSONResponse(content=data, status_code=status_code)


class SpaceCreatePayload(BaseModel):
    space_id: str
    name: str = ""


@app.post("/api/spaces")
async def api_create_space(payload: SpaceCreatePayload, request: Request) -> JSONResponse:
    ts = datetime.utcnow().isoformat() + "Z"
    token = _get_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    base = get_core_api_base_url()
    url = f"{base}/api/v1/spaces"
    logger.info("[UI][SPACES][CREATE] ts=%s space_id=%s core_url=%s", ts, payload.space_id, url)

    try:
        status_code, body_text, data = await core_request_json(
            "POST",
            url,
            token=token,
            json_body={"space_id": payload.space_id, "name": payload.name},
            timeout_s=30.0,
        )
    except Exception:
        logger.exception("[UI][SPACES][CREATE] Core API request failed")
        raise HTTPException(status_code=502, detail="Failed to call Core API")

    if status_code >= 400:
        logger.info("[UI][SPACES][CREATE] Core API status=%s body_preview=%s", status_code, (body_text or "")[:500])
        raise HTTPException(status_code=status_code, detail=(data or body_text))

    return JSONResponse(content=data, status_code=status_code)


class ChatAskPayload(BaseModel):
    space_id: str
    query: str
    top_k: int = 3


@app.post("/api/chat/ask")
async def api_chat_ask(payload: ChatAskPayload, request: Request) -> JSONResponse:
    ts = datetime.utcnow().isoformat() + "Z"
    token = _get_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    base = get_core_api_base_url()
    url = f"{base}/api/v1/spaces/{payload.space_id}/query"
    logger.info(
        "[UI][CHAT] ts=%s space_id=%s query_len=%s top_k=%s core_url=%s",
        ts,
        payload.space_id,
        len(payload.query or ""),
        payload.top_k,
        url,
    )

    try:
        status_code, body_text, data = await core_request_json(
            "POST",
            url,
            token=token,
            json_body={"query": payload.query, "top_k": payload.top_k},
            timeout_s=120.0,
        )
    except Exception:
        logger.exception("[UI][CHAT] Failed to call Core API")
        raise HTTPException(status_code=502, detail="Failed to call Core API")

    if status_code >= 400:
        logger.info("[UI][CHAT] Core API status=%s body_preview=%s", status_code, (body_text or "")[:500])
        raise HTTPException(status_code=status_code, detail=(data or body_text))

    return JSONResponse(content=data, status_code=status_code)


@app.get("/api/sources")
async def api_list_sources(request: Request, space_id: str | None = None) -> JSONResponse:
    token = _get_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    base = get_core_api_base_url()
    url = f"{base}/api/v1/sources"
    if space_id:
        url += f"?space_id={space_id}"

    try:
        status_code, body_text, data = await core_request_json("GET", url, token=token, timeout_s=30.0)
    except Exception:
        logger.exception("[UI][SOURCES][LIST] Core API request failed")
        raise HTTPException(status_code=502, detail="Failed to call Core API")

    if status_code >= 400:
        raise HTTPException(status_code=status_code, detail=(data or body_text))

    return JSONResponse(content=data, status_code=status_code)


class SourceCreatePayload(BaseModel):
    space_id: str
    type: str
    config: Dict[str, Any] = {}
    enabled: bool = True


@app.post("/api/sources")
async def api_create_source(payload: SourceCreatePayload, request: Request) -> JSONResponse:
    token = _get_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    base = get_core_api_base_url()
    url = f"{base}/api/v1/sources"

    try:
        status_code, body_text, data = await core_request_json(
            "POST",
            url,
            token=token,
            json_body=payload.model_dump(),
            timeout_s=30.0,
        )
    except Exception:
        logger.exception("[UI][SOURCES][CREATE] Core API request failed")
        raise HTTPException(status_code=502, detail="Failed to call Core API")

    if status_code >= 400:
        raise HTTPException(status_code=status_code, detail=(data or body_text))

    return JSONResponse(content=data, status_code=status_code)


class SourceUpdatePayload(BaseModel):
    config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


@app.patch("/api/sources/{source_id}")
async def api_update_source(source_id: str, payload: SourceUpdatePayload, request: Request) -> JSONResponse:
    token = _get_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    base = get_core_api_base_url()
    url = f"{base}/api/v1/sources/{source_id}"

    try:
        status_code, body_text, data = await core_request_json(
            "PATCH",
            url,
            token=token,
            json_body=payload.model_dump(exclude_none=True),
            timeout_s=30.0,
        )
    except Exception:
        logger.exception("[UI][SOURCES][UPDATE] Core API request failed")
        raise HTTPException(status_code=502, detail="Failed to call Core API")

    if status_code >= 400:
        raise HTTPException(status_code=status_code, detail=(data or body_text))

    return JSONResponse(content=data, status_code=status_code)


@app.delete("/api/sources/{source_id}")
async def api_delete_source(source_id: str, request: Request) -> JSONResponse:
    token = _get_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    base = get_core_api_base_url()
    url = f"{base}/api/v1/sources/{source_id}"

    try:
        status_code, body_text, data = await core_request_json("DELETE", url, token=token, timeout_s=30.0)
    except Exception:
        logger.exception("[UI][SOURCES][DELETE] Core API request failed")
        raise HTTPException(status_code=502, detail="Failed to call Core API")

    if status_code >= 400:
        raise HTTPException(status_code=status_code, detail=(data or body_text))

    return JSONResponse(content={}, status_code=status_code)
