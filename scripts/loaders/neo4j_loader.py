import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, Set
from neo4j_connection import Neo4jConnection

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def sanitize_name(name: str) -> str:
    """Sanitizes string to prevent Cypher injection on labels."""
    return "".join(c for c in name if c.isalnum() or c == "_")

def prepare_entity_props(entity: dict) -> dict:
    """Dynamically extracts all fields from the entity JSON to be saved as properties."""
    clean_props = {}
    for k, v in entity.items():
        if isinstance(v, str):
            clean_props[k] = v.strip()
        else:
            clean_props[k] = v
    return clean_props

def chunk_list(lst: list, n: int):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def load_entity_file(
    conn: Neo4jConnection, 
    file_path: Path, 
    seen_entity_ids: Set[str], 
    all_fields_seen: Set[str],
    batch_size: int = 100
) -> Tuple[int, List[str]]:
    """Loads a single entity file in batches grouped by entity type."""
    loaded_count = 0
    errors = []

    logger.info(f"Processing file: {file_path.name}")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        err_msg = f"Failed to parse JSON file {file_path.name}: {e}"
        logger.error(err_msg)
        errors.append(err_msg)
        return 0, errors

    entities = [data] if isinstance(data, dict) else (data if isinstance(data, list) else [])
    
    # Group entities by sanitized type label for batching
    grouped_entities: Dict[str, List[dict]] = {}
    
    for entity in sorted(entities, key=lambda x: str(x.get("entity_id", ""))):
        if not isinstance(entity, dict):
            errors.append(f"Entity in {file_path.name} is not a JSON object.")
            continue
            
        entity_id = entity.get("entity_id")
        entity_type = entity.get("type")
        
        if not entity_id or not isinstance(entity_id, str) or not entity_id.strip():
            errors.append(f"Entity missing valid entity_id in {file_path.name}: {entity}")
            continue
            
        if not entity_type or not isinstance(entity_type, str) or not entity_type.strip():
            errors.append(f"Entity missing valid type in {file_path.name}: {entity}")
            continue

        eid_clean = entity_id.strip()
        
        # Track duplicate check (avoid multiple imports of same node in same session)
        if eid_clean in seen_entity_ids:
            logger.debug(f"Duplicate entity_id skipped: {eid_clean}")
            # Note: The prompt doesn't ask us to skip duplicates if they exist,
            # but it says "Existing nodes should be updated if properties are missing."
            # Therefore, we still want to load it to update its properties!
            # So, instead of skipping, we just process it.
            
        seen_entity_ids.add(eid_clean)
        
        # Keep track of all keys dynamically seen
        all_fields_seen.update(entity.keys())
        
        # Prepare properties dynamically
        props = prepare_entity_props(entity)
        sanitized_type = sanitize_name(entity_type.strip())
        
        if not sanitized_type:
            errors.append(f"Sanitized type is empty for entity_id {eid_clean}.")
            continue
            
        # Structure payload for batch
        payload = {
            "entity_id": eid_clean,
            "properties": props
        }
        
        grouped_entities.setdefault(sanitized_type, []).append(payload)

    # Load grouped entities in batches
    for label, batch_list in grouped_entities.items():
        for batch in chunk_list(batch_list, batch_size):
            try:
                # Merge on Entity base label, apply second label dynamically, and set properties dynamically
                query = f"""
                UNWIND $batch AS row
                MERGE (n:Entity {{entity_id: row.entity_id}})
                SET n:{label}
                SET n += row.properties
                """
                conn.execute_query(query, {"batch": batch})
                loaded_count += len(batch)
            except Exception as e:
                err_msg = f"Failed to execute batch load for label '{label}' in {file_path.name}: {e}"
                logger.error(err_msg, exc_info=True)
                errors.append(err_msg)

    logger.info(f"File {file_path.name} processed: {loaded_count} entities loaded.")
    return loaded_count, errors

def load_entities(conn: Neo4jConnection, entities_dir: Path) -> Tuple[int, int, List[str], List[str]]:
    """Loads all entities from the entities directory into Neo4j."""
    if not entities_dir.exists():
        err = f"Entities directory does not exist: {entities_dir}"
        logger.error(err)
        return 0, 0, [], [err]

    json_files = list(entities_dir.rglob("*.json"))
    files_processed = 0
    total_entities_loaded = 0
    all_errors = []
    
    seen_entity_ids: Set[str] = set()
    all_fields_seen: Set[str] = set()

    for file_path in json_files:
        files_processed += 1
        loaded, file_errors = load_entity_file(conn, file_path, seen_entity_ids, all_fields_seen)
        total_entities_loaded += loaded
        all_errors.extend(file_errors)

    return files_processed, total_entities_loaded, sorted(list(all_fields_seen)), all_errors

def generate_report(report_path: Path, fields_loaded: List[str], entities_loaded: int, errors: List[str]) -> None:
    """Generates the load_report.json with dynamically loaded fields list."""
    report = {
        "fields_loaded": fields_loaded,
        "entities_loaded": entities_loaded,
        "errors": errors
    }
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Load report generated at: {report_path}")
    except Exception as e:
        logger.error(f"Failed to generate load report: {e}")

def main() -> None:
    # Resolve paths relative to this script
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parents[1]
    
    entities_dir = project_root / "data" / "entities"
    report_path = project_root / "load_report.json"
    
    logger.info("Starting Neo4j Dynamic Entity Loader...")
    conn = Neo4jConnection()
    
    files_processed = 0
    entities_loaded = 0
    fields_loaded = []
    errors = []

    try:
        conn.connect()
        files_processed, entities_loaded, fields_loaded, errors = load_entities(conn, entities_dir)
    except Exception as e:
        err_msg = f"Fatal database loader failure: {e}"
        logger.error(err_msg, exc_info=True)
        errors.append(err_msg)
    finally:
        conn.close()

    # Generate output report file
    generate_report(report_path, fields_loaded, entities_loaded, errors)

    # Print requested status block
    print("=== Load Complete ===")
    print(f"Files Processed: {files_processed}")
    print(f"Entities Loaded: {entities_loaded}")
    print(f"Errors: {len(errors)}")

if __name__ == "__main__":
    main()
