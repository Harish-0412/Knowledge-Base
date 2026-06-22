from __future__ import annotations

from typing import Any

import streamlit as st


def remember_response(result: dict[str, Any]) -> None:
    st.session_state["last_api_response"] = result.get("data")
    st.session_state["last_error"] = result.get("error")


def show_result(result: dict[str, Any], success_message: str | None = None) -> bool:
    remember_response(result)
    if result.get("ok"):
        if success_message:
            st.success(success_message)
        return True

    st.error(format_error(result))
    return False


def format_error(result: dict[str, Any]) -> str:
    status = result.get("status_code")
    error = result.get("error")
    prefix = f"API error {status}: " if status else ""
    if isinstance(error, dict):
        nested = error.get("message") or error.get("code") or error
        return f"{prefix}{nested}"
    return f"{prefix}{error or 'Unknown error'}"


def require_document_id() -> str | None:
    document_id = st.session_state.get("selected_document_id")
    if not document_id:
        st.warning("Select or upload a document first.")
        return None
    return document_id


def status_badge(label: str, value: Any) -> None:
    text = str(value) if value is not None else "unknown"
    lowered = text.lower()
    if any(word in lowered for word in ["healthy", "ok", "succeeded", "uploaded", "extracted", "profiled", "rules_extracted", "normalized"]):
        st.success(f"{label}: {text}")
    elif any(word in lowered for word in ["warning", "pending", "review", "mock"]):
        st.warning(f"{label}: {text}")
    elif any(word in lowered for word in ["failed", "error", "unhealthy", "missing"]):
        st.error(f"{label}: {text}")
    else:
        st.info(f"{label}: {text}")


def json_expander(label: str, payload: Any, expanded: bool = False) -> None:
    with st.expander(label, expanded=expanded):
        st.json(payload)
