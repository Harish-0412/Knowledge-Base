import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


PROJECT_ROOT = Path(__file__).resolve().parent
NEO4J_DIR = PROJECT_ROOT / "InventoryLayer" / "neo4j"
REPORT_PATH = NEO4J_DIR / "graph_verification_report.json"

# When this root-level script is executed from the project root, the local
# neo4j/ import-artifact directory can shadow the installed neo4j Python
# package. Remove the project root entries before importing the shared
# Neo4jConnection helper.
for path_entry in ("", str(PROJECT_ROOT)):
    while path_entry in sys.path:
        sys.path.remove(path_entry)
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "loaders"))
from neo4j_connection import Neo4jConnection  # noqa: E402


NODE_LABELS = [
    "Device",
    "InstalledBIOS",
    "InstalledFirmware",
    "InstalledOS",
    "InstalledDriver",
    "Vendor",
]

RELATIONSHIP_TYPES = [
    "HAS_BIOS",
    "HAS_FIRMWARE",
    "RUNS_OS",
    "HAS_DRIVER",
    "BELONGS_TO_VENDOR",
]


def expected_counts() -> Dict[str, Dict[str, int]]:
    manifest_path = NEO4J_DIR / "import_manifest.json"
    if not manifest_path.exists():
        return {"nodes": {}, "relationships": {}}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "nodes": {entry["label"]: int(entry["records"]) for entry in manifest.get("node_files", [])},
        "relationships": {
            entry["type"]: int(entry["records"]) for entry in manifest.get("relationship_files", [])
        },
    }


def node_counts(conn: Neo4jConnection) -> Dict[str, int]:
    counts = {}
    for label in NODE_LABELS:
        result = conn.execute_query(f"MATCH (n:{label}) RETURN count(n) AS count")
        counts[label] = int(result[0]["count"])
    return counts


def relationship_counts(conn: Neo4jConnection) -> Dict[str, int]:
    counts = {}
    for rel_type in RELATIONSHIP_TYPES:
        result = conn.execute_query(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) AS count")
        counts[rel_type] = int(result[0]["count"])
    return counts


def endpoint_validation(conn: Neo4jConnection) -> Dict[str, Dict[str, Any]]:
    checks = {
        "HAS_BIOS": """
            MATCH ()-[r:HAS_BIOS]->()
            WITH count(r) AS total
            MATCH (:Device)-[valid:HAS_BIOS]->(:InstalledBIOS)
            RETURN total, count(valid) AS valid
        """,
        "HAS_FIRMWARE": """
            MATCH ()-[r:HAS_FIRMWARE]->()
            WITH count(r) AS total
            MATCH (:Device)-[valid:HAS_FIRMWARE]->(:InstalledFirmware)
            RETURN total, count(valid) AS valid
        """,
        "RUNS_OS": """
            MATCH ()-[r:RUNS_OS]->()
            WITH count(r) AS total
            MATCH (:Device)-[valid:RUNS_OS]->(:InstalledOS)
            RETURN total, count(valid) AS valid
        """,
        "HAS_DRIVER": """
            MATCH ()-[r:HAS_DRIVER]->()
            WITH count(r) AS total
            MATCH (:Device)-[valid:HAS_DRIVER]->(:InstalledDriver)
            RETURN total, count(valid) AS valid
        """,
        "BELONGS_TO_VENDOR": """
            MATCH ()-[r:BELONGS_TO_VENDOR]->()
            WITH count(r) AS total
            MATCH (:Device)-[valid:BELONGS_TO_VENDOR]->(:Vendor)
            RETURN total, count(valid) AS valid
        """,
    }
    results = {}
    for rel_type, query in checks.items():
        row = conn.execute_query(query)[0]
        total = int(row["total"])
        valid = int(row["valid"])
        results[rel_type] = {
            "total_relationships": total,
            "valid_endpoint_relationships": valid,
            "invalid_endpoint_relationships": total - valid,
            "status": "PASS" if total == valid else "FAIL",
        }
    return results


def duplicate_device_ids(conn: Neo4jConnection) -> List[Dict[str, Any]]:
    return conn.execute_query(
        """
        MATCH (d:Device)
        WITH d.device_id AS device_id, count(d) AS count
        WHERE device_id IS NULL OR count > 1
        RETURN device_id, count
        ORDER BY count DESC, device_id
        """
    )


def count_comparison(expected: Dict[str, Dict[str, int]], actual_nodes: Dict[str, int], actual_rels: Dict[str, int]) -> Dict[str, Any]:
    node_results = {}
    for label, expected_count in expected["nodes"].items():
        actual_count = actual_nodes.get(label, 0)
        node_results[label] = {
            "expected": expected_count,
            "actual": actual_count,
            "status": "PASS" if expected_count == actual_count else "FAIL",
        }

    relationship_results = {}
    for rel_type, expected_count in expected["relationships"].items():
        actual_count = actual_rels.get(rel_type, 0)
        relationship_results[rel_type] = {
            "expected": expected_count,
            "actual": actual_count,
            "status": "PASS" if expected_count == actual_count else "FAIL",
        }

    return {"nodes": node_results, "relationships": relationship_results}


def overall_status(report: Dict[str, Any]) -> str:
    if report["errors"]:
        return "FAIL"
    if report["duplicate_device_ids"]:
        return "FAIL"
    for group in ("nodes", "relationships"):
        if any(item["status"] != "PASS" for item in report["count_comparison"][group].values()):
            return "FAIL"
    if any(item["status"] != "PASS" for item in report["relationship_endpoint_validation"].values()):
        return "FAIL"
    return "PASS"


def main() -> None:
    report: Dict[str, Any] = {
        "report_id": "GRAPH-VERIFY-INVENTORY-001",
        "report_type": "inventory_graph_verification",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "import_directory": str(NEO4J_DIR),
        "expected_counts": expected_counts(),
        "actual_node_counts": {},
        "actual_relationship_counts": {},
        "count_comparison": {"nodes": {}, "relationships": {}},
        "relationship_endpoint_validation": {},
        "missing_references": "Neo4j does not permit physically dangling relationships; endpoint validation checks relationship types and endpoint labels.",
        "duplicate_device_ids": [],
        "errors": [],
        "overall_status": "FAIL",
    }

    conn = Neo4jConnection()
    try:
        conn.connect()
        report["actual_node_counts"] = node_counts(conn)
        report["actual_relationship_counts"] = relationship_counts(conn)
        report["count_comparison"] = count_comparison(
            report["expected_counts"],
            report["actual_node_counts"],
            report["actual_relationship_counts"],
        )
        report["relationship_endpoint_validation"] = endpoint_validation(conn)
        report["duplicate_device_ids"] = duplicate_device_ids(conn)
    except Exception as exc:
        logger.error("Inventory graph verification failed: %s", exc, exc_info=True)
        report["errors"].append(str(exc))
    finally:
        conn.close()

    report["overall_status"] = overall_status(report)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info("Inventory graph verification report written to: %s", REPORT_PATH)

    print("=== Inventory Graph Verification Complete ===")
    print(f"Status: {report['overall_status']}")
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
