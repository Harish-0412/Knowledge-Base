# Compatibility Neo4j Connection Guide

## Purpose

This guide connects a human-approved Compatibility Layer release to Neo4j. It does not authorize approval, create a Phase 10 release, or execute an import automatically.

The current Phase 11 gate is blocked while Phase 9 decisions remain pending. Check:

```powershell
Get-Content CompatibilityLayer\releases\v1.0\phase10_release_readiness.json
Get-Content neo4j\import\compatibility-v1.0\phase11_readiness.json
```

Proceed only when Phase 10 is `RELEASED` and Phase 11 is `READY_FOR_CONTROLLED_IMPORT`.

## Connection Configuration

Use environment variables or a secret manager. Never commit credentials.

```powershell
$env:NEO4J_URI = "neo4j+s://your-instance.databases.neo4j.io"
$env:NEO4J_USERNAME = "neo4j"
$env:NEO4J_PASSWORD = "<secret>"
$env:NEO4J_DATABASE = "compatiq_staging"
```

For a local server, the URI is commonly `neo4j://localhost:7687`. TLS-enabled hosted environments should use `neo4j+s://`.

Test connectivity with Neo4j Browser, `cypher-shell`, or the official driver:

```powershell
cypher-shell -a $env:NEO4J_URI -u $env:NEO4J_USERNAME -p $env:NEO4J_PASSWORD -d $env:NEO4J_DATABASE "RETURN 1 AS connected"
```

Expected result: `connected = 1`.

## Package Verification

Generate the Phase 11 package with:

```powershell
python scripts\build_phase11_neo4j_package.py
```

Verify every SHA-256 value in `neo4j/import/compatibility-v1.0/import_manifest.json` before copying files to Neo4j's import directory. Confirm the manifest is ready, every rule is human approved, every predicate file is statically allowlisted, no `RELATED_TO` edge exists, and all referenced Layer 1 entities are present.

## Staging Import

Back up the target and import into a staging database first. Copy the complete `compatibility-v1.0` directory into Neo4j's configured import directory.

```powershell
cypher-shell -a $env:NEO4J_URI -u $env:NEO4J_USERNAME -p $env:NEO4J_PASSWORD -d $env:NEO4J_DATABASE -f neo4j\import\compatibility-v1.0\neo4j_constraints.cypher
cypher-shell -a $env:NEO4J_URI -u $env:NEO4J_USERNAME -p $env:NEO4J_PASSWORD -d $env:NEO4J_DATABASE -f neo4j\import\compatibility-v1.0\import_compatibility_rules.cypher
cypher-shell -a $env:NEO4J_URI -u $env:NEO4J_USERNAME -p $env:NEO4J_PASSWORD -d $env:NEO4J_DATABASE -f neo4j\import\compatibility-v1.0\validate_import.cypher
```

The generated Cypher uses fixed relationship labels and never evaluates a relationship type supplied by CSV data.

## Graph Mapping

- Each approved rule becomes a `CompatibilityRule` node.
- `(:CompatibilityRule)-[:TARGETS]->(:Entity)` identifies the governed subject.
- A static predicate edge from the rule to the object entity represents the rule assertion.
- Conditions, exceptions, evidence, and remediation remain canonical JSON properties.
- Approval actor, approval time, release version, confidence, and provenance remain queryable.

## Acceptance Queries

```cypher
MATCH (rule:CompatibilityRule) RETURN count(rule) AS rule_count;
```

The result must equal the Phase 11 manifest count.

```cypher
MATCH (rule:CompatibilityRule)
WHERE rule.status <> 'approved'
RETURN rule.rule_id, rule.status;
```

Expected: no rows.

```cypher
MATCH (rule:CompatibilityRule)
WHERE NOT (rule)-[:TARGETS]->(:Entity)
RETURN rule.rule_id;
```

Expected: no rows.

```cypher
MATCH (rule:CompatibilityRule)-[relationship]->()
WHERE type(relationship) = 'RELATED_TO'
RETURN rule.rule_id;
```

Expected: no rows.

## Production Promotion

Promote only after staging counts, endpoints, approval properties, predicates, and checksums match the manifest. Record the database backup identifier, operator, timestamp, Phase 10 release checksum, Phase 11 manifest checksum, and validation output.

The repository does not connect to or mutate the live database. Production execution remains an explicit operator action.

## Rollback

Prefer restoring the pre-import backup. For a controlled batch rollback, remove only rules from the exact release version after approval:

```cypher
MATCH (rule:CompatibilityRule {release_version: $releaseVersion})
DETACH DELETE rule;
```

Verify `$releaseVersion` against the manifest before execution. Never delete canonical `Entity` nodes as part of a compatibility-rule rollback.
