from __future__ import annotations

import base64
import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

import requests
import streamlit as st


@dataclass
class IngestUiPayload:
    space_id: str
    tenant_id: Optional[str]
    urls: Optional[List[str]]
    files: Optional[List[Dict[str, Any]]]  # uploaded files encoded to JSON-safe objects


def _parse_urls(text: str) -> List[str]:
    lines = [l.strip() for l in (text or "").splitlines()]
    return [l for l in lines if l]


def _now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _post_json(url: str, body: Dict[str, Any], timeout_s: float = 30.0) -> requests.Response:
    return requests.post(url, json=body, timeout=timeout_s)


def _encode_uploaded_files(
        uploaded_files: List[Any],
        max_file_bytes: int = 5 * 1024 * 1024,  # 5 MB per file
        max_total_bytes: int = 15 * 1024 * 1024,  # 15 MB total
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    total = 0

    for f in uploaded_files:
        # Streamlit UploadedFile supports read()
        data: bytes = f.read()  # type: ignore[attr-defined]
        size = len(data)
        total += size

        if size > max_file_bytes:
            raise ValueError(
                f"File too large: {getattr(f, 'name', 'unknown')} ({size} bytes). Limit: {max_file_bytes} bytes")
        if total > max_total_bytes:
            raise ValueError(f"Total upload too large ({total} bytes). Limit: {max_total_bytes} bytes")

        sha256 = hashlib.sha256(data).hexdigest()
        content_b64 = base64.b64encode(data).decode("ascii")

        out.append(
            {
                "name": getattr(f, "name", "file"),
                "mime": getattr(f, "type", None),
                "size": size,
                "sha256": sha256,
                "encoding": "base64",
                "content_b64": content_b64,
            }
        )

    return out


def _validate_payload(payload: IngestUiPayload) -> List[str]:
    errors: List[str] = []

    if not payload.space_id.strip():
        errors.append("space_id is required")

    has_urls = bool(payload.urls and len(payload.urls) > 0)
    has_files = bool(payload.files and len(payload.files) > 0)

    if not has_urls and not has_files:
        errors.append("Provide at least one of: urls or uploaded files")

    if has_urls:
        bad = [u for u in payload.urls or [] if not (u.startswith("http://") or u.startswith("https://"))]
        if bad:
            errors.append(f"Invalid URL(s): {', '.join(bad[:5])}" + (" ..." if len(bad) > 5 else ""))

    return errors


def _redact_files_for_preview(files: Optional[List[Dict[str, Any]]], b64_preview_chars: int = 120) -> Optional[
    List[Dict[str, Any]]]:
    if not files:
        return files
    redacted: List[Dict[str, Any]] = []
    for f in files:
        f2 = dict(f)
        b64 = f2.get("content_b64")
        if isinstance(b64, str) and len(b64) > b64_preview_chars:
            f2["content_b64"] = b64[:b64_preview_chars] + "...(truncated)"
        redacted.append(f2)
    return redacted


st.set_page_config(page_title="DocFlow - Sources", layout="centered")
st.title("DocFlow — Source setup (n8n webhook)")

with st.sidebar:
    st.subheader("Connection")
    n8n_base = st.text_input("N8N_BASE_URL", value="http://localhost:5678")
    mode = st.radio("Webhook mode", options=["test", "prod"], index=0, horizontal=True)
    webhook_path = st.text_input("Webhook path", value="dockflow/ingest")
    timeout_s = st.number_input("Timeout (sec)", min_value=1, max_value=300, value=30)

    if mode == "test":
        st.warning(
            "Test webhook (/webhook-test) работает только когда воркфлоу запущен в редакторе "
            "(нажми Execute workflow), и обычно принимает один вызов."
        )
    else:
        st.info("Prod webhook (/webhook) работает когда воркфлоу Active = ON.")

st.subheader("Target space")
space_id = st.text_input("space_id", value="demo-space", help="Space identifier used across the pipeline")

with st.expander("Optional context"):
    tenant_id = st.text_input("tenant_id (optional)", value="", help="Leave empty if not used")

st.subheader("Sources")

tab_http, tab_upload = st.tabs(["HTTP URLs", "Upload files"])

with tab_http:
    urls_text = st.text_area(
        "URLs (one per line)",
        value="https://habr.com/ru/articles/976404/",
        height=140,
    )

with tab_upload:
    st.caption("Выбери один или несколько файлов с компьютера. Они будут отправлены в webhook как JSON (base64).")
    uploaded_files = st.file_uploader(
        "Files",
        accept_multiple_files=True,
        type=None,  # можно ограничить: ["txt", "md", "pdf"] и т.д.
    )

st.subheader("Run ingestion")

col1, col2 = st.columns([1, 1])
with col1:
    send_btn = st.button("Run ingestion", type="primary")
with col2:
    show_raw = st.checkbox("Show raw request/response", value=True)

urls = _parse_urls(urls_text)

files_payload: Optional[List[Dict[str, Any]]] = None
if uploaded_files:
    try:
        files_payload = _encode_uploaded_files(list(uploaded_files))
    except ValueError as e:
        st.error(str(e))
        st.stop()

payload = IngestUiPayload(
    space_id=space_id.strip(),
    tenant_id=tenant_id.strip() or None,
    urls=urls if urls else None,
    files=files_payload if files_payload else None,
)

if send_btn:
    errors = _validate_payload(payload)
    if errors:
        for e in errors:
            st.error(e)
        st.stop()

    prefix = "webhook-test" if mode == "test" else "webhook"
    endpoint = f"{n8n_base.rstrip('/')}/{prefix}/{webhook_path.strip().lstrip('/')}"

    request_body: Dict[str, Any] = {
        "context": {
            "space_id": payload.space_id,
            "tenant_id": payload.tenant_id,
            "run_id": str(uuid.uuid4()),
            "started_at": _now_iso_z(),
        },
        "urls": payload.urls,
        "files": payload.files,
    }

    if show_raw:
        preview = dict(request_body)
        preview["files"] = _redact_files_for_preview(preview.get("files"))
        st.code(
            f"POST {endpoint}\n\n{json.dumps(preview, ensure_ascii=False, indent=2)}",
            language="json",
        )

    try:
        resp = _post_json(endpoint, request_body, timeout_s=float(timeout_s))
    except requests.RequestException as ex:
        st.error(f"Request failed: {ex}")
        st.stop()

    st.write(f"HTTP {resp.status_code}")

    try:
        data = resp.json()
    except Exception:
        data = None

    if 200 <= resp.status_code < 300:
        st.success("Ingestion triggered")
        if data is not None:
            st.json(data)
        else:
            st.write(resp.text)
    else:
        st.error("n8n returned an error")
        if data is not None:
            st.json(data)
        else:
            st.code(resp.text)
