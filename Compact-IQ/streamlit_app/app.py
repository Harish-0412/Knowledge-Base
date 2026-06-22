from __future__ import annotations

import os
from typing import Any

import streamlit as st

from api_client import ApiClient, DEFAULT_BASE_URL
from components.chunks_view import render_chunks
from components.document_upload import render_upload_and_selection
from components.exports_view import render_exports
from components.pipeline_runner import render_pipeline_runner
from components.profile_view import render_profile
from components.rule_candidates_view import render_rule_candidates
from components.ui_helpers import json_expander, show_result, status_badge


st.set_page_config(page_title="CompatIQ Member 3 Tester", layout="wide")


def main() -> None:
    st.title("CompatIQ Member 3 Document Intelligence Tester")
    st.caption("Developer-only UI that exercises the FastAPI backend endpoints.")

    api = _render_sidebar()

    tabs = st.tabs(
        [
            "Health",
            "Upload & Select",
            "Profile",
            "Chunks",
            "Rule Candidates",
            "Full Pipeline",
            "Exports",
            "Debug",
        ]
    )

    with tabs[0]:
        render_health(api)
    with tabs[1]:
        render_upload_and_selection(api)
    with tabs[2]:
        render_profile(api)
    with tabs[3]:
        render_chunks(api)
    with tabs[4]:
        render_rule_candidates(api)
    with tabs[5]:
        render_pipeline_runner(api)
    with tabs[6]:
        render_exports(api)
    with tabs[7]:
        render_debug(api)


def _render_sidebar() -> ApiClient:
    st.sidebar.header("Backend Settings")
    default_base_url = os.getenv("FASTAPI_BASE_URL") or DEFAULT_BASE_URL
    base_url = st.sidebar.text_input("FASTAPI_BASE_URL", value=st.session_state.get("fastapi_base_url", default_base_url))
    st.session_state["fastapi_base_url"] = base_url
    api = ApiClient(base_url)

    st.sidebar.header("Document Selection")
    selected = st.sidebar.text_input("selected document_id", value=st.session_state.get("selected_document_id", ""))
    if selected:
        st.session_state["selected_document_id"] = selected.strip()

    if st.sidebar.button("Load Documents"):
        result = api.list_documents()
        if show_result(result):
            st.session_state["documents_result"] = result

    result = st.session_state.get("documents_result")
    if result and result.get("ok"):
        documents = result.get("data") or []
        options = [doc["document_id"] for doc in documents]
        if options:
            current = st.session_state.get("selected_document_id")
            index = options.index(current) if current in options else 0
            selected_doc = st.sidebar.selectbox("Choose document", options, index=index, key="sidebar_document_select")
            st.session_state["selected_document_id"] = selected_doc

    st.sidebar.divider()
    st.sidebar.write("Current document:")
    st.sidebar.code(st.session_state.get("selected_document_id") or "None")
    return api


def render_health(api: ApiClient) -> None:
    st.subheader("Backend Health")
    if st.button("Check Health", use_container_width=True):
        results = {
            "backend": api.health(),
            "db": api.db_health(),
            "llm": api.llm_health(),
        }
        st.session_state["health_results"] = results
        st.session_state["last_api_response"] = results
        st.session_state["last_error"] = {
            name: result.get("error") for name, result in results.items() if not result.get("ok")
        } or None

    results = st.session_state.get("health_results")
    if not results:
        st.info("Click Check Health to call `/api/health`, `/api/health/db`, and `/api/health/llm`.")
        return

    cols = st.columns(3)
    for idx, name in enumerate(["backend", "db", "llm"]):
        result = results[name]
        with cols[idx]:
            if result.get("ok"):
                data = result.get("data") or {}
                status = data.get("status") or data.get("provider") or "ok"
                status_badge(name.upper(), status)
                st.json(data)
            else:
                st.error(f"{name.upper()} failed")
                st.write(result.get("error"))


def render_debug(api: ApiClient) -> None:
    st.subheader("Developer Debug")
    st.write("API base URL")
    st.code(api.base_url)
    st.write("Selected document_id")
    st.code(st.session_state.get("selected_document_id") or "None")

    prompt = st.text_area(
        "LLM test prompt",
        value="Extract one compatibility rule from: Windows Server 2012 requires BIOS 1.3.5 or later.",
    )
    if st.button("Run LLM Test"):
        result = api.llm_test(prompt)
        if show_result(result):
            st.session_state["llm_test_result"] = result

    if st.session_state.get("llm_test_result"):
        json_expander("LLM test response", st.session_state["llm_test_result"], expanded=True)

    json_expander("Last API response", st.session_state.get("last_api_response"))
    json_expander("Last error", st.session_state.get("last_error"))

    if st.button("Clear Session"):
        _clear_session()
        st.rerun()


def _clear_session() -> None:
    preserved: dict[str, Any] = {"fastapi_base_url": st.session_state.get("fastapi_base_url")}
    st.session_state.clear()
    st.session_state.update({key: value for key, value in preserved.items() if value})


if __name__ == "__main__":
    main()
