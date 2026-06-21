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

def validate_entities():
    # Resolve paths relative to this script
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parents[1]
    
    ontology_path = project_root / "ontology" / "node_types.json"
    entities_dir = project_root / "data" / "entities"
    report_path = project_root / "validation_report.json"
    
    logger.info(f"Ontology path: {ontology_path}")
    logger.info(f"Entities directory: {entities_dir}")
    
    # Load ontology node types
    if not ontology_path.exists():
        err_msg = f"Ontology file not found at {ontology_path}"
        logger.error(err_msg)
        report = {"valid": [], "warnings": [], "errors": [{"error": err_msg}]}
        write_report(report_path, report)
        return
        
    try:
        with open(ontology_path, "r", encoding="utf-8") as f:
            ontology_data = json.load(f)
            valid_node_types = set(ontology_data.get("node_types", []))
    except Exception as e:
        err_msg = f"Failed to parse ontology file: {e}"
        logger.error(err_msg)
        report = {"valid": [], "warnings": [], "errors": [{"error": err_msg}]}
        write_report(report_path, report)
        return

    required_fields = ["entity_id", "name", "type", "layer", "description"]
    
    valid_entities = []
    warnings = []
    errors = []
    
    seen_entity_ids = {}  # entity_id -> file_path
    
    if not entities_dir.exists():
        warnings.append(f"Entities directory does not exist: {entities_dir}")
        logger.warning(f"Entities directory does not exist: {entities_dir}")
    else:
        # Scan all JSON files in entities directory recursively
        json_files = list(entities_dir.rglob("*.json"))
        logger.info(f"Found {len(json_files)} JSON file(s) to validate.")
        
        for file_path in json_files:
            rel_path = file_path.relative_to(project_root)
            logger.info(f"Validating file: {rel_path}")
            
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
                
            # Handle both single entity dict or list of entity dicts
            if isinstance(data, dict):
                entities_to_validate = [data]
            elif isinstance(data, list):
                entities_to_validate = data
            else:
                err_msg = f"Root of JSON file {rel_path} must be an object or a list."
                logger.error(err_msg)
                errors.append({
                    "file": str(rel_path),
                    "error": "Invalid root structure",
                    "details": err_msg
                })
                continue
                
            for idx, entity in enumerate(entities_to_validate):
                context = f"item at index {idx}" if isinstance(data, list) else "root object"
                
                # Check required fields & empty values
                entity_errors = []
                
                # Keep track of individual required fields validation
                for field in required_fields:
                    if field not in entity:
                        entity_errors.append(f"Missing required field: '{field}'")
                    else:
                        val = entity[field]
                        if val is None or (isinstance(val, str) and not val.strip()):
                            entity_errors.append(f"Field '{field}' is empty")
                
                # Check node type validity if type is present and not empty
                node_type = entity.get("type")
                if node_type and isinstance(node_type, str) and node_type.strip():
                    if node_type not in valid_node_types:
                        entity_errors.append(f"Invalid node type: '{node_type}'. Must be one of: {sorted(list(valid_node_types))}")
                
                # Check duplicates if entity_id is present and not empty
                entity_id = entity.get("entity_id")
                if entity_id and isinstance(entity_id, str) and entity_id.strip():
                    eid_clean = entity_id.strip()
                    if eid_clean in seen_entity_ids:
                        entity_errors.append(f"Duplicate entity_id: '{eid_clean}' already defined in {seen_entity_ids[eid_clean]}")
                    else:
                        seen_entity_ids[eid_clean] = str(rel_path)
                
                # Record errors, warnings or validate
                if entity_errors:
                    logger.error(f"Validation error in {rel_path} ({context}): {'; '.join(entity_errors)}")
                    errors.append({
                        "file": str(rel_path),
                        "context": context,
                        "entity_id": entity_id,
                        "errors": entity_errors
                    })
                else:
                    valid_entities.append(entity_id)
                    
    # Generate the report
    report = {
        "valid": valid_entities,
        "warnings": warnings,
        "errors": errors
    }
    
    write_report(report_path, report)

def write_report(report_path, report):
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Validation report successfully written to {report_path}")
    except Exception as e:
        logger.error(f"Failed to write validation report: {e}")

if __name__ == "__main__":
    validate_entities()
