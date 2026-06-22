# SCHEMAS — CompatIQ Canonical Contracts

All modules must use these schemas. These are the fixed integration contracts for the project.

## 1. IDs and Naming Rules

| Entity | Format |
|---|---|
| Document | `DOC-000001` |
| Chunk | `CHUNK-000001` |
| Rule candidate | `RCAND-000001` |
| Approved rule | `RULE-000001` |
| Inventory snapshot | `INV-000001` |
| Device | `DEV-000001` |
| Component instance | `COMP-000001` |
| Scan | `SCAN-000001` |
| Violation | `VIO-000001` |
| Remediation step | `REM-000001` |

## 2. Enums

### component_type

```json
[
  "bios", "cpu", "os", "firmware", "driver", "agent", "management_tool",
  "hba", "raid_controller", "network_adapter", "storage_controller",
  "virtualization_feature", "tpm", "model", "device_type", "hardware_revision",
  "readiness", "unknown"
]
```

### operator

```json
["installed", "exists", "not_exists", "==", "!=", ">=", "<=", ">", "<", "matches", "in", "not_in"]
```

### rule_type

```json
[
  "min_version_constraint",
  "max_version_constraint",
  "exact_version_constraint",
  "incompatible_combination",
  "feature_support_added",
  "known_issue_fixed",
  "deprecated_after",
  "update_order_constraint",
  "readiness_requirement"
]
```

### severity

```json
["info", "warning", "critical", "blocker"]
```

### review_status

```json
["pending_review", "approved", "edited", "rejected", "needs_clarification"]
```

### compatibility_status

```json
["compliant", "warning", "critical", "blocked", "unknown"]
```

### readiness_status

```json
["ready", "not_ready", "unknown"]
```

### rollout_recommendation

```json
["safe_for_ring_1", "safe_after_remediation", "blocked", "needs_review"]
```

## 3. Document Schema

```json
{
  "document_id": "DOC-000001",
  "filename": "R420_BIOS_Release_Notes.pdf",
  "source_type": "pdf",
  "vendor": "Dell",
  "platform": "Dell PowerEdge R420",
  "document_status": "uploaded",
  "uploaded_at": "2026-06-19T10:00:00Z",
  "metadata": {}
}
```

## 4. Document Chunk Schema

```json
{
  "chunk_id": "CHUNK-000001",
  "document_id": "DOC-000001",
  "page_number": 4,
  "chunk_type": "release_note_bullet",
  "section_title": "BIOS Version 02.04.02",
  "text": "Corrected an issue where VMware ESXi 5.1.x, QLE24xx cards stop responding during disk I/O...",
  "extraction_method": "pymupdf",
  "quality_score": 0.94,
  "bbox": null,
  "created_at": "2026-06-19T10:05:00Z"
}
```

## 5. Condition Schema

```json
{
  "condition_id": "COND-000001",
  "component_type": "cpu",
  "component_name": "Intel Xeon",
  "component_family": "E5-2400 V2",
  "vendor": "Intel",
  "operator": "installed",
  "value_raw": "Intel Xeon E5-2400 V2 family",
  "value_normalized": "intel_xeon_e5_2400_v2",
  "version_raw": null,
  "version_normalized": null,
  "version_scheme": null,
  "metadata": {}
}
```

## 6. Requirement Schema

```json
{
  "requirement_id": "REQ-000001",
  "component_type": "bios",
  "component_name": "System BIOS",
  "component_family": null,
  "operator": ">=",
  "value_raw": null,
  "value_normalized": null,
  "version_raw": "02.04.02",
  "version_normalized": "2.4.2",
  "version_scheme": "semantic",
  "requirement_kind": "min_version",
  "metadata": {}
}
```

## 7. Rule Candidate Schema

```json
{
  "candidate_id": "RCAND-000001",
  "source_document_id": "DOC-000001",
  "source_chunk_id": "CHUNK-000001",
  "source_page": 4,
  "source_excerpt": "Corrected an issue where VMware ESXi 5.1.x, QLE24xx cards stop responding...",
  "rule_type": "known_issue_fixed",
  "condition_logic": "AND",
  "conditions": [],
  "requirements": [],
  "exceptions": [],
  "severity": "critical",
  "confidence_score": 0.7,
  "confidence_reason": "Known issue fix implies BIOS version requirement for the matching configuration.",
  "review_status": "pending_review",
  "remediation_hint": "Update BIOS to 02.04.02 or later before rollout.",
  "tags": ["bios", "vmware", "hba"],
  "created_at": "2026-06-19T10:10:00Z"
}
```

## 8. Approved Rule Schema

Approved rules use the same logical fields as candidates, but have a stable `rule_id`, review metadata, and normalized fields.

```json
{
  "rule_id": "RULE-000001",
  "candidate_id": "RCAND-000001",
  "source_document_id": "DOC-000001",
  "source_chunk_id": "CHUNK-000001",
  "source_page": 4,
  "source_excerpt": "Corrected an issue where VMware ESXi 5.1.x, QLE24xx cards stop responding...",
  "rule_type": "known_issue_fixed",
  "condition_logic": "AND",
  "conditions": [],
  "requirements": [],
  "exceptions": [],
  "severity": "critical",
  "confidence_score": 0.7,
  "review_status": "approved",
  "reviewed_by": "endpoint_engineer",
  "reviewed_at": "2026-06-19T10:20:00Z",
  "normalized_at": "2026-06-19T10:20:10Z",
  "remediation_hint": "Update BIOS to 02.04.02 or later before rollout.",
  "tags": ["bios", "vmware", "hba"]
}
```

