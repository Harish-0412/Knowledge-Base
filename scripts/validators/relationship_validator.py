import os
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def load_relationship_types(ontology_path: Path) -> set:
    """Loads valid relationship types from the ontology file."""
    if not ontology_path.exists():
        logger.error(f"Ontology file not found at {ontology_path}")
        return set()
    try:
        with open(ontology_path, "r", encoding="utf-8") as f:
            ontology_data = json.load(f)
            return set(ontology_data.get("relationship_types", []))
    except Exception as e:
        logger.error(f"Failed to parse ontology file: {e}")
        return set()

def load_existing_entity_ids(entities_dir: Path) -> set:
    """Scans all JSON files in entities directory and collects all entity_ids."""
    entity_ids = set()
    if not entities_dir.exists():
        logger.warning(f"Entities directory does not exist at {entities_dir}")
        return entity_ids

    json_files = list(entities_dir.rglob("*.json"))
    for file_path in json_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Handle both single dictionary or list of dictionaries
            entities = [data] if isinstance(data, dict) else (data if isinstance(data, list) else [])
            for entity in entities:
                if isinstance(entity, dict):
                    eid = entity.get("entity_id")
                    if eid and isinstance(eid, str) and eid.strip():
                        entity_ids.add(eid.strip())
        except Exception as e:
            logger.warning(f"Could not load entity IDs from {file_path}: {e}")
            
    logger.info(f"Loaded {len(entity_ids)} unique entity ID(s) for cross-reference validation.")
    return entity_ids

def validate_relationships(relationships_dir: Path, valid_types: set, existing_entity_ids: set, project_root: Path) -> dict:
    """Validates all relationship JSON files in the relationships directory."""
    valid_relationships = []
    warnings = []
    errors = []

    if not relationships_dir.exists():
        msg = f"Relationships directory does not exist: {relationships_dir}"
        logger.warning(msg)
        warnings.append(msg)
        return {"valid": valid_relationships, "warnings": warnings, "errors": errors}

    json_files = list(relationships_dir.rglob("*.json"))
    logger.info(f"Found {len(json_files)} relationship JSON file(s) to validate.")

    required_fields = ["source", "relationship", "target"]

    for file_path in json_files:
        rel_path = file_path.relative_to(project_root)
        logger.info(f"Validating relationship file: {rel_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            err_msg = f"Failed to parse JSON file {rel_path}: {e}"
            logger.error(err_msg)
            errors.append({
                "file": str(rel_path),
                "error": "Invalid JSON syntax",
                "details": str(e)
            })
            continue

        # Handle both single relationship dict or list of relationship dicts
        if isinstance(data, dict):
            items_to_validate = [data]
        elif isinstance(data, list):
            items_to_validate = data
        else:
            err_msg = f"Root of JSON file {rel_path} must be an object or a list."
            logger.error(err_msg)
            errors.append({
                "file": str(rel_path),
                "error": "Invalid root structure",
                "details": err_msg
            })
            continue

        for idx, item in enumerate(items_to_validate):
            context = f"item at index {idx}" if isinstance(data, list) else "root object"
            
            if not isinstance(item, dict):
                errors.append({
                    "file": str(rel_path),
                    "context": context,
                    "error": "Relationship item is not a JSON object/dictionary."
                })
                continue

            item_errors = []

            # 1. Check for missing/empty fields
            for field in required_fields:
                if field not in item:
                    item_errors.append(f"Missing required field: '{field}'")
                else:
                    val = item[field]
                    if val is None or (isinstance(val, str) and not val.strip()):
                        item_errors.append(f"Field '{field}' is empty")

            source = item.get("source")
            rel_type = item.get("relationship")
            target = item.get("target")

            # 2. Check invalid relationship type
            if rel_type and isinstance(rel_type, str) and rel_type.strip():
                rel_type_clean = rel_type.strip()
                if rel_type_clean not in valid_types:
                    item_errors.append(f"Invalid relationship type: '{rel_type_clean}'. Must be one of: {sorted(list(valid_types))}")

            # 3. Check source node exists
            if source and isinstance(source, str) and source.strip():
                source_clean = source.strip()
                if source_clean not in existing_entity_ids:
                    item_errors.append(f"Source entity ID '{source_clean}' does not exist in data/entities/")

            # 4. Check target node exists
            if target and isinstance(target, str) and target.strip():
                target_clean = target.strip()
                if target_clean not in existing_entity_ids:
                    item_errors.append(f"Target entity ID '{target_clean}' does not exist in data/entities/")

            # Record errors or add to valid list
            if item_errors:
                logger.error(f"Validation error in {rel_path} ({context}): {'; '.join(item_errors)}")
                errors.append({
                    "file": str(rel_path),
                    "context": context,
                    "relationship": item,
                    "errors": item_errors
                })
            else:
                valid_relationships.append({
                    "source": source.strip() if isinstance(source, str) else source,
                    "relationship": rel_type.strip() if isinstance(rel_type, str) else rel_type,
                    "target": target.strip() if isinstance(target, str) else target
                })

    return {
        "valid": valid_relationships,
        "warnings": warnings,
        "errors": errors
    }

def main():
    # Resolve paths relative to this script
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parents[1]

    ontology_path = project_root / "ontology" / "relationship_types.json"
    entities_dir = project_root / "data" / "entities"
    relationships_dir = project_root / "data" / "relationships"
    report_path = project_root / "relationship_validation_report.json"

    logger.info(f"Loading relationship types ontology from {ontology_path}...")
    valid_types = load_relationship_types(ontology_path)

    logger.info(f"Loading existing entity IDs for integrity checks from {entities_dir}...")
    existing_entity_ids = load_existing_entity_ids(entities_dir)

    logger.info(f"Validating relationships from {relationships_dir}...")
    report = validate_relationships(relationships_dir, valid_types, existing_entity_ids, project_root)

    try:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Relationship validation report successfully written to {report_path}")
    except Exception as e:
        logger.error(f"Failed to write validation report to {report_path}: {e}")

if __name__ == "__main__":
    main()
