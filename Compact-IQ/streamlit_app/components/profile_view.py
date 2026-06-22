from __future__ import annotations

import pandas as pd
import streamlit as st

from api_client import ApiClient
from components.ui_helpers import require_document_id, show_result, status_badge


EXTRACTOR_LABELS = {
    "pymupdf": "PyMuPDF",
    "docling": "Docling",
    "chandra_ocr": "Chandra OCR",
    "text": "text",
    "csv": "csv",
}


def render_profile(api: ApiClient) -> None:
    document_id = require_document_id()
    if not document_id:
        return

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Run Profile", use_container_width=True):
            result = api.run_profile(document_id)
            if show_result(result, "Profile generated."):
                st.session_state["profile_result"] = result
    with col2:
        if st.button("Load Existing Profile", use_container_width=True):
            result = api.get_profile(document_id)
            if show_result(result):
                st.session_state["profile_result"] = result

    result = st.session_state.get("profile_result")
    if not result or not result.get("ok"):
        return

    profiles = result["data"].get("profiles", [])
    if not profiles:
        st.info("No profile rows found.")
        return

    rows = [
        {
            "page_number": row.get("page_number"),
            "page_type": row.get("page_type"),
            "recommended_extractor": row.get("recommended_extractor"),
            "confidence": row.get("confidence"),
            "reason": row.get("reason"),
        }
        for row in profiles
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.subheader("Extractor Choices")
    for row in profiles:
        extractor = row.get("recommended_extractor")
        label = EXTRACTOR_LABELS.get(extractor, extractor)
        status_badge(f"Page {row.get('page_number')} extractor", label)