## 9. Inventory Snapshot Schema

```json
{
  "inventory_snapshot_id": "INV-000001",
  "source_name": "mock_cmdb_generator",
  "generated_at": "2026-06-19T10:30:00Z",
  "device_count": 200,
  "metadata": {}
}
```

## 10. Device Schema

```json
{
  "device_id": "DEV-000001",
  "inventory_snapshot_id": "INV-000001",
  "hostname": "prod-r420-001",
  "serial_number": "SN-R420-0001",
  "asset_tag": "ASSET-0001",
  "device_type": "server",
  "manufacturer": "Dell",
  "model": "PowerEdge R420",
  "model_normalized": "dell_poweredge_r420",
  "department": "Infrastructure",
  "location": "DC-Rack-05",
  "owner_team": "Platform SRE",
  "environment": "production",
  "lifecycle_status": "active",
  "last_seen_at": "2026-06-19T09:30:00Z",
  "components": [],
  "readiness": {},
  "metadata": {}
}
```

## 11. Device Component Schema

```json
{
  "component_instance_id": "COMP-000001",
  "device_id": "DEV-000001",
  "component_type": "bios",
  "component_name": "System BIOS",
  "component_family": null,
  "vendor": "Dell",
  "version_raw": "02.00.21",
  "version_normalized": "2.0.21",
  "version_scheme": "semantic",
  "value_raw": null,
  "value_normalized": null,
  "status": "installed",
  "install_date": "2026-01-15",
  "last_updated_at": "2026-01-15T02:30:00Z",
  "metadata": {}
}
```

## 12. Readiness Schema

```json
{
  "agent_health": "healthy",
  "pending_reboot": false,
  "disk_free_gb": 64,
  "battery_percent": null,
  "ac_power_connected": true,
  "bitlocker_suspended": true,
  "maintenance_window_available": true,
  "network_reachable": true,
  "last_seen_within_hours": 2,
  "metadata": {}
}
```

## 13. Compliance Scan Schema

```json
{
  "scan_id": "SCAN-000001",
  "inventory_snapshot_id": "INV-000001",
  "ruleset_version": "ruleset-2026-06-19-001",
  "scan_started_at": "2026-06-19T11:00:00Z",
  "scan_completed_at": "2026-06-19T11:00:15Z",
  "status": "completed",
  "summary": {
    "total_devices": 200,
    "compliant": 120,
    "warning": 35,
    "critical": 30,
    "blocked": 10,
    "unknown": 5,
    "not_ready": 28
  }
}
```

## 14. Compliance Result Schema

```json
{
  "scan_id": "SCAN-000001",
  "device_id": "DEV-000001",
  "compatibility_status": "critical",
  "readiness_status": "ready",
  "score": 58,
  "applicable_rule_count": 3,
  "violation_count": 1,
  "readiness_failure_count": 0,
  "rollout_recommendation": "safe_after_remediation",
  "violations": [],
  "readiness_failures": [],
  "root_cause_summary": "BIOS version is below the minimum required version.",
  "generated_at": "2026-06-19T11:00:15Z"
}
```

## 15. Violation Schema

```json
{
  "violation_id": "VIO-000001",
  "scan_id": "SCAN-000001",
  "device_id": "DEV-000001",
  "rule_id": "RULE-000001",
  "severity": "critical",
  "violation_type": "requirement_failed",
  "observed_component_type": "bios",
  "observed_value_raw": "02.00.21",
  "observed_value_normalized": "2.0.21",
  "expected_component_type": "bios",
  "expected_operator": ">=",
  "expected_value_raw": "02.04.02",
  "expected_value_normalized": "2.4.2",
  "message": "BIOS 02.00.21 is below required version 02.04.02.",
  "root_cause_candidate": "BIOS version is below the minimum required version.",
  "source_chunk_id": "CHUNK-000001",
  "remediation_steps": []
}
```

## 16. Remediation Step Schema

```json
{
  "step_id": "REM-000001",
  "order": 1,
  "action_type": "update_component",
  "target_component_type": "bios",
  "from_version": "02.00.21",
  "to_version": "02.04.02 or later",
  "reason": "Required before this configuration is considered compatible.",
  "is_simulated": true
}
```

## 17. Graph Export Schema

```json
{
  "graph_id": "GRAPH-DEV-000001",
  "graph_type": "device_violation_explanation",
  "nodes": [
    {
      "id": "DEV-000001",
      "type": "device",
      "label": "prod-r420-001",
      "data": {}
    }
  ],
  "edges": [
    {
      "id": "EDGE-000001",
      "source": "DEV-000001",
      "target": "RULE-000001",
      "type": "VIOLATES",
      "label": "violates",
      "data": {}
    }
  ]
}
```
