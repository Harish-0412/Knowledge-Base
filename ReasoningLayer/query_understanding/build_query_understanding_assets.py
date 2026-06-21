"""Generate Phase 2 catalogs, pattern corpus, test corpus, and manifest."""

from __future__ import annotations

import json
from pathlib import Path


BASE = Path(__file__).resolve().parent
DATE = "2026-06-21"
VERSION = "1.0.0"


INTENT_SPECS = [
    ("INTENT-CONCEPT-EXPLANATION", "ConceptExplanation", "Explain a domain or reasoning concept.", ["BIOS", "Firmware", "OperatingSystem", "Driver", "SecurityComponent", "ManagementTool"], ["Layer1"], "explanation"),
    ("INTENT-ROOT-CAUSE-ANALYSIS", "RootCauseAnalysis", "Determine why a device or state is failing.", ["Device", "Violation", "Rule"], ["Layer2", "Layer3"], "root_cause_analysis"),
    ("INTENT-COMPLIANCE-STATUS", "ComplianceStatus", "Determine compliance state and failed controls.", ["Device", "Rule", "Violation"], ["Layer2", "Layer3"], "compliance_status"),
    ("INTENT-RECOMMENDATION-REQUEST", "RecommendationRequest", "Request corrective actions for a device or violation.", ["Device", "Violation", "RootCause"], ["Layer2", "Layer3"], "recommendations"),
    ("INTENT-PREVENTION-REQUEST", "PreventionRequest", "Request controls that prevent recurrence.", ["Violation", "RootCause"], ["Layer3"], "prevention_strategy"),
    ("INTENT-RISK-ASSESSMENT", "RiskAssessment", "Assess technical and business risk.", ["Device", "Violation", "Risk"], ["Layer2", "Layer3"], "risk_assessment"),
    ("INTENT-DEPENDENCY-ANALYSIS", "DependencyAnalysis", "Trace direct or transitive dependencies.", ["BIOS", "Firmware", "OperatingSystem", "Driver", "Rule"], ["Layer3"], "dependency_graph"),
    ("INTENT-COMPATIBILITY-INQUIRY", "CompatibilityInquiry", "Determine whether components or versions are compatible.", ["BIOS", "Firmware", "OperatingSystem", "Driver", "Version"], ["Layer3"], "compatibility_result"),
    ("INTENT-VIOLATION-INVESTIGATION", "ViolationInvestigation", "Investigate a specific violation and its evidence.", ["Device", "Violation", "Rule"], ["Layer2", "Layer3"], "violation_details"),
    ("INTENT-FLEET-ANALYSIS", "FleetAnalysis", "Analyze inventory state across a fleet or device group.", ["Device", "Risk", "Violation"], ["Layer2"], "fleet_summary"),
    ("INTENT-DEVICE-INVESTIGATION", "DeviceInvestigation", "Inspect the state and inventory of one device.", ["Device"], ["Layer2"], "device_details"),
    ("INTENT-RULE-EXPLANATION", "RuleExplanation", "Explain a compatibility rule and its evidence.", ["Rule", "Document"], ["Layer3"], "rule_explanation"),
    ("INTENT-VERSION-ANALYSIS", "VersionAnalysis", "Find required, installed, allowed, or fixed versions.", ["Version", "BIOS", "Firmware", "OperatingSystem", "Driver"], ["Layer3"], "version_analysis"),
    ("INTENT-LIFECYCLE-ANALYSIS", "LifecycleAnalysis", "Evaluate support, approval, deprecation, or end-of-life state.", ["BIOS", "Firmware", "OperatingSystem", "Driver", "Rule"], ["Layer3"], "lifecycle_analysis"),
    ("INTENT-UPGRADE-IMPACT", "UpgradeImpactAnalysis", "Assess readiness, dependencies, and risk before an upgrade.", ["Device", "Version", "BIOS", "Firmware", "OperatingSystem", "Driver"], ["Layer2", "Layer3"], "upgrade_impact"),
]

