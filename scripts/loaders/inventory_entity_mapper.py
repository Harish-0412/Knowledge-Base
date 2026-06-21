import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add script directory to sys.path to find neo4j_connection
script_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(script_dir))
from neo4j_connection import Neo4jConnection

BATCH_SIZE = 50

def normalize_lookup_name(value: object) -> str:
    """Normalizes an entity or component name for exact-name lookup."""
    return " ".join(str(value or "").strip().casefold().split())


def get_target_entity_name(comp_type: str, comp_name: str) -> str | None:
    """Classifies a component and returns the target Entity name according to the mapping strategy."""
    comp_type = str(comp_type or "").strip().lower()
    comp_name = str(comp_name or "").strip()

    # 1. BIOS
    if comp_type == "bios":
        return "BIOS"

    # 2. TPM
    if comp_type == "tpm":
        return "TPM"

    # 3. Operating Systems
    if comp_type == "os":
        if "Windows 11" in comp_name:
            return "Windows 11"
        elif "Windows 10" in comp_name:
            return "Windows 10"
        elif "Windows" in comp_name:
            return "Windows"
        elif "Ubuntu" in comp_name:
            return "Ubuntu"
        elif "RHEL" in comp_name:
            return "RHEL"
        elif "macOS" in comp_name:
            return "macOS"
        elif "Linux" in comp_name:
            return "Linux"
        return None

    # 7. Management Tools
    if comp_type == "management_tool":
        return "Endpoint Manager"

    # 4. Drivers
    is_driver = (comp_type == "driver") or ("driver" in comp_name.lower())
    if is_driver:
        if "Network" in comp_name:
            return "Network Driver"
        elif "Storage" in comp_name:
            return "Storage Driver"
        elif "Graphics" in comp_name:
            return "Graphics Driver"
        elif "Audio" in comp_name:
            return "Audio Driver"
        elif "Chipset" in comp_name:
            return "Chipset Driver"

    # 5. Firmware
    is_firmware = (comp_type == "firmware") or ("firmware" in comp_name.lower())
    if is_firmware:
        if "Network" in comp_name or "NIC" in comp_name:
            return "Network Firmware"
        elif "Storage" in comp_name:
            return "Storage Firmware"
        elif "Embedded Controller" in comp_name:
            return "Embedded Controller Firmware"
        if comp_type == "bios":
            return "BIOS"

    # 6. Agents
    is_agent = (comp_type == "agent") or ("agent" in comp_name.lower())
    if is_agent:
        if any(keyword in comp_name for keyword in ["SentinelOne", "CrowdStrike", "Defender for Endpoint"]):
            return "EDR Agent"
        else:
            return "Endpoint Agent"

    return None

