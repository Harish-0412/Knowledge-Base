import csv
import json
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone
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

def sanitize_label(label: str) -> str:
    """Sanitizes labels to prevent Cypher injection."""
    return "".join(c for c in label if c.isalnum() or c == "_")

def load_layer1_entities(csv_path: Path, conn: Neo4jConnection) -> Tuple[int, int, List[str]]:
    """Loads entities from data/layer1/entities.csv into Neo4j using dynamic multi-label batching."""
    loaded_count = 0
    updated_count = 0
    errors = []

    if not csv_path.exists():
        err = f"Entities CSV file not found at: {csv_path}"
        logger.error(err)
        errors.append(err)
        return 0, 0, errors

    rows = []
    try:
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                err = "CSV file has no header row."
                logger.error(err)
                errors.append(err)
                return 0, 0, errors
            
            for line_num, row in enumerate(reader, start=2):
                # Detect and skip completely empty rows
                all_values = [str(v).strip() for v in row.values() if v is not None]
                if not any(all_values):
                    continue
                rows.append(row)
    except Exception as e:
        err = f"Failed to parse CSV file: {e}"
        logger.error(err, exc_info=True)
        errors.append(err)
        return 0, 0, errors

    # Group entities by sanitized dynamic label combinations to support batching
    grouped_payloads: Dict[Tuple[str, ...], List[dict]] = {}
    current_timestamp = datetime.now(timezone.utc).isoformat() + "Z"

    for idx, row in enumerate(rows):
        entity_id_raw = row.get("entity_id:ID(Entity)") or ""
        entity_id = entity_id_raw.strip()
        if not entity_id:
            errors.append(f"Row {idx+2}: Missing entity_id")
            continue

        label_raw = row.get(":LABEL") or ""
        labels_list = [sanitize_label(l.strip()) for l in label_raw.split(";") if l.strip()]
        if not labels_list:
            labels_list = ["Entity"]
        elif "Entity" not in labels_list:
            labels_list.append("Entity")

        labels_tuple = tuple(sorted(labels_list))

        # Dynamically build property payload
        properties = {}
        for col_name, val in row.items():
            if col_name == ":LABEL":
                continue
            
            # Map entity_id column header
            prop_key = "entity_id" if col_name == "entity_id:ID(Entity)" else col_name
            
            # Exclude timestamp and graph layer keys if they are present in CSV
            if prop_key in ("created_at", "updated_at", "graph_layer"):
                continue

            cleaned_val = (val or "").strip()
            if prop_key == "aliases":
                if cleaned_val:
                    properties[prop_key] = [a.strip() for a in cleaned_val.split("|") if a.strip()]
                else:
                    properties[prop_key] = []
            else:
                properties[prop_key] = cleaned_val

        payload = {
            "entity_id": entity_id,
            "properties": properties,
            "timestamp": current_timestamp
        }
        grouped_payloads.setdefault(labels_tuple, []).append(payload)

    batch_size = 50
    for labels_tuple, payloads in grouped_payloads.items():
        labels_str = ":".join(labels_tuple)
        
        # Batch merge query using ON CREATE and ON MATCH to track true stats
        query = f"""
        UNWIND $batch AS row
        MERGE (e:Entity {{entity_id: row.entity_id}})
        ON CREATE SET e.created_at = row.timestamp, e._is_new = true
        ON MATCH SET e._is_new = false
        SET e.updated_at = row.timestamp
        SET e.graph_layer = "domain"
        SET e:{labels_str}
        SET e += row.properties
        WITH e, e._is_new AS is_new
        REMOVE e._is_new
        RETURN is_new
        """

        for i in range(0, len(payloads), batch_size):
            chunk = payloads[i:i+batch_size]
            try:
                results = conn.execute_query(query, {"batch": chunk})
                for record in results:
                    is_new = record.get("is_new")
                    if is_new:
                        loaded_count += 1
                    else:
                        updated_count += 1
            except Exception as e:
                err = f"Failed to execute load for label combination {labels_str}: {e}"
                logger.error(err, exc_info=True)
                errors.append(err)

    return loaded_count, updated_count, errors

def main() -> None:
    # Resolve project root and input/output paths
    project_root = script_dir.parents[1]
    csv_path = project_root / "data" / "layer1" / "entities_v1_1.csv"
    report_path = project_root / "reports" / "layer1_load_report.json"

    logger.info("Starting Layer 1 Entity Loader.")
    logger.info(f"Loading ontology file: {csv_path}")
    
    conn = Neo4jConnection()
    loaded_count = 0
    updated_count = 0
    errors = []

    try:
        conn.connect()
        loaded_count, updated_count, load_errors = load_layer1_entities(csv_path, conn)
        errors.extend(load_errors)
    except Exception as e:
        err_msg = f"Fatal loader database failure: {e}"
        logger.error(err_msg, exc_info=True)
        errors.append(err_msg)
    finally:
        conn.close()

    # Generate load report
    report = {
        "loaded": loaded_count,
        "updated": updated_count,
        "errors": errors
    }
    
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Layer 1 load report written to: {report_path}")
    except Exception as e:
        logger.error(f"Failed to generate load report file: {e}")

    # Output stats summary
    print("=== Layer 1 Entity Load Complete ===")
    print(f"Loaded (New): {loaded_count}")
    print(f"Updated (Existing): {updated_count}")
    print(f"Errors: {len(errors)}")

if __name__ == "__main__":
    main()
