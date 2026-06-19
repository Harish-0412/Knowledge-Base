# Neo4j 1.1.0-rc2 Import

`entities.csv` contains stable entity nodes. `resolved_references.csv` contains validated staging references. `external_references.csv` preserves every non-resolved reference. `neo4j_constraints.cypher` creates non-destructive schema objects. `import_manifest.json` records counts and checksums.

Import order: constraints, entities, then resolved references. `RELATED_TO` is provisional and must not be treated as semantic truth. `entity_id` is the stable join key for future Qdrant payloads. Unresolved or deferred references must never become graph nodes automatically.

Configure Neo4j's import directory as `C:/SideQuest/KnowledgeBase/neo4j/import`, then run from this package directory (replace the database name if required):

```powershell
cypher-shell -d neo4j -f neo4j_constraints.cypher
cypher-shell -d neo4j "LOAD CSV WITH HEADERS FROM 'file:///v1.1-rc2/entities.csv' AS row CREATE (n:Entity {entity_id: row['entity_id:ID(Entity)'], name: row.name, normalized_name: row.normalized_name, type: row.type, subtype: row.subtype, layer: row.layer, knowledge_category: row.knowledge_category, aliases: row.aliases, concept_scope: row.concept_scope, vendor: CASE row.vendor WHEN '' THEN null ELSE row.vendor END, verification_status: row.verification_status, source_file: row.source_file, status: row.status}) FOREACH (_ IN CASE row.knowledge_category WHEN 'Firmware' THEN [1] ELSE [] END | SET n:Firmware) FOREACH (_ IN CASE row.knowledge_category WHEN 'Operating System' THEN [1] ELSE [] END | SET n:OperatingSystem) FOREACH (_ IN CASE row.knowledge_category WHEN 'Driver' THEN [1] ELSE [] END | SET n:Driver) FOREACH (_ IN CASE row.knowledge_category WHEN 'Security' THEN [1] ELSE [] END | SET n:SecurityComponent) FOREACH (_ IN CASE row.knowledge_category WHEN 'Management' THEN [1] ELSE [] END | SET n:ManagementTool)"
cypher-shell -d neo4j "LOAD CSV WITH HEADERS FROM 'file:///v1.1-rc2/resolved_references.csv' AS row MATCH (source:Entity {entity_id: row[':START_ID(Entity)']}), (target:Entity {entity_id: row[':END_ID(Entity)']}) CREATE (source)-[:RELATED_TO {reference_value: row.reference_value, resolution_method: row.resolution_method}]->(target)"
```

Migration from v1.0 preserves existing IDs and adds 30 entities. Known warnings are recorded in the release validation report.