def build_inventory_mappings(conn: Neo4jConnection) -> Tuple[int, int, int, int, int, List[dict], List[str]]:
    """Maps ComponentInstances using exact names before the existing rules."""
    mapped_count = 0
    exact_name_mapped = 0
    rule_mapped = 0
    unmapped_count = 0
    relationships_created = 0
    unmapped_components = []
    errors = []

    logger.info("Fetching existing Domain Entities from Neo4j...")
    try:
        entities_result = conn.execute_query(
            "MATCH (e:Entity) RETURN e.entity_id as entity_id, e.name as name, e.normalized_name as normalized_name"
        )
    except Exception as e:
        err = f"Failed to retrieve Entities from Neo4j: {e}"
        logger.error(err, exc_info=True)
        return 0, 0, 0, 0, 0, [], [err]

    # Both Entity.name and Entity.normalized_name participate in exact matching.
    name_to_id: Dict[str, str] = {}
    for r in entities_result:
        entity_id = r["entity_id"]
        if r.get("name"):
            name_to_id[normalize_lookup_name(r["name"])] = entity_id
        if r.get("normalized_name"):
            name_to_id[normalize_lookup_name(r["normalized_name"])] = entity_id

    logger.info(f"Loaded {len(name_to_id)} normalized entity name keys from database.")

    logger.info("Fetching ComponentInstance nodes from Neo4j...")
    try:
        components_result = conn.execute_query(
            "MATCH (c:ComponentInstance) RETURN c.component_instance_id as comp_id, c.component_type as comp_type, c.component_name as comp_name"
        )
    except Exception as e:
        err = f"Failed to retrieve ComponentInstances from Neo4j: {e}"
        logger.error(err, exc_info=True)
        return 0, 0, 0, 0, 0, [], [err]

    logger.info(f"Retrieved {len(components_result)} ComponentInstance nodes to evaluate.")

    relationship_batch = []

    for comp in components_result:
        comp_id = comp["comp_id"]
        comp_type = comp["comp_type"]
        comp_name = comp["comp_name"]

        # Stage 1: exact normalized component name against Entity.name and
        # Entity.normalized_name. Existing rules run only when this misses.
        target_entity_id = name_to_id.get(normalize_lookup_name(comp_name))
        target_name = None
        resolution_method = None

        if target_entity_id:
            resolution_method = "exact_name"
        else:
            # Stage 2: preserve the pre-Layer-1.1 fallback rules.
            target_name = get_target_entity_name(comp_type, comp_name)
            if target_name:
                target_entity_id = name_to_id.get(normalize_lookup_name(target_name))
            if target_entity_id:
                resolution_method = "rule"

        if target_entity_id:
            relationship_batch.append({
                "component_instance_id": comp_id,
                "entity_id": target_entity_id
            })
            mapped_count += 1
            if resolution_method == "exact_name":
                exact_name_mapped += 1
            else:
                rule_mapped += 1
        else:
            reason = (
                "No exact-name or rule-based mapping matched"
                if not target_name
                else f"Target entity '{target_name}' not found in database"
            )
            unmapped_components.append({
                "component_instance_id": comp_id,
                "component_name": comp_name,
                "component_type": comp_type,
                "reason": reason
            })
            unmapped_count += 1

    # Batch merge relationships
    for i in range(0, len(relationship_batch), BATCH_SIZE):
        chunk = relationship_batch[i:i+BATCH_SIZE]
        try:
            query = """
            UNWIND $batch AS row
            MATCH (c:ComponentInstance {component_instance_id: row.component_instance_id})
            MATCH (e:Entity {entity_id: row.entity_id})
            MERGE (c)-[:INSTANCE_OF]->(e)
            """
            conn.execute_query(query, {"batch": chunk})
            relationships_created += len(chunk)
        except Exception as e:
            err = f"Failed to execute relationship merge batch: {e}"
            logger.error(err, exc_info=True)
            errors.append(err)

    logger.info(
        "Mapping resolution summary: exact_name=%d, rule_based=%d, unmapped=%d",
        exact_name_mapped,
        rule_mapped,
        unmapped_count,
    )

    return (
        mapped_count,
        exact_name_mapped,
        rule_mapped,
        unmapped_count,
        relationships_created,
        unmapped_components,
        errors,
    )

def main():
    project_root = script_dir.parents[1]
    report_path = project_root / "reports" / "inventory_mapping_report.json"
    unmapped_path = project_root / "reports" / "unmapped_components.json"

    logger.info("Starting Inventory-to-Entity Mapper...")
    
    conn = Neo4jConnection()
    mapped = 0
    exact_name_mapped = 0
    rule_mapped = 0
    unmapped = 0
    relationships_created = 0
    unmapped_components = []
    errors = []

    try:
        conn.connect()
        (
            mapped,
            exact_name_mapped,
            rule_mapped,
            unmapped,
            relationships_created,
            unmapped_components,
            run_errors,
        ) = build_inventory_mappings(conn)
        errors.extend(run_errors)
    except Exception as e:
        err_msg = f"Fatal mapper database failure: {e}"
        logger.error(err_msg, exc_info=True)
        errors.append(err_msg)
    finally:
        conn.close()

    # Generate inventory_mapping_report.json
    # Format contains unmapped component IDs
    unmapped_ids = [c["component_instance_id"] for c in unmapped_components]
    report = {
        "mapped": mapped,
        "exact_name_mapped": exact_name_mapped,
        "rule_mapped": rule_mapped,
        "unmapped": unmapped,
        "relationships_created": relationships_created,
        "unmapped_components": unmapped_ids
    }
    
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Inventory mapping report written to: {report_path}")
    except Exception as e:
        logger.error(f"Failed to generate inventory mapping report file: {e}")

    # Generate unmapped_components.json
    try:
        unmapped_path.parent.mkdir(parents=True, exist_ok=True)
        with open(unmapped_path, "w", encoding="utf-8") as f:
            json.dump(unmapped_components, f, indent=2)
        logger.info(f"Unmapped components file written to: {unmapped_path}")
    except Exception as e:
        logger.error(f"Failed to generate unmapped components file: {e}")

    # Output summary stats
    print("=== Inventory-to-Entity Mapping Complete ===")
    print(f"Mapped Components:      {mapped}")
    print(f"Exact Name Mappings:    {exact_name_mapped}")
    print(f"Rule-based Mappings:    {rule_mapped}")
    print(f"Unmapped Components:    {unmapped}")
    print(f"Relationships Created:  {relationships_created}")
    print(f"Errors:                 {len(errors)}")

if __name__ == "__main__":
    main()
