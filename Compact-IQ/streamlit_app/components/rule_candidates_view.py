from __future__ import annotations

import pandas as pd
import streamlit as st

from api_client import ApiClient
from components.ui_helpers import json_expander, require_document_id, show_result, status_badge


def render_rule_candidates(api: ApiClient) -> None:
    document_id = require_document_id()
    if not document_id:
        return

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Extract Rules from Chunks", use_container_width=True):
            result = api.extract_rules(document_id)
            if show_result(result, "Rule extraction finished."):
                st.session_state["rule_extraction_result"] = result
                _load_candidates(api, document_id)
    with col2:
        if st.button("Load Rule Candidates", use_container_width=True):
            _load_candidates(api, document_id)

    extraction_result = st.session_state.get("rule_extraction_result")
    if extraction_result and extraction_result.get("ok"):
        _render_rule_extraction_summary(extraction_result["data"])

    candidates_result = st.session_state.get("rule_candidates_result")
    if not candidates_result or not candidates_result.get("ok"):
        return

    candidates = candidates_result["data"].get("rule_candidates", [])
    if not candidates:
        st.info("No rule candidates found.")
        return

    rows = [
        {
            "candidate_id": candidate.get("candidate_id"),
            "rule_id": candidate.get("rule_id"),
            "candidate_kind": (candidate.get("normalized_rule_json") or {}).get("candidate_kind"),
            "rule_type": candidate.get("rule_type"),
            "severity": candidate.get("severity"),
            "confidence_score": candidate.get("confidence_score"),
            "review_status": candidate.get("review_status"),
            "normalization_status": candidate.get("normalization_status"),
            "source_chunk_id": candidate.get("source_chunk_id"),
        }
        for candidate in candidates
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    kinds = sorted({row.get("candidate_kind") or "unknown" for row in rows})
    selected_kinds = st.multiselect("Candidate kind", kinds, default=kinds)
    if selected_kinds:
        candidates = [
            candidate
            for candidate in candidates
            if ((candidate.get("normalized_rule_json") or {}).get("candidate_kind") or "unknown") in selected_kinds
        ]

    for candidate in candidates:
        title = f"Candidate {candidate.get('candidate_id')} | {candidate.get('rule_type') or 'unknown'}"
        with st.expander(title):
            cols = st.columns(3)
            cols[0].write(f"**Rule ID:** {candidate.get('rule_id') or '-'}")
            cols[1].write(f"**Severity:** {candidate.get('severity') or '-'}")
            cols[2].write(f"**Confidence:** {candidate.get('confidence_score')}")
            normalized = candidate.get("normalized_rule_json") or {}
            st.write(f"**Candidate kind:** {normalized.get('candidate_kind') or '-'}")
            status_badge("Review status", candidate.get("review_status"))
            status_badge("Normalization status", candidate.get("normalization_status"))
            st.write(f"**Confidence reason:** {candidate.get('confidence_reason') or '-'}")
            st.write(f"**Source chunk:** {candidate.get('source_chunk_id')}")
            st.write("**Source excerpt**")
            st.code(candidate.get("source_excerpt") or "")
            st.write(f"**Explanation:** {candidate.get('explanation') or '-'}")

            _render_normalized_summary(normalized)
            json_expander("raw_llm_output_json", candidate.get("raw_llm_output_json"))
            json_expander("normalized_rule_json", normalized)
            if candidate.get("validation_errors_json"):
                json_expander("validation_errors_json", candidate.get("validation_errors_json"), expanded=True)


def _load_candidates(api: ApiClient, document_id: str) -> None:
    result = api.get_rule_candidates(document_id)
    if show_result(result):
        st.session_state["rule_candidates_result"] = result


def _render_rule_extraction_summary(data: dict) -> None:
    metrics = st.columns(4)
    created = data.get("rule_candidates_created", 0)
    metrics[0].metric("Raw candidates", data.get("raw_rule_candidates_created", created))
    metrics[1].metric("Normalized", data.get("normalized_rule_candidates_created", "-"))
    metrics[2].metric("Needs review", data.get("needs_human_review", "-"))
    metrics[3].metric("Failed", data.get("failed_candidates", "-"))
    if data.get("warnings"):
        st.warning(data["warnings"])


def _render_normalized_summary(normalized: dict | list) -> None:
    if not isinstance(normalized, dict) or not normalized:
        return

    conditions = normalized.get("conditions") or []
    if conditions:
        st.write("**Conditions**")
        st.dataframe(pd.DataFrame(conditions), use_container_width=True, hide_index=True)

    requirements = normalized.get("requirements") or normalized.get("requirement") or []
    if isinstance(requirements, dict):
        requirements = [requirements]
    if requirements:
        st.write("**Requirements**")
        for requirement in requirements:
            st.json(requirement)
