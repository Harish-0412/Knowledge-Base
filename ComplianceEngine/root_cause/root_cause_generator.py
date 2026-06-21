import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT_CAUSE_DIR = Path(__file__).resolve().parent
SAMPLE_OUTPUT = ROOT_CAUSE_DIR / "sample_root_cause_records.json"
VALIDATION_REPORT = ROOT_CAUSE_DIR / "root_cause_validation_report.json"


RULE_CATALOG = [
    {
        "rule": "RULE-001",
        "expected": "Firmware >= 3.5",
        "actual_values": ["3.1", "3.2", "3.3", "3.4"]
    },
    {
        "rule": "RULE-002",
        "expected": "BIOS >= 1.28.0",
        "actual_values": ["1.22.0", "1.24.1", "1.25.0", "1.27.0"]
    },
    {
        "rule": "RULE-003",
        "expected": "Windows 11 23H2 or later",
        "actual_values": ["Windows 10 22H2", "Windows 11 22H2"]
    },
    {
        "rule": "RULE-004",
        "expected": "Intel AX211 Wi-Fi Driver >= 23.40.0.4",
        "actual_values": ["22.250.1.2", "23.20.0.4", "23.30.0.6"]
    },
    {
        "rule": "RULE-005",
        "expected": "Security Agent installed and active",
        "actual_values": ["Not installed", "Installed but inactive", "Agent service stopped"]
    },
    {
        "rule": "RULE-006",
        "expected": "TPM 2.0 enabled",
        "actual_values": ["TPM disabled", "TPM 1.2", "TPM not detected"]
    },
    {
        "rule": "RULE-007",
        "expected": "Secure Boot enabled",
        "actual_values": ["Disabled", "Unsupported", "Pending reboot"]
    },
    {
        "rule": "RULE-008",
        "expected": "Management tool version >= 5.3.0",
        "actual_values": ["4.12.0", "5.0.1", "5.2.1"]
    },
    {
        "rule": "RULE-009",
        "expected": "NVIDIA RTX Workstation Driver >= 552.55",
        "actual_values": ["535.183.01", "550.90.07", "551.86"]
    },
    {
        "rule": "RULE-010",
        "expected": "Ubuntu 22.04.4 LTS or later",
        "actual_values": ["Ubuntu 20.04.6 LTS", "Ubuntu 22.04.2 LTS"]
    }
]


def generate_root_cause_records(count: int = 100) -> List[Dict[str, Any]]:
    """Generate deterministic sample root cause API response records."""
    records: List[Dict[str, Any]] = []

    for idx in range(1, count + 1):
        device = f"Laptop{idx:03d}"
        finding_count = 1 + (idx % 3)
        findings = []

        for offset in range(finding_count):
            rule = RULE_CATALOG[(idx + offset) % len(RULE_CATALOG)]
            actual_values = rule["actual_values"]
            findings.append(
                {
                    "rule": rule["rule"],
                    "expected": rule["expected"],
                    "actual": actual_values[(idx + offset) % len(actual_values)]
                }
            )

        records.append(
            {
                "device": device,
                "status": "NON_COMPLIANT",
                "root_cause": findings
            }
        )

    return records


def validate_record(record: Dict[str, Any]) -> List[str]:
    errors: List[str] = []

    allowed_top_level = {"device", "status", "root_cause"}
    extra_keys = set(record) - allowed_top_level
    missing_keys = allowed_top_level - set(record)

    if extra_keys:
        errors.append(f"Unexpected top-level keys: {sorted(extra_keys)}")
    if missing_keys:
        errors.append(f"Missing top-level keys: {sorted(missing_keys)}")
        return errors

    if not isinstance(record["device"], str) or not record["device"].strip():
        errors.append("device must be a non-empty string")
    if record["status"] not in {"COMPLIANT", "NON_COMPLIANT"}:
        errors.append("status must be COMPLIANT or NON_COMPLIANT")
    if not isinstance(record["root_cause"], list):
        errors.append("root_cause must be an array")
        return errors
    if record["status"] == "NON_COMPLIANT" and not record["root_cause"]:
        errors.append("NON_COMPLIANT records must include at least one root cause")

    for index, finding in enumerate(record["root_cause"]):
        allowed_finding_keys = {"rule", "expected", "actual"}
        if not isinstance(finding, dict):
            errors.append(f"root_cause[{index}] must be an object")
            continue

        extra_finding_keys = set(finding) - allowed_finding_keys
        missing_finding_keys = allowed_finding_keys - set(finding)
        if extra_finding_keys:
            errors.append(f"root_cause[{index}] unexpected keys: {sorted(extra_finding_keys)}")
        if missing_finding_keys:
            errors.append(f"root_cause[{index}] missing keys: {sorted(missing_finding_keys)}")
            continue

        for field in ("rule", "expected", "actual"):
            if not isinstance(finding[field], str) or not finding[field].strip():
                errors.append(f"root_cause[{index}].{field} must be a non-empty string")
        if not finding["rule"].startswith("RULE-") or len(finding["rule"]) != 8:
            errors.append(f"root_cause[{index}].rule must match RULE-000 format")

    return errors


def validate_records(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    record_errors = []
    device_names = []

    for index, record in enumerate(records):
        device_names.append(record.get("device"))
        errors = validate_record(record)
        if errors:
            record_errors.append(
                {
                    "record_index": index,
                    "device": record.get("device"),
                    "errors": errors
                }
            )

    duplicate_devices = sorted(
        {
            device
            for device in device_names
            if device is not None and device_names.count(device) > 1
        }
    )

    return {
        "record_count": len(records),
        "expected_record_count": 100,
        "duplicate_devices": duplicate_devices,
        "invalid_records": record_errors,
        "status": "PASS" if len(records) == 100 and not duplicate_devices and not record_errors else "FAIL"
    }


def main() -> None:
    records = generate_root_cause_records(100)
    SAMPLE_OUTPUT.write_text(json.dumps(records, indent=2), encoding="utf-8")

    validation = validate_records(records)
    report = {
        "report_id": "ROOT-CAUSE-VALIDATION-001",
        "report_type": "root_cause_sample_validation",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_file": "ComplianceEngine/root_cause/root_cause_schema.json",
        "sample_file": "ComplianceEngine/root_cause/sample_root_cause_records.json",
        "validation": validation,
        "overall_status": validation["status"]
    }
    VALIDATION_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
