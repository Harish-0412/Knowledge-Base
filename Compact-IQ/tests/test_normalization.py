from app.db.models import Document, DocumentChunk, RuleCandidate
from app.db.session import SessionLocal
from app.services.cisco_normalization import compare_cisco_ios_xe_versions, parse_cisco_ios_xe_release
from app.services.normalization_service import NormalizationService
from app.services.schema_validation_service import SchemaValidationService


def create_candidate(payload: dict, source_excerpt: str = "System BIOS 02.00.21 or later is required.", page_number: int = 1) -> int:
    assert SessionLocal is not None
    with SessionLocal() as db:
        document = Document(
            document_id="DOC-ABCDEF123456",
            filename="normalize.txt",
            original_filename="normalize.txt",
            file_path="normalize.txt",
            content_type="text/plain",
            source_type="text",
            file_size_bytes=1,
            status="rules_extracted",
            metadata_json={},
        )
        db.add(document)
        chunk = DocumentChunk(
            document_id=document.document_id,
            page_number=page_number,
            chunk_index=0,
            chunk_type="paragraph",
            section_title=None,
            text=source_excerpt,
            source_excerpt=source_excerpt,
            extraction_method="text",
            quality_score=0.95,
            bbox_json=None,
            metadata_json={},
        )
        db.add(chunk)
        db.flush()
        candidate = RuleCandidate(
            document_id=document.document_id,
            source_chunk_id=chunk.chunk_id,
            rule_type=payload.get("rule_type"),
            condition_logic=payload.get("condition_logic"),
            conditions_json=payload.get("conditions"),
            requirement_json=payload.get("requirement"),
            severity=payload.get("severity"),
            confidence_score=payload.get("confidence_score", 0.8),
            confidence_reason=payload.get("confidence_reason", "test"),
            explanation=payload.get("explanation"),
            source_excerpt=source_excerpt,
            review_status="pending_review",
            normalization_status="pending_normalization",
            raw_llm_output_json={"rule_candidates": [payload]},
            normalized_rule_json=None,
            validation_errors_json=None,
        )
        db.add(candidate)
        db.commit()
        return candidate.candidate_id


def normalize(candidate_id: int) -> RuleCandidate:
    assert SessionLocal is not None
    with SessionLocal() as db:
        candidate = db.get(RuleCandidate, candidate_id)
        assert candidate is not None
        NormalizationService().normalize_candidate(candidate)
        db.commit()
        db.refresh(candidate)
        return candidate


def test_normalize_bios_aliases():
    candidate_id = create_candidate(
        {
            "rule_type": "requires_minimum_version",
            "condition_logic": "all",
            "conditions": [{"field": "CPU", "operator": "installed", "value": "Intel Xeon"}],
            "requirement": {"field": "System BIOS", "operator": "or later", "value": "02.00.21"},
            "severity": "medium",
        }
    )

    candidate = normalize(candidate_id)

    assert candidate.requirement_json[0]["component_type"] == "bios"


def test_normalize_os_aliases():
    candidate_id = create_candidate(
        {
            "rule_type": "requires_minimum_version",
            "condition_logic": "all",
            "conditions": [{"field": "Operating System", "operator": "installed", "value": "Windows Server 2012 R2"}],
            "requirement": {"field": "Driver", "operator": "minimum", "value": "v2.0.21"},
            "severity": "low",
        }
    )

    candidate = normalize(candidate_id)

    assert candidate.conditions_json[0]["component_type"] == "os"
    assert candidate.conditions_json[0]["version_scheme"] == "named_release"


def test_normalize_operators():
    candidate_id = create_candidate(
        {
            "rule_type": "requires_minimum_version",
            "condition_logic": "all",
            "conditions": [{"field": "Firmware", "operator": "at least", "value": "5.1"}],
            "requirement": {"field": "BIOS", "operator": "older than", "value": "02.00.21"},
            "severity": "critical",
        }
    )

    candidate = normalize(candidate_id)

    assert candidate.conditions_json[0]["operator"] == ">="
    assert candidate.requirement_json[0]["operator"] == "<"


def test_normalize_version_zero_padded_to_semantic():
    candidate_id = create_candidate(
        {
            "rule_type": "requires_minimum_version",
            "condition_logic": "all",
            "conditions": [{"field": "CPU", "operator": "installed", "value": "Intel Xeon"}],
            "requirement": {"field": "Dell BIOS", "operator": "minimum", "value": "02.00.21"},
            "severity": "medium",
        }
    )

    candidate = normalize(candidate_id)

    requirement = candidate.requirement_json[0]
    assert requirement["version_raw"] == "02.00.21"
    assert requirement["version_normalized"] == "2.0.21"
    assert requirement["version_scheme"] == "semantic"


def test_compound_and_conditions_are_preserved():
    candidate_id = create_candidate(
        {
            "rule_type": "requires_minimum_version",
            "condition_logic": "all",
            "conditions": [
                {"field": "CPU", "operator": "installed", "value": "Intel Xeon E5-2400 V2 family"},
                {"field": "OS", "operator": "installed", "value": "Windows Server 2012 R2"},
            ],
            "requirement": {"field": "BIOS", "operator": "minimum", "value": "02.00.21"},
            "severity": "medium",
        }
    )

    candidate = normalize(candidate_id)

    assert candidate.condition_logic == "AND"
    assert len(candidate.conditions_json) == 2
    assert candidate.conditions_json[0]["component_type"] == "cpu"
    assert candidate.conditions_json[1]["component_type"] == "os"


def test_ambiguous_values_become_needs_human_review():
    candidate_id = create_candidate(
        {
            "rule_type": "other",
            "condition_logic": "all",
            "conditions": [{"field": "mystery", "operator": "installed", "value": None}],
            "requirement": {"field": "unknown", "operator": "exists", "value": None},
            "severity": "unknown",
        }
    )

    candidate = normalize(candidate_id)

    assert candidate.normalization_status == "needs_human_review"
    assert candidate.validation_errors_json


