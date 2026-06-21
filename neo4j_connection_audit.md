# Neo4j Connection Audit

Generated: 2026-06-21  
Scope:

- `ReasoningLayer/evidence_aggregation/connectors/neo4j_connector.py`
- `ReasoningLayer/llm/connectors/neo4j_connector.py`
- `.env`
- `.env.example`

No business logic was modified.

## Executive Summary

Neo4j connectivity is working, but the configured application database is wrong.

Current `.env` config sets:

```text
NEO4J_DATABASE=endpoint-kb
```

Live Neo4j databases found:

```text
neo4j   online
system  online
```

Result:

```text
Configured database endpoint-kb does not exist.
Actual available application database is neo4j.
```

## Connector Configuration Behavior

### Evidence Aggregation Connector

File:

```text
ReasoningLayer/evidence_aggregation/connectors/neo4j_connector.py
```

Observed behavior:

```python
load_dotenv(ROOT / ".env")
self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
self.user = user or os.getenv("NEO4J_USERNAME", os.getenv("NEO4J_USER", "neo4j"))
self.password = password if password is not None else os.getenv("NEO4J_PASSWORD", "")
self.database = database or os.getenv("NEO4J_DATABASE", "neo4j")
```

This connector:

- supports `NEO4J_USERNAME`
- falls back to `NEO4J_USER`
- defaults database to `neo4j`
- uses `.env`
- returns empty query results if Neo4j query execution fails

### LLM Neo4j Connector

File:

```text
ReasoningLayer/llm/connectors/neo4j_connector.py
```

Observed behavior:

```python
_load_root_env()
self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
self.username = os.getenv("NEO4J_USERNAME", os.getenv("NEO4J_USER", "neo4j"))
self.password = os.getenv("NEO4J_PASSWORD", "")
self.database = os.getenv("NEO4J_DATABASE", "neo4j")
```

This connector:

- supports `NEO4J_USERNAME`
- falls back to `NEO4J_USER`
- defaults database to `neo4j`
- uses root `.env`
- fails health check if configured database does not exist

## Environment Variable Audit

### `.env`

Values redacted where sensitive.

| Variable | Present | Observed Value |
|---|---:|---|
| `NEO4J_URI` | yes | `bolt://localhost:7687` |
| `NEO4J_USERNAME` | yes | `neo4j` |
| `NEO4J_PASSWORD` | yes | `<REDACTED>` |
| `NEO4J_DATABASE` | yes | `endpoint-kb` |

Additional observation:

- `.env` contains duplicated `NEO4J_URI`, `NEO4J_USERNAME`, and `NEO4J_PASSWORD` entries.
- The duplicated values appear equivalent, so the duplicate entries are untidy but not the current failure cause.
- The failure cause is `NEO4J_DATABASE=endpoint-kb`.

### `.env.example`

Observed:

```text
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here
```

Issue:

- `.env.example` uses `NEO4J_USER`.
- Current connectors support `NEO4J_USER` as a fallback, but the preferred variable used by `.env` and most code is `NEO4J_USERNAME`.
- `.env.example` does not document `NEO4J_DATABASE`.

Recommended `.env.example` shape:

```text
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password_here
NEO4J_DATABASE=neo4j
```

## Live Neo4j Verification

Read-only verification was performed using the configured credentials.

### Connectivity

```text
PASS
```

Neo4j is reachable at:

```text
bolt://localhost:7687
```

### Database list

```text
neo4j   online
system  online
```

### Configured database test

Configured database:

```text
endpoint-kb
```

Result:

```text
FAIL
Database does not exist. Database name: 'endpoint-kb'.
```

### Actual available application database test

Database:

```text
neo4j
```

Result:

```text
PASS
RETURN 1 AS result → 1
```

## Actual Neo4j Database Name

The actual available application database is:

```text
neo4j
```

The configured database is:

```text
endpoint-kb
```

The configured database does not exist.

## Exact Fix

Recommended fix for the current environment:

```text
Set NEO4J_DATABASE=neo4j in .env
```

Exact `.env` line to use:

```text
NEO4J_DATABASE=neo4j
```

Why this is the correct fix:

- Neo4j is reachable.
- Credentials work.
- The database `neo4j` exists and accepts queries.
- The database `endpoint-kb` does not exist.

## Alternative Fix

If the intended architecture requires a separate database named `endpoint-kb`, create it first.

For Neo4j Enterprise / multi-database environments:

```cypher
CREATE DATABASE `endpoint-kb` IF NOT EXISTS;
```

Then keep:

```text
NEO4J_DATABASE=endpoint-kb
```

Important:

- Neo4j Community Edition generally uses the default `neo4j` database.
- If running Community Edition, prefer `NEO4J_DATABASE=neo4j`.

## Impact on ReasoningLayer

Current impact:

- `ReasoningLayer/evidence_aggregation/connectors/neo4j_connector.py` can connect to the server, but Layer 2 retrieval queries fail because sessions are opened against `endpoint-kb`.
- `ReasoningLayer/llm/connectors/neo4j_connector.py` health checks fail for the same reason.
- Evidence retrieval for questions like `Why is Laptop001 non-compliant?` returns no Neo4j inventory evidence.

Expected result after setting:

```text
NEO4J_DATABASE=neo4j
```

The connectors should be able to execute queries against the default database, assuming the inventory graph has been loaded into `neo4j`.

## Final Status

```text
AUDIT STATUS: FAIL
```

Reason:

```text
Configured database endpoint-kb does not exist.
```

Recommended action:

```text
Change NEO4J_DATABASE to neo4j, or create endpoint-kb before using it.
```

