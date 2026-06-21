import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from neo4j_connection import Neo4jConnection

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def load_entity_index(conn: Neo4jConnection) -> Dict[str, str]:
    """Builds a lowercased name -> entity_id index from all Entity nodes in Neo4j.
    
    Returns:
        dict: Mapping of lowercase entity name -> entity_id
    """
    logger.info("Building Entity name index from Neo4j...")
    
    results = conn.execute_query(
        "MATCH (e:Entity) WHERE e.name IS NOT NULL RETURN e.entity_id AS entity_id, e.name AS name"
    )
    
    index = {}
    for row in results:
        name = row.get("name")
        entity_id = row.get("entity_id")
        if name and entity_id:
            index[name.strip().lower()] = entity_id.strip()
    
    logger.info(f"Indexed {len(index)} Entity node name(s) for matching.")
    return index

def resolve_match(component: dict, entity_index: Dict[str, str]) -> Optional[str]:
    """Attempts to match a ComponentInstance to an Entity using multiple fields.
    
    Match priority:
      1. component_name (exact, case-insensitive)
      2. component_family (exact, case-insensitive)
      3. value_normalized (exact, case-insensitive, underscore->space normalized)
    
    Returns:
        str: Matched entity_id, or None if unmatched
    """
    def normalize(s: str) -> str:
        return s.strip().lower().replace("_", " ").replace("-", " ")
    
    # Collect candidate match strings
    candidates = []
    
    comp_name = component.get("component_name")
    if comp_name and isinstance(comp_name, str) and comp_name.strip():
        candidates.append(("component_name", comp_name.strip().lower()))

    comp_family = component.get("component_family")
    if comp_family and isinstance(comp_family, str) and comp_family.strip():
        candidates.append(("component_family", comp_family.strip().lower()))

    value_norm = component.get("value_normalized")
    if value_norm and isinstance(value_norm, str) and value_norm.strip():
        candidates.append(("value_normalized", normalize(value_norm)))

    # Build a normalized entity index for flexible matching
    normalized_entity_index = {normalize(k): v for k, v in entity_index.items()}
    
    # Try each candidate field in order
    for field, candidate_value in candidates:
        # Direct lowercased match
        if candidate_value in entity_index:
            logger.info(f"[EXACT MATCH] '{candidate_value}' via field '{field}'")
            return entity_index[candidate_value]
        
        # Normalized match (underscore/dash handling)
        norm_candidate = normalize(candidate_value)
        if norm_candidate in normalized_entity_index:
            logger.info(f"[NORMALIZED MATCH] '{candidate_value}' -> '{norm_candidate}' via field '{field}'")
            return normalized_entity_index[norm_candidate]

    return None

def build_relationships(conn: Neo4jConnection) -> Tuple[int, List[dict], List[str]]:
    """Main logic: matches ComponentInstances to Entities and creates INSTANCE_OF relationships.

    Returns:
        Tuple of (mapped_count, unmatched_records, error_list)
    """
    errors = []
    unmatched = []
    mapped = 0

    # Load entity lookup index
    try:
        entity_index = load_entity_index(conn)
    except Exception as e:
        err_msg = f"Failed to build Entity index: {e}"
        logger.error(err_msg, exc_info=True)
        return 0, [], [err_msg]
    
    if not entity_index:
        logger.warning("Entity index is empty. No ontology entities available for matching. Ensure neo4j_loader.py has been run first.")
        return 0, [], []

    # Fetch all ComponentInstance nodes
    logger.info("Fetching all ComponentInstance nodes from Neo4j...")
    try:
        components = conn.execute_query(
            """
            MATCH (c:ComponentInstance)
            RETURN 
                c.component_instance_id AS component_instance_id,
                c.component_name AS component_name,
                c.component_family AS component_family,
                c.value_normalized AS value_normalized,
                c.component_type AS component_type
            """
        )
    except Exception as e:
        err_msg = f"Failed to fetch ComponentInstance nodes: {e}"
        logger.error(err_msg, exc_info=True)
        return 0, [], [err_msg]

    logger.info(f"Found {len(components)} ComponentInstance node(s) to process.")

    for comp in components:
        comp_inst_id = comp.get("component_instance_id")
        if not comp_inst_id:
            errors.append("Encountered ComponentInstance with null component_instance_id. Skipping.")
            continue

        # Attempt to resolve a matching Entity
        matched_entity_id = resolve_match(comp, entity_index)

        if matched_entity_id:
            # Create INSTANCE_OF relationship
            try:
                conn.execute_query(
                    """
                    MATCH (c:ComponentInstance {component_instance_id: $comp_id})
                    MATCH (e:Entity {entity_id: $entity_id})
                    MERGE (c)-[:INSTANCE_OF]->(e)
                    """,
                    {
                        "comp_id": comp_inst_id,
                        "entity_id": matched_entity_id
                    }
                )
                logger.info(f"Linked: {comp_inst_id} ('{comp.get('component_name')}') -[:INSTANCE_OF]-> {matched_entity_id}")
                mapped += 1
            except Exception as e:
                err_msg = f"Failed to create INSTANCE_OF relationship for {comp_inst_id}: {e}"
                logger.error(err_msg, exc_info=True)
                errors.append(err_msg)
        else:
            # Record unmatched
            logger.warning(f"No match found for ComponentInstance '{comp_inst_id}' ('{comp.get('component_name')}').")
            unmatched.append({
                "component_instance_id": comp_inst_id,
                "component_name": comp.get("component_name"),
                "component_family": comp.get("component_family"),
                "value_normalized": comp.get("value_normalized"),
                "component_type": comp.get("component_type")
            })

    return mapped, unmatched, errors

def generate_report(report_path: Path, mapped: int, unmapped: int, errors: List[str]) -> None:
    """Writes the inventory_mapping_report.json file."""
    report = {
        "mapped": mapped,
        "unmapped": unmapped,
        "errors": errors
    }
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Mapping report written to: {report_path}")
    except Exception as e:
        logger.error(f"Failed to write mapping report: {e}")

def save_unmatched(unmatched_path: Path, unmatched: List[dict]) -> None:
    """Writes unmatched component records to unmatched_inventory.json."""
    try:
        with open(unmatched_path, "w", encoding="utf-8") as f:
            json.dump(unmatched, f, indent=2)
        logger.info(f"Unmatched inventory written to: {unmatched_path} ({len(unmatched)} records)")
    except Exception as e:
        logger.error(f"Failed to write unmatched inventory: {e}")

def main() -> None:
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parents[1]

    mapping_report_path = project_root / "inventory_mapping_report.json"
    unmatched_path = project_root / "unmatched_inventory.json"

    conn = Neo4jConnection()
    mapped = 0
    unmatched = []
    errors = []

    try:
        conn.connect()
        mapped, unmatched, errors = build_relationships(conn)
    except Exception as e:
        err_msg = f"Fatal error in inventory relationship builder: {e}"
        logger.error(err_msg, exc_info=True)
        errors.append(err_msg)
    finally:
        conn.close()

    # Write outputs
    save_unmatched(unmatched_path, unmatched)
    generate_report(mapping_report_path, mapped, len(unmatched), errors)

    # Summary output
    print("=== Inventory Mapping Complete ===")
    print(f"Mapped (INSTANCE_OF created): {mapped}")
    print(f"Unmapped (no match found):    {len(unmatched)}")
    print(f"Errors:                       {len(errors)}")

if __name__ == "__main__":
    main()