ENTITY_SPECS = [
    ("Device", "Managed endpoint or server inventory object.", ["device", "endpoint", "laptop", "workstation", "server", "machine"]),
    ("BIOS", "Pre-boot BIOS or UEFI firmware component.", ["bios", "system bios", "uefi", "rom bios"]),
    ("Firmware", "Embedded software controlling platform or device hardware.", ["firmware", "system firmware", "device firmware", "fw"]),
    ("OperatingSystem", "Endpoint operating system family, release, or build.", ["operating system", "os", "windows", "linux", "ubuntu"]),
    ("Driver", "Software interface between an operating system and hardware.", ["driver", "drivers", "driver pack", "device driver"]),
    ("SecurityComponent", "Endpoint security control or agent.", ["security component", "security agent", "antivirus", "endpoint protection", "secure boot", "tpm"]),
    ("ManagementTool", "Endpoint management, patching, or monitoring component.", ["management tool", "management agent", "mdm", "monitoring agent", "patch manager"]),
    ("Rule", "Layer 3 compatibility or configuration rule.", ["rule", "compatibility rule", "constraint", "policy rule", "crule"]),
    ("Version", "Normalized component version or version constraint value.", ["version", "release", "build", "revision", "fixed in"]),
    ("Violation", "Failed compatibility, compliance, dependency, or policy expectation.", ["violation", "failure", "non-compliant", "incompatibility"]),
    ("RootCause", "Reasoning classification explaining a violation.", ["root cause", "cause", "reason", "configuration drift", "version mismatch"]),
    ("Recommendation", "Corrective action class proposed for a root cause.", ["recommendation", "fix", "remediation", "corrective action"]),
    ("Risk", "Ordered impact assessment from Informational through Critical.", ["risk", "severity", "impact", "critical", "high", "medium", "low"]),
    ("Vendor", "Organization associated with a product or source.", ["vendor", "manufacturer", "publisher", "supplier"]),
    ("Document", "Evidence-bearing source document or advisory.", ["document", "advisory", "bulletin", "source", "evidence"]),
]

SIGNALS = {
    "ConceptExplanation": {"signals": ["what is", "what are", "define", "explain the concept", "describe"],
                           "negative_signals": ["compliance status", "risk level", "required version", "root cause", "lifecycle status", "upgrade impact", "rule evidence"], "priority": 5},
    "RootCauseAnalysis": {"signals": ["why is", "why did", "root cause", "what caused", "reason for", "failing"], "priority": 80},
    "ComplianceStatus": {"signals": ["compliance status", "is compliant", "non-compliant", "compliance state", "failed controls", "affect compliance"], "priority": 65},
    "RecommendationRequest": {"signals": ["how do i fix", "how can i fix", "what should i do", "recommend a fix", "remediate", "corrective action"], "priority": 75},
    "PreventionRequest": {"signals": ["how can i prevent", "prevent recurrence", "prevention strategy", "avoid this again", "prevent this"], "priority": 75},
    "RiskAssessment": {"signals": ["assess risk", "what risks", "risk level", "business impact", "technical impact", "how risky"], "priority": 70},
    "DependencyAnalysis": {"signals": ["depends on", "dependencies", "dependency chain", "requires", "prerequisite", "what depends"], "priority": 70},
    "CompatibilityInquiry": {"signals": ["compatible with", "compatibility issues", "is compatible", "support firmware", "work with", "supported combination"], "priority": 60},
    "ViolationInvestigation": {"signals": ["investigate violation", "violation details", "why this violation", "violation evidence", "show violation"], "priority": 85},
    "FleetAnalysis": {"signals": ["affected devices", "fleet", "across devices", "all managed devices", "how many devices", "device group"], "priority": 75},
    "DeviceInvestigation": {"signals": ["show inventory for", "inspect device", "device details", "device state", "inventory of"], "priority": 55},
    "RuleExplanation": {"signals": ["explain rule", "why does rule", "rule logic", "rule evidence", "what does rule"], "priority": 85},
    "VersionAnalysis": {"signals": ["version is required", "required version", "minimum version", "fixed version", "version range", "which version"], "priority": 70},
    "LifecycleAnalysis": {"signals": ["end of support", "end of life", "deprecated", "lifecycle status", "support window", "still supported"], "priority": 75},
    "UpgradeImpactAnalysis": {"signals": ["upgrade impact", "before upgrading", "if i upgrade", "upgrade readiness", "safe to upgrade", "upgrade path"], "priority": 90},
}

ROUTES = {spec[1]: spec[4] for spec in INTENT_SPECS}

