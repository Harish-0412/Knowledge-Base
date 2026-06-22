from __future__ import annotations

import pandas as pd
import streamlit as st

from api_client import ApiClient
from components.ui_helpers import require_document_id, show_result, status_badge


def render_exports(api: ApiClient) -> None:
    document_id = require_document_id()
    if not document_id:
        return

    if st.button("Load Export Status", use_container_width=True):
        result = api.get_exports(document_id)
        if show_result(result):
            st.session_state["exports_result"] = result

    result = st.session_state.get("exports_result")
    if not result or not result.get("ok"):
        return

    exports = result["data"].get("exports", {})
    rows = [
        {
            "export": name,
            "exists": value.get("exists"),
            "path": value.get("path"),
        }
        for name, value in exports.items()
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    for row in rows:
        status_badge(row["export"], "exists" if row["exists"] else "missing")
        st.code(row["path"])

    st.info(
        "The backend currently returns local file paths, not file download endpoints. "
        "Open these paths from the backend machine or use the integration export endpoint "
        "`GET /api/export/document/{document_id}/rule-candidates` for normalized candidate JSON."
    )
