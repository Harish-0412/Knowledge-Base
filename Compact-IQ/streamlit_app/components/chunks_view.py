from __future__ import annotations

import pandas as pd
import streamlit as st

from api_client import ApiClient
from components.ui_helpers import json_expander, require_document_id, show_result


def render_chunks(api: ApiClient) -> None:
    document_id = require_document_id()
    if not document_id:
        return

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Run Extraction", use_container_width=True):
            result = api.run_extraction(document_id)
            if show_result(result, "Extraction finished."):
                st.session_state["extraction_result"] = result
    with col2:
        if st.button("Load Chunks", use_container_width=True):
            result = api.get_chunks(document_id)
            if show_result(result):
                st.session_state["chunks_result"] = result

    with st.expander("Chunk Filters"):
        only_llm = st.checkbox("Show only LLM input chunks")
        llm_usage = st.selectbox("LLM usage", ["", "rule_extraction", "global_context", "background_context", "evidence_only", "ignore"])
        semantic_zone = st.selectbox(
            "Semantic zone",
            [
                "",
                "document_metadata",
                "overview",
                "supported_components",
                "compatibility_requirements",
                "certified_configurations",
                "unsupported_configurations",
                "known_issues",
                "fixed_issues",
                "upgrade_requirements",
                "driver_requirements",
                "firmware_requirements",
                "security_updates",
                "remediation_guidance",
                "additional_notes",
                "unknown",
            ],
        )
        likelihood = st.selectbox("Rule likelihood", ["", "high", "medium", "low"])
        chunk_type = st.text_input("Chunk type")
        if st.button("Apply Chunk Filters"):
            result = api.get_chunks(
                document_id,
                send_to_llm=True if only_llm else None,
                rule_likelihood=likelihood or None,
                chunk_type=chunk_type or None,
                llm_usage=llm_usage or None,
                semantic_zone=semantic_zone or None,
            )
            if show_result(result):
                st.session_state["chunks_result"] = result

    extraction_result = st.session_state.get("extraction_result")
    if extraction_result and extraction_result.get("ok"):
        data = extraction_result["data"]
        metrics = st.columns(3)
        metrics[0].metric("Chunks created", data.get("chunks_created", 0))
        metrics[1].metric("Methods used", ", ".join(data.get("methods_used", [])) or "-")
        metrics[2].metric("LLM input chunks", data.get("llm_input_chunk_count", 0))
        st.write("Rule likelihood summary")
        st.json(data.get("rule_likelihood_summary", {}))
        st.write("LLM usage summary")
        st.json(data.get("llm_usage_summary", {}))
        st.write("Semantic zone summary")
        st.json(data.get("semantic_zone_summary", {}))
        st.caption(f"Rejected: {data.get('chunks_rejected', 0)} | Deduplicated: {data.get('chunks_deduplicated', 0)}")
        if data.get("warnings"):
            st.warning(data["warnings"])

    chunks_result = st.session_state.get("chunks_result")
    if not chunks_result or not chunks_result.get("ok"):
        return

    chunks = chunks_result["data"].get("chunks", [])
    if not chunks:
        st.info("No chunks found.")
        return

    summary_rows = [
        {
            "chunk_id": chunk.get("chunk_id"),
            "page_number": chunk.get("page_number"),
            "chunk_type": chunk.get("chunk_type"),
            "section_title": chunk.get("section_title"),
            "semantic_zone": chunk.get("semantic_zone"),
            "llm_usage": chunk.get("llm_usage"),
            "rule_signal_score": chunk.get("rule_signal_score"),
            "source_parser": chunk.get("source_parser"),
            "source_chunker": chunk.get("source_chunker"),
            "extraction_method": chunk.get("extraction_method"),
            "quality_score": chunk.get("quality_score"),
            "rule_likelihood": chunk.get("rule_likelihood"),
            "send_to_llm": chunk.get("send_to_llm"),
        }
        for chunk in chunks
    ]
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

    for chunk in chunks:
        title = f"Chunk {chunk.get('chunk_id')} | page {chunk.get('page_number')} | {chunk.get('chunk_type')}"
        with st.expander(title):
            st.write(f"**Section:** {chunk.get('section_title') or '-'}")
            st.write(f"**Extraction method:** {chunk.get('extraction_method')}")
            st.write(f"**Quality score:** {chunk.get('quality_score')}")
            st.write(f"**Source parser:** {chunk.get('source_parser') or '-'}")
            st.write(f"**Source chunker:** {chunk.get('source_chunker') or '-'}")
            st.write(f"**LLM usage:** {chunk.get('llm_usage')}")
            st.write(f"**Rule signal score:** {chunk.get('rule_signal_score')}")
            st.write(f"**Rule likelihood:** {chunk.get('rule_likelihood')}")
            st.write(f"**Send to LLM:** {chunk.get('send_to_llm')}")
            st.write(f"**Semantic zone:** {chunk.get('semantic_zone') or '-'}")
            st.write(f"**Section path:** {chunk.get('section_path_json') or []}")
            st.write(f"**Rule signals:** {', '.join(chunk.get('rule_signals_json') or []) or '-'}")
            st.write(f"**Classification signals:** {', '.join(chunk.get('classification_signals_json') or []) or '-'}")
            st.write("**Source excerpt**")
            st.code(chunk.get("source_excerpt") or "")
            with st.expander("Full text"):
                st.text(chunk.get("text") or "")
            if chunk.get("table_row_json"):
                json_expander("table_row_json", chunk["table_row_json"])
            if chunk.get("metadata_json"):
                json_expander("metadata_json", chunk["metadata_json"])