PATTERN_TEMPLATES = {
    "ConceptExplanation": ["What is {subject}?", "Define {subject}.", "Describe {subject}.", "Explain the concept of {subject}.", "What are {subject} components?"],
    "RootCauseAnalysis": ["Why is {device} failing?", "What caused {device} to fail?", "Find the root cause for {device}.", "What is the reason for {device} failing?", "Why did {device} become non-compliant?"],
    "ComplianceStatus": ["What is the compliance status of {device}?", "Is {device} compliant?", "Show the compliance state for {device}.", "Why is {device} non-compliant?", "Which failed controls affect {device}?"],
    "RecommendationRequest": ["How do I fix {device}?", "How can I fix {device}?", "What should I do for {device}?", "Recommend a fix for {device}.", "What corrective action applies to {device}?"],
    "PreventionRequest": ["How can I prevent this violation?", "What prevention strategy avoids version mismatch?", "How do we prevent recurrence?", "How can we avoid this again?", "Which control can prevent this conflict?"],
    "RiskAssessment": ["What risks affect {device}?", "Assess risk for {device}.", "What is the risk level for {device}?", "Describe the business impact for {device}.", "How risky is this violation?"],
    "DependencyAnalysis": ["What depends on BIOS?", "Show firmware dependencies.", "Trace the dependency chain for BIOS.", "Which driver requires Firmware 3.2?", "What prerequisite applies to BIOS?"],
    "CompatibilityInquiry": ["Is BIOS 2.1 compatible with Firmware 3.2?", "What compatibility issues exist?", "Does BIOS 2.1 support Firmware 3.2?", "Will Driver 4.1 work with OS 11.2?", "Show the supported combination for BIOS and firmware."],
    "ViolationInvestigation": ["Investigate violation VIOL-VERSION for {device}.", "Show violation details for {device}.", "Why this violation on {device}?", "Find violation evidence for {device}.", "Show violation VIOL-COMPATIBILITY."],
    "FleetAnalysis": ["Show affected devices in the fleet.", "Analyze the fleet for conflicts.", "Which devices are non-compliant?", "How many devices have high risk?", "Summarize device group compliance."],
    "DeviceInvestigation": ["Show inventory for {device}.", "Inspect device {device}.", "Show device details for {device}.", "What is the device state of {device}?", "Display the inventory of {device}."],
    "RuleExplanation": ["Explain rule CRULE-FW-001.", "Why does rule CRULE-FW-001 exist?", "Show rule logic for CRULE-FW-001.", "What is the rule evidence for CRULE-FW-001?", "What does rule CRULE-FW-001 require?"],
    "VersionAnalysis": ["Which firmware version is required?", "What is the required version of BIOS?", "Show the minimum version for the driver.", "Which fixed version resolves the issue?", "What version range is supported?"],
    "LifecycleAnalysis": ["Is BIOS 2.1 still supported?", "When is firmware end of support?", "Show deprecated drivers.", "What is the lifecycle status of CRULE-FW-001?", "Which OS is at end of life?"],
    "UpgradeImpactAnalysis": ["What is the upgrade impact for {device}?", "Is {device} safe to upgrade?", "Check upgrade readiness for {device}.", "What happens if I upgrade BIOS to 2.1?", "Show the upgrade path for Firmware 3.2."],
}


def write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def build_patterns() -> list[dict]:
    subjects = ["BIOS", "firmware", "operating systems", "drivers", "security agents", "management tools"]
    patterns = []
    number = 1
    for intent, templates in PATTERN_TEMPLATES.items():
        for index in range(10):
            text = templates[index % len(templates)].format(device=f"Device{index + 1:03d}", subject=subjects[index % len(subjects)])
            patterns.append({"pattern_id": f"QP-{number:03d}", "query": text, "intent": intent,
                             "target_layers": ROUTES[intent], "coverage": "Hybrid" if len(ROUTES[intent]) > 1 else ROUTES[intent][0]})
            number += 1
    return patterns


def case(case_id: int, category: str, query: str, intent: str, layers: list[str], entities: dict | None = None) -> dict:
    return {"test_id": f"QUT-{case_id:03d}", "category": category, "query": query, "expected_intent": intent,
            "expected_entities": entities or {}, "expected_target_layers": layers}


