# Relationship Ontology v1.0 Test Fixtures

## Safety Notice

Everything in this directory is synthetic test data. These fixtures are not production knowledge, do not establish facts about RC2 entities, and must never be imported into Neo4j. The manifest sets `production_import_allowed` to `false`.

## Purpose

The fixtures provide deterministic inputs for the future Python relationship validator. They exercise JSON Schema behavior, registry identity, registered predicates, domain/range rules, evidence and condition policies, confidence thresholds, approval, duplicates, cycles, contradictions, collection behavior, and production-import rejection.

Actual RC2 entity IDs are used in valid examples so future tests can verify that endpoints exist and satisfy category/type rules. Their presence does not make the synthetic statement true. Every statement explicitly identifies itself as a synthetic fixture assertion.

## Files

- `valid_relationships.json`: schema-valid, rule-valid synthetic records.
- `invalid_relationships.json`: isolated invalid cases with expected error codes.
- `example_manifest.json`: calculated counts and coverage for both files.
- `README.md`: fixture handling and extension instructions.

## Valid Fixture Structure

The valid file has a test-only container with release metadata, calculated coverage, and a `relationships` array. Objects inside `relationships` conform exactly to `relationship_record.schema.json`; no fixture-only fields are inserted into individual relationship records.

Valid fixtures cover every registered predicate, every assertion scope, both `ALL` and `ANY`, every condition operator, every evidence source type, and all approval and verification states. Confidence values meet each predicate's configured minimum. Valid high-risk fixtures contain synthetic authoritative evidence.

## Invalid Case Structure

Each item in `cases` contains:

- `case_id`: deterministic `INVALID-CASE-NNN` identifier.
- `title` and `description`: the intended failure scenario.
- `validation_layer`: where the future validator should detect it.
- `expected_valid`: always false.
- `expected_error_codes`: the exact expected standardized codes.
- `records`: one or more relationship-record-like objects.

`validation_layer` identifies JSON Schema, registry, relationship type, domain/range, evidence, conditions, confidence, approval, duplicate, cycle, contradiction, or collection validation. Schema-layer records may intentionally violate the record schema. Rule-level records are usually schema-valid so the intended semantic failure remains isolated.

## Collection-Level Cases

Duplicates, cycles, reciprocal relationships, and contradictions require multiple records. Their validity cannot be determined by validating each record independently. The future validator must canonicalize conditions, build the relevant entity-predicate graph, and evaluate the records as a collection.

Condition object-key order is ignored for duplicate identity, while array meaning is preserved. Conditions are data and are never executed.

## Synthetic Evidence

Fixture evidence uses synthetic URNs and test titles. Authoritative-policy tests may use `official_documentation`, `industry_standard`, or `vendor_documentation` with the title `Synthetic authoritative evidence fixture`. This is allowed only so tests can exercise evidence-policy branches.

Synthetic evidence can never satisfy production governance. The future validator must recognize it as fixture-only based on the examples directory and test manifest. No real source or URL is implied.

## Future Validator Use

The validator should:

1. Load the record schema, type catalog, rules, and registry.
2. Validate each valid fixture at schema and rule layers.
3. Confirm every valid fixture remains valid.
4. Validate each invalid case at its declared layer.
5. Compare emitted error codes with `expected_error_codes`.
6. Evaluate multi-record cases as collections.
7. Refuse any production import attempt involving these fixtures.

## Adding a Valid Example

1. Use the next `REL-EXAMPLE-NNN` ID.
2. Use existing RC2 entity IDs and a registered predicate.
3. Check source/target category and type allowlists.
4. Meet inherited condition, evidence, confidence, and scope policies.
5. Prefix the statement with synthetic fixture wording.
6. Use only synthetic evidence IDs, titles, URNs, locators, and notes.
7. Avoid self-relationships, duplicates, forbidden cycles, and contradictions.
8. Recalculate all coverage and manifest fields.

## Adding an Invalid Case

1. Use the next `INVALID-CASE-NNN` and `REL-INVALID-NNN-NN` IDs.
2. Design the case around one validation behavior where possible.
3. Keep unrelated fields valid to avoid cascading failures.
4. Select the correct `validation_layer`.
5. List only error codes the case is designed to trigger.
6. Include all records required for collection behavior.
7. Recalculate error-code coverage and manifest counts.

Fixture identifiers are zero-padded and deterministic. Do not use runtime timestamps, random UUIDs, real evidence URLs, or production relationship IDs.

## Neo4j Prohibition

These files are absent from every Neo4j production import manifest. They must not be copied into import pipelines, transformed into semantic edges, or interpreted as approved knowledge. `RELATED_TO` staging data is not converted by these fixtures.
