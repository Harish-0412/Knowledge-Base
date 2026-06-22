from __future__ import annotations

import pandas as pd
import streamlit as st

from api_client import ApiClient
from components.ui_helpers import show_result, status_badge


def render_upload_and_selection(api: ApiClient) -> None:
    st.subheader("Upload Document")
    uploaded_file = st.file_uploader(
        "Choose a document",
        type=["pdf", "txt", "md", "csv", "docx"],
        accept_multiple_files=False,
    )
    if st.button("Upload Document", disabled=uploaded_file is None):
        result = api.upload_document(uploaded_file)
        if show_result(result, "Document uploaded."):
            document = result["data"]
            st.session_state["selected_document_id"] = document["document_id"]
            st.code(document["document_id"])
            st.json(document)

    st.divider()
    st.subheader("Uploaded Documents")
    if st.button("Refresh Document List"):
        st.session_state["documents_result"] = api.list_documents()
        show_result(st.session_state["documents_result"])

    result = st.session_state.get("documents_result")
    if result is None:
        result = api.list_documents()
        st.session_state["documents_result"] = result
        show_result(result)

    if not result.get("ok"):
        return

    documents = result.get("data") or []
    if not documents:
        st.info("No uploaded documents found.")
        return

    st.dataframe(pd.DataFrame(documents), use_container_width=True, hide_index=True)
    options = [doc["document_id"] for doc in documents]
    current = st.session_state.get("selected_document_id")
    index = options.index(current) if current in options else 0
    selected = st.selectbox("Selected document_id", options, index=index)
    st.session_state["selected_document_id"] = selected

    selected_doc = next((doc for doc in documents if doc["document_id"] == selected), None)
    if selected_doc:
        status_badge("Document status", selected_doc.get("status"))
        st.json(selected_doc)
