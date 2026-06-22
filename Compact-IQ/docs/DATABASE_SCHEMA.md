# DATABASE_SCHEMA — PostgreSQL

PostgreSQL is the source of truth.

## Core Tables

```sql
CREATE TABLE documents (
    document_id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    source_type TEXT NOT NULL,
    vendor TEXT,
    platform TEXT,
    document_status TEXT NOT NULL,
    uploaded_at TIMESTAMPTZ NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE document_chunks (
    chunk_id TEXT PRIMARY KEY,
    document_id TEXT REFERENCES documents(document_id) ON DELETE CASCADE,
    page_number INT,
    chunk_type TEXT,
    section_title TEXT,
    text TEXT NOT NULL,
    extraction_method TEXT,
    quality_score FLOAT,
    bbox JSONB,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE rule_candidates (
    candidate_id TEXT PRIMARY KEY,
    source_document_id TEXT REFERENCES documents(document_id),
    source_chunk_id TEXT REFERENCES document_chunks(chunk_id),
    rule_json JSONB NOT NULL,
    confidence_score FLOAT,
    review_status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE approved_rules (
    rule_id TEXT PRIMARY KEY,
    candidate_id TEXT REFERENCES rule_candidates(candidate_id),
    source_document_id TEXT REFERENCES documents(document_id),
    source_chunk_id TEXT REFERENCES document_chunks(chunk_id),
    rule_json JSONB NOT NULL,
    severity TEXT NOT NULL,
    reviewed_by TEXT,
    reviewed_at TIMESTAMPTZ,
    normalized_at TIMESTAMPTZ,
    tags TEXT[] DEFAULT '{}'
);

CREATE TABLE inventory_snapshots (
    inventory_snapshot_id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL,
    device_count INT,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE devices (
    device_id TEXT PRIMARY KEY,
    inventory_snapshot_id TEXT REFERENCES inventory_snapshots(inventory_snapshot_id),
    hostname TEXT NOT NULL,
    serial_number TEXT,
    asset_tag TEXT,
    device_type TEXT NOT NULL,
    manufacturer TEXT,
    model TEXT,
    model_normalized TEXT,
    department TEXT,
    location TEXT,
    owner_team TEXT,
    environment TEXT,
    lifecycle_status TEXT,
    last_seen_at TIMESTAMPTZ,
    readiness JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE device_components (
    component_instance_id TEXT PRIMARY KEY,
    device_id TEXT REFERENCES devices(device_id) ON DELETE CASCADE,
    component_type TEXT NOT NULL,
    component_name TEXT NOT NULL,
    component_family TEXT,
    vendor TEXT,
    version_raw TEXT,
    version_normalized TEXT,
    version_scheme TEXT,
    value_raw TEXT,
    value_normalized TEXT,
    status TEXT DEFAULT 'installed',
    install_date DATE,
    last_updated_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE compliance_scans (
    scan_id TEXT PRIMARY KEY,
    inventory_snapshot_id TEXT REFERENCES inventory_snapshots(inventory_snapshot_id),
    ruleset_version TEXT,
    scan_started_at TIMESTAMPTZ NOT NULL,
    scan_completed_at TIMESTAMPTZ,
    status TEXT NOT NULL,
    summary JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE compliance_results (
    scan_id TEXT REFERENCES compliance_scans(scan_id),
    device_id TEXT REFERENCES devices(device_id),
    compatibility_status TEXT NOT NULL,
    readiness_status TEXT NOT NULL,
    score INT NOT NULL,
    applicable_rule_count INT,
    violation_count INT,
    readiness_failure_count INT,
    rollout_recommendation TEXT,
    root_cause_summary TEXT,
    result_json JSONB NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (scan_id, device_id)
);

CREATE TABLE violations (
    violation_id TEXT PRIMARY KEY,
    scan_id TEXT REFERENCES compliance_scans(scan_id),
    device_id TEXT REFERENCES devices(device_id),
    rule_id TEXT REFERENCES approved_rules(rule_id),
    severity TEXT NOT NULL,
    violation_type TEXT,
    message TEXT,
    root_cause_candidate TEXT,
    source_chunk_id TEXT REFERENCES document_chunks(chunk_id),
    violation_json JSONB NOT NULL
);
```

## pgvector Tables

```sql
-- Requires: CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE chunk_embeddings (
    chunk_id TEXT PRIMARY KEY REFERENCES document_chunks(chunk_id) ON DELETE CASCADE,
    embedding VECTOR(768),
    embedding_model TEXT,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE rule_embeddings (
    rule_id TEXT PRIMARY KEY REFERENCES approved_rules(rule_id) ON DELETE CASCADE,
    embedding VECTOR(768),
    embedding_model TEXT,
    created_at TIMESTAMPTZ NOT NULL
);
```

## Recommended Indexes

```sql
CREATE INDEX idx_chunks_document ON document_chunks(document_id);
CREATE INDEX idx_rule_candidates_status ON rule_candidates(review_status);
CREATE INDEX idx_approved_rules_tags ON approved_rules USING GIN(tags);
CREATE INDEX idx_devices_model ON devices(manufacturer, model);
CREATE INDEX idx_devices_snapshot ON devices(inventory_snapshot_id);
CREATE INDEX idx_components_device ON device_components(device_id);
CREATE INDEX idx_components_type_version ON device_components(component_type, version_normalized);
CREATE INDEX idx_results_status ON compliance_results(compatibility_status, readiness_status);
CREATE INDEX idx_violations_rule ON violations(rule_id);
CREATE INDEX idx_violations_device ON violations(device_id);
```
