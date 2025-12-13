from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

import requests
import streamlit as st


@dataclass
class IngestUiPayload:
    tenant_id: Optional[str]
    urls: Optional[List[str]]
    file_glob: Optional[str]


def _parse_urls(text: str) -> List[str]:
    lines = [l.strip() for l in (text or "").splitlines()]
    return [l for l in lines if l]


def _validate_payload(space_id: str, payload: IngestUiPayload) -> List[str]:
    errors: List[str] = []

    if not space_id.strip():
        errors.append("space_id is required")

    has_urls = bool(payload.urls and len(payload.urls) > 0)
    has_glob = bool(payload.file_glob and payload.file_glob.strip())

    if not has_urls and not has_glob:
        errors.append("Provide at least one of: urls or file_glob")

    if has_urls:
        bad = [u for u in payload.urls or [] if not (u.startswith("http://") or u.startswith("https://"))]
        if bad:
            errors.append(f"Invalid URL(s): {', '.join(bad[:5])}" + (" ..." if len(bad) > 5 else ""))

    return errors


def _post_json(url: str, body: Dict[str, Any], timeout_s: float = 30.0) -> requests.Response:
    return requests.post(url, json=body, timeout=timeout_s)


st.set_page_config(page_title="DocFlow - Sources", layout="centered")
st.title("DocFlow — Source setup")

with st.sidebar:
    st.subheader("Connection")
    core_api_base = st.text_input("CORE_API_BASE_URL", value="http://localhost:8000")
    timeout_s = st.number_input("Timeout (sec)", min_value=1, max_value=300, value=30)

st.subheader("Target space")
space_id = st.text_input("space_id", value="demo-space", help="Space identifier used across the pipeline")

with st.expander("Optional context"):
    tenant_id = st.text_input("tenant_id (optional)", value="", help="Leave empty if not used")

st.subheader("Sources")

tab_http, tab_files = st.tabs(["HTTP URLs", "File glob"])

with tab_http:
    urls_text = st.text_area(
        "URLs (one per line)",
        value="https://habr.com/ru/articles/976404/",
        height=140,
    )

with tab_files:
    file_glob = st.text_input("file_glob", value="", placeholder="**/*.txt")

st.subheader("Run ingestion")

col1, col2 = st.columns([1, 1])

with col1:
    send_btn = st.button("Run ingestion", type="primary")

with col2:
    show_raw = st.checkbox("Show raw request/response", value=True)

urls = _parse_urls(urls_text)
payload = IngestUiPayload(
    tenant_id=tenant_id.strip() or None,
    urls=urls if urls else None,
    file_glob=file_glob.strip() or None,
)

if send_btn:
    errors = _validate_payload(space_id, payload)
    if errors:
        for e in errors:
            st.error(e)
        st.stop()

    endpoint = f"{core_api_base.rstrip('/')}/spaces/{space_id}/sources/ingest"

    request_body = {
        "tenant_id": payload.tenant_id,
        "urls": payload.urls,
        "file_glob": payload.file_glob,
    }

    if show_raw:
        st.code(
            f"POST {endpoint}\n\n{json.dumps(request_body, ensure_ascii=False, indent=2)}",
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
        st.success("Ingestion started")

        if isinstance(data, dict):
            ctx = data.get("context") if isinstance(data.get("context"), dict) else {}
            status = data.get("status")

            if status:
                st.write(f"status: `{status}`")

            if ctx:
                st.write("context:")
                st.json(ctx)
            else:
                st.json(data)
        else:
            st.write(resp.text)
    else:
        st.error("Core API returned an error")
        if data is not None:
            st.json(data)
        else:
            st.code(resp.text)
