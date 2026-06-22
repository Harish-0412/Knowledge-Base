from app.db.models import DocumentChunk, RuleCandidate
from app.services.cisco_normalization import parse_cisco_ios_xe_release
from app.services.processing_lane_service import (
    CandidateQualityGate,
    DeterministicCandidateGenerator,
    LaneDecision,
    TableSchemaClassifier,
)


def make_chunk(text: str, page_number: int = 2) -> DocumentChunk:
    return DocumentChunk(
        document_id="DOC-ABCDEF123456",
        page_number=page_number,
        chunk_index=0,
        chunk_type="table_row",
        section_title="Cisco Catalyst 9200 Series Switches",
        text=text,
        source_excerpt=text,
        extraction_method="text",
        quality_score=1.0,
        metadata_json={},
    )


def test_table_schema_classifier_detects_cisco_switch_model_table():
    chunk = make_chunk("Switch Model: C9200-24T-A | Default License Level 1: Network Advantage | Description: ports | Introductory Release: Cisco IOS XE Gibraltar 16.10.1")

    decision = TableSchemaClassifier().classify(chunk)

    assert decision.table_schema_type == "cisco_switch_model_introductory_release"
    assert decision.processing_lane == "deterministic_support_matrix"


def test_cisco_switch_model_deterministic_candidate_generation():
    chunk = make_chunk("Switch Model: C9200-24T-A | Default License Level 1: Network Advantage | Description: ports | Introductory Release: Cisco IOS XE Gibraltar 16.10.1")
    decision = LaneDecision(
        processing_lane="deterministic_support_matrix",
        table_schema_type="cisco_switch_model_introductory_release",
        generator="cisco_switch_model_intro_release",
    )

    [candidate] = DeterministicCandidateGenerator().generate("DOC-ABCDEF123456", chunk, decision)
    payload = candidate.raw_llm_output_json["rule_candidates"][0]

    assert payload["candidate_kind"] == "support_matrix_fact"
    assert payload["rule_type"] == "model_support_min_version"
    assert payload["conditions"][0]["component_type"] == "device_model"
    assert payload["conditions"][0]["version_raw"] is None
    assert payload["requirements"][0]["component_type"] == "network_os"
    assert payload["requirements"][0]["component_name"] == "Cisco IOS XE"
    assert payload["requirements"][0]["component_family"] == "Gibraltar"
    assert payload["requirements"][0]["version_scheme"] == "cisco_ios_xe"
    assert payload["source_page"] == 2


def test_cisco_network_module_deterministic_candidate_generation():
    chunk = make_chunk("Network Module: C9200-NM-4G | Description: Four SFP slots | Introductory Release: Cisco IOS XE Gibraltar 16.10.1")
    decision = LaneDecision(
        processing_lane="deterministic_support_matrix",
        table_schema_type="cisco_network_module_introductory_release",
        generator="cisco_network_module_intro_release",
    )

    [candidate] = DeterministicCandidateGenerator().generate("DOC-ABCDEF123456", chunk, decision)
    payload = candidate.raw_llm_output_json["rule_candidates"][0]

    assert payload["candidate_kind"] == "support_matrix_fact"
    assert payload["rule_type"] == "network_module_support_min_version"
    assert payload["conditions"][0]["component_type"] == "network_module"
    assert payload["requirements"][0]["version_scheme"] == "cisco_ios_xe"


def test_unsupported_feature_deterministic_candidate_generation():
    chunk = make_chunk("Feature: IPsec VPN | Not Supported On These Variants: All")
    decision = LaneDecision(
        processing_lane="deterministic_table_rule",
        table_schema_type="unsupported_feature_matrix",
        generator="unsupported_feature",
    )

    [candidate] = DeterministicCandidateGenerator().generate("DOC-ABCDEF123456", chunk, decision)
    payload = candidate.raw_llm_output_json["rule_candidates"][0]

    assert payload["candidate_kind"] == "unsupported_feature"
    assert payload["rule_type"] == "unsupported_feature"
    assert payload["requirements"][0]["requirement_kind"] == "not_supported"
    assert payload["requirements"][0]["component_type"] == "feature"


def test_quality_gate_catches_bad_support_matrix_candidate():
    candidate = RuleCandidate(
        document_id="DOC-ABCDEF123456",
        source_chunk_id=1,
        source_excerpt="Switch Model: C9200-24T-A | Introductory Release: Cisco IOS XE Gibraltar 16.10.1",
        review_status="pending_review",
        normalization_status="normalized",
        raw_llm_output_json={"rule_candidates": []},
        normalized_rule_json={
            "rule_type": "readiness_requirement",
            "source_page": None,
            "source_excerpt": "Switch Model: C9200-24T-A | Introductory Release: Cisco IOS XE Gibraltar 16.10.1",
            "conditions": [{"component_type": "unknown", "version_raw": "C9200-24T-A"}],
            "requirements": [{"component_type": "network_os", "value_raw": "os", "version_scheme": "semantic"}],
        },
    )

    warnings = CandidateQualityGate().evaluate(candidate)

    assert "missing_candidate_kind" in warnings
    assert "unknown_component_type" in warnings
    assert "model_as_version_error" in warnings
    assert "support_matrix_as_readiness_requirement" in warnings


def test_cisco_ios_xe_parser_suffix_remains_cisco_scheme():
    parsed = parse_cisco_ios_xe_release("Cisco IOS XE Amsterdam 17.3.2a")

    assert parsed["component_name"] == "Cisco IOS XE"
    assert parsed["component_family"] == "Amsterdam"
    assert parsed["version_raw"] == "17.3.2a"
    assert parsed["version_scheme"] == "cisco_ios_xe"