def test_source_evidence_is_preserved():
    excerpt = "Dell BIOS 02.00.21 or later is required for Intel Xeon."
    candidate_id = create_candidate(
        {
            "rule_type": "requires_minimum_version",
            "condition_logic": "all",
            "conditions": [{"field": "CPU", "operator": "installed", "value": "Intel Xeon"}],
            "requirement": {"field": "Dell BIOS", "operator": "or later", "value": "02.00.21"},
            "severity": "medium",
            "source_excerpt": excerpt,
        },
        source_excerpt=excerpt,
    )

    candidate = normalize(candidate_id)

    assert candidate.normalized_rule_json["source_excerpt"] == excerpt
    assert candidate.source_excerpt == excerpt


def test_normalized_output_validates_against_model():
    candidate_id = create_candidate(
        {
            "rule_type": "requires_minimum_version",
            "condition_logic": "all",
            "conditions": [{"field": "CPU", "operator": "installed", "value": "Intel Xeon E5-2400 V2 family"}],
            "requirement": {"field": "System BIOS", "operator": "minimum", "value": "02.00.21"},
            "severity": "medium",
        }
    )

    candidate = normalize(candidate_id)
    valid, errors = SchemaValidationService().validate_normalized_candidate(candidate.normalized_rule_json)

    assert valid is True
    assert errors == []
    assert candidate.normalization_status == "normalized"


def test_cisco_model_component_type_normalization_does_not_store_model_as_version():
    excerpt = "Switch Model: C9200-24T-A | Introductory Release: Cisco IOS XE Gibraltar 16.10.1"
    candidate_id = create_candidate(
        {
            "rule_type": "readiness_requirement",
            "condition_logic": "AND",
            "conditions": [{"component_type": "model", "component_name": "C9200-24T-A", "operator": "installed", "value_raw": "C9200-24T-A", "vendor": "Cisco"}],
            "requirements": [{"component_type": "os", "component_name": "Cisco IOS XE Gibraltar", "operator": ">=", "version_raw": "16.10.1", "requirement_kind": "min_version"}],
            "severity": "info",
        },
        source_excerpt=excerpt,
        page_number=2,
    )

    candidate = normalize(candidate_id)
    condition = candidate.normalized_rule_json["conditions"][0]

    assert condition["component_type"] == "device_model"
    assert condition["value_raw"] == "C9200-24T-A"
    assert condition["version_raw"] is None
    assert condition["version_normalized"] is None
    assert condition["version_scheme"] is None


def test_cisco_ios_xe_parser_with_train_and_suffix():
    parsed = parse_cisco_ios_xe_release("Cisco IOS XE Gibraltar 16.10.1")
    assert parsed["component_name"] == "Cisco IOS XE"
    assert parsed["component_family"] == "Gibraltar"
    assert parsed["version_raw"] == "16.10.1"
    assert parsed["version_scheme"] == "cisco_ios_xe"

    suffix = parse_cisco_ios_xe_release("Cisco IOS XE Amsterdam 17.3.2a")
    assert suffix["component_family"] == "Amsterdam"
    assert suffix["version_raw"] == "17.3.2a"
    assert suffix["version_scheme"] == "cisco_ios_xe"
    assert compare_cisco_ios_xe_versions("17.3.2a", "17.3.2") > 0


def test_introductory_release_classifies_as_support_matrix_fact_and_preserves_source_page():
    excerpt = "Switch Model: C9200-24T-A | Introductory Release: Cisco IOS XE Gibraltar 16.10.1"
    candidate_id = create_candidate(
        {
            "rule_type": "readiness_requirement",
            "condition_logic": "AND",
            "conditions": [{"component_type": "model", "component_name": "C9200-24T-A", "operator": "installed", "value_raw": "C9200-24T-A"}],
            "requirements": [{"component_type": "os", "component_name": "Cisco IOS XE Gibraltar", "operator": ">=", "version_raw": "16.10.1", "requirement_kind": "min_version"}],
            "severity": "info",
            "confidence_score": 0.95,
        },
        source_excerpt=excerpt,
        page_number=3,
    )

    candidate = normalize(candidate_id)
    normalized = candidate.normalized_rule_json

    assert normalized["candidate_kind"] == "support_matrix_fact"
    assert normalized["rule_type"] == "model_support_min_version"
    assert normalized["source_page"] == 3
    assert normalized["confidence_score"] <= 0.8
    assert candidate.normalization_status == "normalized"


def test_unsupported_feature_classification():
    excerpt = "IPsec VPN is not supported on Cisco Catalyst 9200 Series Switches."
    candidate_id = create_candidate(
        {
            "rule_type": "incompatible_combination",
            "condition_logic": "AND",
            "conditions": [{"component_type": "device_type", "component_name": "Cisco Catalyst 9200 Series Switches", "operator": "installed", "value_raw": "Cisco Catalyst 9200 Series Switches"}],
            "requirements": [{"component_type": "virtualization_feature", "component_name": "IPsec VPN", "operator": "not supported", "value_raw": "IPsec VPN", "requirement_kind": "not_allowed"}],
            "severity": "info",
        },
        source_excerpt=excerpt,
    )

    candidate = normalize(candidate_id)
    normalized = candidate.normalized_rule_json
    requirement = normalized["requirements"][0]

    assert normalized["candidate_kind"] == "unsupported_feature"
    assert normalized["rule_type"] == "unsupported_feature"
    assert requirement["operator"] == "not_supported"
    assert requirement["requirement_kind"] == "not_supported"
    assert requirement["component_type"] == "feature"
