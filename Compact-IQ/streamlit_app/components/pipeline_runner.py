from __future__ import annotations

import streamlit as st

from api_client import ApiClient
from components.ui_helpers import json_expander, require_document_id, show_result


def render_pipeline_runner(api: ApiClient) -> None:
    document_id = require_document_id()
    if not document_id:
        return

    if st.button("Run Full Document Intelligence Pipeline", type="primary", use_container_width=True):
        result = api.run_full_pipeline(document_id)
        if show_result(result, "Full pipeline finished."):
            st.session_state["pipeline_result"] = result

    result = st.session_state.get("pipeline_result")
    if not result or not result.get("ok"):
        return

    data = result["data"]
    metrics = st.columns(4)
    metrics[0].metric("Status", data.get("status", "-"))
    metrics[1].metric("Profiles", data.get("profile_count", 0))
    metrics[2].metric("Chunks", data.get("chunks_created", 0))
    metrics[3].metric("Raw candidates", data.get("raw_rule_candidates_created", data.get("rule_candidates_created", 0)))

    metrics = st.columns(4)
    metrics[0].metric("Normalized", data.get("normalized_rule_candidates_created", data.get("normalized_candidates", 0)))
    metrics[1].metric("Needs review", data.get("needs_human_review", 0))
    metrics[2].metric("Failed", data.get("failed_candidates", 0))
    metrics[3].metric("Extractors", ", ".join(data.get("extractors_used", [])) or "-")

    if data.get("warnings"):
        st.warning(data["warnings"])

    st.subheader("Export Paths")
    exports = data.get("exports") or {}
    if exports:
        for name, path in exports.items():
            st.code(f"{name}: {path}")
    else:
        st.info("No export paths returned.")

    json_expander("Full pipeline response", data, expanded=True)
