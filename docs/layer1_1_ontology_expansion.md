# Layer 1.1 ontology expansion

## Scope and result

`reports/unmapped_components.json` contains 123 records and 17 unique `(component_type, component_name)` pairs. Forty records are inventory-only metadata (`Device Model` and `Device Type`) and are deliberately excluded. The remaining 83 records resolve to 15 new technology entities in `data/layer1/entity_expansion.csv`.

No row in `data/layer1/entities.csv` is changed. The expansion is additive and contains no duplicate entity ID, name, or normalized name relative to the base ontology.

## Merge strategy

Run from the repository root:

```powershell
python scripts/merge_layer1_1_entities.py
```

This produces `data/layer1/entities_v1_1.csv` with the Neo4j bulk-import headers used by the current base file. The script:

1. preserves all 54 base rows and their order;
2. validates the required 13-column expansion schema;
3. rejects duplicate IDs, names, and normalized names across both inputs;
4. converts `entity_id` to `entity_id:ID(Entity)` and derives `:LABEL` as `Entity;<type>`; and
5. appends the 15 new rows, yielding 69 entities.

## Neo4j reload

Back up the database before a reload. The current loader reads only `data/layer1/entities.csv`, so use a temporary path override or copy `entities_v1_1.csv` to the configured import location. Do not overwrite the base ontology source file.

For a clean Layer 1/Layer 2 rebuild, run the existing constraint and loader workflow with `entities_v1_1.csv` as the Layer 1 input, then reload device inventory. For an additive refresh, load the 15 expansion rows with the same `MERGE (e:Entity {entity_id: row.entity_id})` behavior used by `layer1_entity_loader.py`.

After the entities are present, rebuild `INSTANCE_OF` relationships using normalized exact-name matching before the existing category fallback logic:

```cypher
MATCH (c:ComponentInstance)
WHERE NOT (c)-[:INSTANCE_OF]->(:Entity)
WITH c, toLower(trim(c.component_name)) AS component_name
MATCH (e:Entity)
WHERE e.normalized_name = component_name
MERGE (c)-[:INSTANCE_OF]->(e);
```

Then run the existing inventory mapper to retain its generic mappings and verify:

```cypher
MATCH (c:ComponentInstance)
RETURN count(c) AS total,
       count { (c)-[:INSTANCE_OF]->(:Entity) } AS mapped,
       count(c) - count { (c)-[:INSTANCE_OF]->(:Entity) } AS unmapped;
```

Expected result for the supplied inventory is 262 total, 222 mapped, and 40 unmapped. The 40 remaining records are the intentionally excluded Device Model and Device Type metadata. This estimate assumes component names in Neo4j match the supplied report and the exact-name mapping query is executed; merely re-running the current Python mapper will not map the new categories.
