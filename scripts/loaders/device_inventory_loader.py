import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple

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

def flatten_props(obj: dict, exclude_keys: list = None) -> dict:
    """Flattens top-level JSON fields into Neo4j compatible properties.
    
    Nested dicts are stored as JSON strings. Arrays are preserved as lists.
    """
    exclude = set(exclude_keys or [])
    props = {}
    for k, v in obj.items():
        if k in exclude:
            continue
        if isinstance(v, dict):
            props[k] = json.dumps(v) if v else None
        elif isinstance(v, list):
            str_items = []
            for item in v:
                if isinstance(item, dict):
                    str_items.append(json.dumps(item))
                else:
                    str_items.append(str(item) if item is not None else "")
            props[k] = str_items
        else:
            props[k] = v
    return props

def load_inventory(json_path: Path, conn: Neo4jConnection) -> Tuple[int, int, int, List[str]]:
    """Loads devices, components, and HAS_COMPONENT relationships in batches into Neo4j."""
    devices_loaded = 0
    components_loaded = 0
    relationships_created = 0
    errors = []

    if not json_path.exists():
        err = f"Inventory file not found at: {json_path}"
        logger.error(err)
        errors.append(err)
        return 0, 0, 0, errors

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        err = f"Failed to parse JSON file {json_path.name}: {e}"
        logger.error(err)
        errors.append(err)
        return 0, 0, 0, errors

    devices = [data] if isinstance(data, dict) else (data if isinstance(data, list) else [])
    current_timestamp = datetime.now(timezone.utc).isoformat() + "Z"

    device_batch = []
    component_batch = []
    relationship_batch = []

    for dev_idx, dev in enumerate(devices):
        dev_id = dev.get("device_id")
        if not dev_id:
            errors.append(f"Device at index {dev_idx} missing 'device_id'. Skipping.")
            continue
        
        dev_id_str = str(dev_id).strip()
        
        # Flatten device properties, excluding components, metadata, and readiness blocks
        dev_props = flatten_props(dev, exclude_keys=["components", "metadata", "readiness", "created_at", "updated_at", "graph_layer"])
        
        # Explicitly preserve metadata and readiness as serialized JSON string properties
        if "metadata" in dev:
            dev_props["metadata"] = json.dumps(dev["metadata"]) if dev["metadata"] else None
        if "readiness" in dev:
            dev_props["readiness"] = json.dumps(dev["readiness"]) if dev["readiness"] else None
            
        device_batch.append({
            "device_id": dev_id_str,
            "properties": dev_props,
            "timestamp": current_timestamp
        })

        components = dev.get("components", [])
        if not isinstance(components, list):
            continue

        for comp_idx, comp in enumerate(components):
            comp_inst_id = comp.get("component_instance_id")
            if not comp_inst_id:
                errors.append(f"Component at index {comp_idx} in device '{dev_id_str}' missing 'component_instance_id'. Skipping.")
                continue

            comp_inst_id_str = str(comp_inst_id).strip()
            
            # Flatten component properties, excluding reserved schema columns
            comp_props = flatten_props(comp, exclude_keys=["created_at", "updated_at", "graph_layer"])
            
            component_batch.append({
                "component_instance_id": comp_inst_id_str,
                "properties": comp_props,
                "timestamp": current_timestamp
            })

            relationship_batch.append({
                "device_id": dev_id_str,
                "component_instance_id": comp_inst_id_str,
                "timestamp": current_timestamp
            })

    # Load Devices in batches
    for i in range(0, len(device_batch), BATCH_SIZE):
        chunk = device_batch[i:i+BATCH_SIZE]
        try:
            query = """
            UNWIND $batch AS row
            MERGE (d:Device {device_id: row.device_id})
            ON CREATE SET d.created_at = row.timestamp
            SET d.updated_at = row.timestamp
            SET d.graph_layer = "inventory"
            SET d += row.properties
            """
            conn.execute_query(query, {"batch": chunk})
            devices_loaded += len(chunk)
        except Exception as e:
            err = f"Failed to load device batch: {e}"
            logger.error(err, exc_info=True)
            errors.append(err)

    # Load ComponentInstances in batches
    for i in range(0, len(component_batch), BATCH_SIZE):
        chunk = component_batch[i:i+BATCH_SIZE]
        try:
            query = """
            UNWIND $batch AS row
            MERGE (c:ComponentInstance {component_instance_id: row.component_instance_id})
            ON CREATE SET c.created_at = row.timestamp
            SET c.updated_at = row.timestamp
            SET c.graph_layer = "inventory"
            SET c += row.properties
            """
            conn.execute_query(query, {"batch": chunk})
            components_loaded += len(chunk)
        except Exception as e:
            err = f"Failed to load component batch: {e}"
            logger.error(err, exc_info=True)
            errors.append(err)

    # Create HAS_COMPONENT relationships in batches
    for i in range(0, len(relationship_batch), BATCH_SIZE):
        chunk = relationship_batch[i:i+BATCH_SIZE]
        try:
            query = """
            UNWIND $batch AS row
            MATCH (d:Device {device_id: row.device_id})
            MATCH (c:ComponentInstance {component_instance_id: row.component_instance_id})
            MERGE (d)-[r:HAS_COMPONENT]->(c)
            ON CREATE SET r.created_at = row.timestamp
            SET r.updated_at = row.timestamp
            """
            conn.execute_query(query, {"batch": chunk})
            relationships_created += len(chunk)
        except Exception as e:
            err = f"Failed to create HAS_COMPONENT relationships batch: {e}"
            logger.error(err, exc_info=True)
            errors.append(err)

    return devices_loaded, components_loaded, relationships_created, errors

def main():
    if len(sys.argv) > 1:
        json_path = Path(sys.argv[1])
    else:
        json_path = script_dir.parents[1] / "mock_inventory(2).json"
        
    report_path = script_dir.parents[1] / "reports" / "device_inventory_load_report.json"

    logger.info(f"Starting Device Inventory Loader. Input: {json_path}")
    
    conn = Neo4jConnection()
    devices_loaded = 0
    components_loaded = 0
    relationships_created = 0
    errors = []

    try:
        conn.connect()
        devices_loaded, components_loaded, relationships_created, load_errors = load_inventory(json_path, conn)
        errors.extend(load_errors)
    except Exception as e:
        err_msg = f"Fatal loader database failure: {e}"
        logger.error(err_msg, exc_info=True)
        errors.append(err_msg)
    finally:
        conn.close()

    # Generate load report
    report = {
        "devices_loaded": devices_loaded,
        "components_loaded": components_loaded,
        "relationships_created": relationships_created,
        "errors": errors
    }
    
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Inventory load report written to: {report_path}")
    except Exception as e:
        logger.error(f"Failed to generate load report file: {e}")

    # Output summary
    print("=== Device Inventory Load Complete ===")
    print(f"Devices Loaded: {devices_loaded}")
    print(f"Components Loaded: {components_loaded}")
    print(f"Relationships Created: {relationships_created}")
    print(f"Errors: {len(errors)}")

if __name__ == "__main__":
    main()