def build_tests() -> list[dict]:
    cases = []
    subjects = [("BIOS", "bios"), ("firmware", "firmware"), ("operating system", "operating_system"), ("driver", "driver"), ("security agent", "security_component")]
    for i in range(50):
        subject, key = subjects[i % len(subjects)]
        query = [f"What is {subject}?", f"Define {subject}.", f"Describe {subject}.", f"Explain the concept of {subject}.", f"What are {subject} components?"][i % 5]
        cases.append(case(len(cases) + 1, "Layer1", query, "ConceptExplanation", ["Layer1"], {"component_types": [key]}))

    for i in range(50):
        device = f"Device{i + 101:03d}"
        if i % 2 == 0:
            query = [f"Show inventory for {device}.", f"Inspect device {device}.", f"Show device details for {device}."][i % 3]
            cases.append(case(len(cases) + 1, "Layer2", query, "DeviceInvestigation", ["Layer2"], {"device": device}))
        else:
            query = ["Show affected devices in the fleet.", "Analyze the fleet for conflicts.", "How many devices have high risk?", "Summarize device group compliance."][i % 4]
            cases.append(case(len(cases) + 1, "Layer2", query, "FleetAnalysis", ["Layer2"]))

    layer3_templates = [
        ("DependencyAnalysis", "What depends on BIOS?", {"component_types": ["bios"]}),
        ("CompatibilityInquiry", "Does BIOS 2.1 support Firmware 3.2?", {"bios": "2.1", "firmware": "3.2"}),
        ("RuleExplanation", "Explain rule CRULE-FW-001.", {"rule": "CRULE-FW-001"}),
        ("VersionAnalysis", "Which firmware version is required?", {"component_types": ["firmware"]}),
        ("LifecycleAnalysis", "Is BIOS 2.1 still supported?", {"bios": "2.1"}),
    ]
    for i in range(50):
        intent, query, entities = layer3_templates[i % len(layer3_templates)]
        cases.append(case(len(cases) + 1, "Layer3", query, intent, ["Layer3"], entities))

    hybrid_templates = [
        ("RootCauseAnalysis", "Why is {device} failing?"),
        ("ComplianceStatus", "What is the compliance status of {device}?"),
        ("RecommendationRequest", "How do I fix {device}?"),
        ("RiskAssessment", "Assess risk for {device}."),
        ("ViolationInvestigation", "Investigate violation VIOL-VERSION for {device}."),
        ("UpgradeImpactAnalysis", "Check upgrade readiness for {device}."),
    ]
    for i in range(100):
        intent, template = hybrid_templates[i % len(hybrid_templates)]
        device = f"Laptop{i + 201:03d}"
        entities = {"device": device}
        if intent == "ViolationInvestigation":
            entities["violation"] = "VIOL-VERSION"
        cases.append(case(len(cases) + 1, "Hybrid", template.format(device=device), intent, ["Layer2", "Layer3"], entities))
    return cases


def main() -> None:
    intents = [{"intent_id": a, "intent_name": b, "description": c, "expected_entities": d, "target_layers": e, "response_type": f}
               for a, b, c, d, e, f in INTENT_SPECS]
    entities = [{"entity_type": a, "description": b, "aliases": c} for a, b, c in ENTITY_SPECS]
    patterns = build_patterns()
    tests = build_tests()
    rules = {"version": VERSION, "intent_signals": SIGNALS, "intent_routes": ROUTES,
             "routing_policy": {"layer_order": ["Layer1", "Layer2", "Layer3"], "device_entity_adds": "Layer2", "rule_or_reasoning_entity_adds": "Layer3"}}
    write(BASE / "intent_catalog.json", intents)
    write(BASE / "entity_catalog.json", entities)
    write(BASE / "query_router_rules.json", rules)
    write(BASE / "query_patterns.json", patterns)
    write(BASE / "tests" / "query_understanding_test_cases.json", tests)
    manifest = {
        "manifest_id": "QUERY-UNDERSTANDING-PHASE2-V1", "version": VERSION, "created_date": DATE,
        "status": "generated_pending_validation", "intent_count": len(intents), "entity_count": len(entities),
        "pattern_count": len(patterns), "test_case_count": len(tests),
        "test_distribution": {name: sum(x["category"] == name for x in tests) for name in ("Layer1", "Layer2", "Layer3", "Hybrid")},
        "implementation_files": ["intent_classifier.py", "entity_extractor.py", "query_router.py", "query_parser.py", "query_understanding_service.py"],
        "consumers": ["Evidence Aggregation Layer", "Neo4j Retrieval Engine", "Qdrant Retrieval Engine", "Root Cause Engine", "Recommendation Engine"]
    }
    write(BASE / "query_understanding_manifest.json", manifest)
    print(json.dumps({"intents": len(intents), "entities": len(entities), "patterns": len(patterns), "tests": len(tests)}))


if __name__ == "__main__":
    main()
