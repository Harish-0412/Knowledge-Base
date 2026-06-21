import csv
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


PROJECT_ROOT = Path(__file__).resolve().parent
NEO4J_DIR = PROJECT_ROOT / "InventoryLayer" / "neo4j"
REPORT_PATH = NEO4J_DIR / "neo4j_load_report.json"
BATCH_SIZE = 500

# When this root-level script is executed from the project root, the local
# neo4j/ import-artifact directory can shadow the installed neo4j Python
# package. Remove the project root entries before importing the shared
# Neo4jConnection helper.
for path_entry in ("", str(PROJECT_ROOT)):
    while path_entry in sys.path:
        sys.path.remove(path_entry)
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "loaders"))
from neo4j_connection import Neo4jConnection  # noqa: E402


NODE_FILES = {
    "Device": "device_nodes.csv",
    "InstalledBIOS": "bios_nodes.csv",
    "InstalledFirmware": "firmware_nodes.csv",
    "InstalledOS": "os_nodes.csv",
    "InstalledDriver": "driver_nodes.csv",
    "Vendor": "vendor_nodes.csv",
}

RELATIONSHIP_FILES = {
    "HAS_BIOS": "has_bios_relationships.csv",
    "HAS_FIRMWARE": "has_firmware_relationships.csv",
    "RUNS_OS": "runs_os_relationships.csv",
    "HAS_DRIVER": "has_driver_relationships.csv",
    "BELONGS_TO_VENDOR": "belongs_to_vendor_relationships.csv",
}


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Required import file not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def chunks(rows: List[Dict[str, str]], size: int = BATCH_SIZE) -> Iterable[List[Dict[str, str]]]:
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def run_batched(conn: Neo4jConnection, query: str, rows: List[Dict[str, str]]) -> int:
    processed = 0
    for batch in chunks(rows):
        result = conn.execute_query(query, {"rows": batch})
        if result:
            processed += int(result[0].get("processed", 0))
    return processed


def load_constraints(conn: Neo4jConnection) -> None:
    """Creates non-destructive uniqueness constraints used by the inventory graph."""
    constraints = [
        """
        CREATE CONSTRAINT device_id_unique IF NOT EXISTS
        FOR (n:Device) REQUIRE n.device_id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT installed_bios_import_id_unique IF NOT EXISTS
        FOR (n:InstalledBIOS) REQUIRE n.import_id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT installed_firmware_import_id_unique IF NOT EXISTS
        FOR (n:InstalledFirmware) REQUIRE n.import_id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT installed_os_import_id_unique IF NOT EXISTS
        FOR (n:InstalledOS) REQUIRE n.import_id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT installed_driver_import_id_unique IF NOT EXISTS
        FOR (n:InstalledDriver) REQUIRE n.import_id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT vendor_name_unique IF NOT EXISTS
        FOR (n:Vendor) REQUIRE n.vendor_name IS UNIQUE
        """,
    ]
    for query in constraints:
        conn.execute_query(query)


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


def validate_csv_references() -> Dict[str, Any]:
    """Checks that every relationship endpoint exists in the generated CSV node files."""
    node_ids = {
        "Device": {row[":ID(Device)"] for row in read_csv_rows(NEO4J_DIR / "device_nodes.csv")},
        "BIOS": {row[":ID(BIOS)"] for row in read_csv_rows(NEO4J_DIR / "bios_nodes.csv")},
        "Firmware": {row[":ID(Firmware)"] for row in read_csv_rows(NEO4J_DIR / "firmware_nodes.csv")},
        "OS": {row[":ID(OS)"] for row in read_csv_rows(NEO4J_DIR / "os_nodes.csv")},
        "Driver": {row[":ID(Driver)"] for row in read_csv_rows(NEO4J_DIR / "driver_nodes.csv")},
        "Vendor": {row[":ID(Vendor)"] for row in read_csv_rows(NEO4J_DIR / "vendor_nodes.csv")},
    }
    specs = {
        "HAS_BIOS": ("has_bios_relationships.csv", ":START_ID(Device)", "Device", ":END_ID(BIOS)", "BIOS"),
        "HAS_FIRMWARE": (
            "has_firmware_relationships.csv",
            ":START_ID(Device)",
            "Device",
            ":END_ID(Firmware)",
            "Firmware",
        ),
        "RUNS_OS": ("runs_os_relationships.csv", ":START_ID(Device)", "Device", ":END_ID(OS)", "OS"),
        "HAS_DRIVER": (
            "has_driver_relationships.csv",
            ":START_ID(Device)",
            "Device",
            ":END_ID(Driver)",
            "Driver",
        ),
        "BELONGS_TO_VENDOR": (
            "belongs_to_vendor_relationships.csv",
            ":START_ID(Device)",
            "Device",
            ":END_ID(Vendor)",
            "Vendor",
        ),
    }
    checks = {}
    for rel_type, (file_name, start_col, start_group, end_col, end_group) in specs.items():
        rows = read_csv_rows(NEO4J_DIR / file_name)
        missing_start = sorted({row[start_col] for row in rows if row[start_col] not in node_ids[start_group]})
        missing_end = sorted({row[end_col] for row in rows if row[end_col] not in node_ids[end_group]})
        checks[rel_type] = {
            "rows_checked": len(rows),
            "missing_start_references": missing_start,
            "missing_end_references": missing_end,
            "status": "PASS" if not missing_start and not missing_end else "FAIL",
        }
    return checks


def load_nodes(conn: Neo4jConnection) -> Dict[str, int]:
    queries = {
        "Device": """
        UNWIND $rows AS row
        MERGE (n:Device {device_id: row[":ID(Device)"]})
        SET n.device_name = row.device_name,
            n.vendor = row.vendor,
            n.device_model = row.device_model,
            n.inventory_timestamp = datetime(row["inventory_timestamp:datetime"]),
            n.graph_layer = "inventory",
            n.updated_at = datetime()
        RETURN count(row) AS processed
        """,
        "InstalledBIOS": """
        UNWIND $rows AS row
        MERGE (n:InstalledBIOS {import_id: row[":ID(BIOS)"]})
        SET n.name = row.name,
            n.vendor = row.vendor,
            n.bios_version = row.bios_version,
            n.graph_layer = "inventory",
            n.updated_at = datetime()
        RETURN count(row) AS processed
        """,
        "InstalledFirmware": """
        UNWIND $rows AS row
        MERGE (n:InstalledFirmware {import_id: row[":ID(Firmware)"]})
        SET n.name = row.name,
            n.vendor = row.vendor,
            n.firmware_version = row.firmware_version,
            n.graph_layer = "inventory",
            n.updated_at = datetime()
        RETURN count(row) AS processed
        """,
        "InstalledOS": """
        UNWIND $rows AS row
        MERGE (n:InstalledOS {import_id: row[":ID(OS)"]})
        SET n.name = row.name,
            n.family = row.family,
            n.version = row.version,
            n.edition = row.edition,
            n.architecture = row.architecture,
            n.graph_layer = "inventory",
            n.updated_at = datetime()
        RETURN count(row) AS processed
        """,
        "InstalledDriver": """
        UNWIND $rows AS row
        MERGE (n:InstalledDriver {import_id: row[":ID(Driver)"]})
        SET n.name = row.name,
            n.version = row.version,
            n.vendor = row.vendor,
            n.component_type = row.component_type,
            n.graph_layer = "inventory",
            n.updated_at = datetime()
        RETURN count(row) AS processed
        """,
        "Vendor": """
        UNWIND $rows AS row
        MERGE (n:Vendor {vendor_name: row.vendor_name})
        SET n.import_id = row[":ID(Vendor)"],
            n.normalized_vendor_name = row.normalized_vendor_name,
            n.graph_layer = "inventory",
            n.updated_at = datetime()
        RETURN count(row) AS processed
        """,
    }
    processed = {}
    for label, file_name in NODE_FILES.items():
        rows = read_csv_rows(NEO4J_DIR / file_name)
        logger.info("Loading %s nodes from %s (%s rows)", label, file_name, len(rows))
        processed[label] = run_batched(conn, queries[label], rows)
    return processed


def load_relationships(conn: Neo4jConnection) -> Dict[str, int]:
    queries = {
        "HAS_BIOS": """
        UNWIND $rows AS row
        MATCH (start:Device {device_id: row[":START_ID(Device)"]})
        MATCH (end:InstalledBIOS {import_id: row[":END_ID(BIOS)"]})
        MERGE (start)-[r:HAS_BIOS]->(end)
        SET r.graph_layer = "inventory", r.updated_at = datetime()
        RETURN count(row) AS processed
        """,
        "HAS_FIRMWARE": """
        UNWIND $rows AS row
        MATCH (start:Device {device_id: row[":START_ID(Device)"]})
        MATCH (end:InstalledFirmware {import_id: row[":END_ID(Firmware)"]})
        MERGE (start)-[r:HAS_FIRMWARE]->(end)
        SET r.graph_layer = "inventory", r.updated_at = datetime()
        RETURN count(row) AS processed
        """,
        "RUNS_OS": """
        UNWIND $rows AS row
        MATCH (start:Device {device_id: row[":START_ID(Device)"]})
        MATCH (end:InstalledOS {import_id: row[":END_ID(OS)"]})
        MERGE (start)-[r:RUNS_OS]->(end)
        SET r.graph_layer = "inventory", r.updated_at = datetime()
        RETURN count(row) AS processed
        """,
        "HAS_DRIVER": """
        UNWIND $rows AS row
        MATCH (start:Device {device_id: row[":START_ID(Device)"]})
        MATCH (end:InstalledDriver {import_id: row[":END_ID(Driver)"]})
        MERGE (start)-[r:HAS_DRIVER]->(end)
        SET r.graph_layer = "inventory", r.updated_at = datetime()
        RETURN count(row) AS processed
        """,
        "BELONGS_TO_VENDOR": """
        UNWIND $rows AS row
        MATCH (start:Device {device_id: row[":START_ID(Device)"]})
        MATCH (end:Vendor {import_id: row[":END_ID(Vendor)"]})
        MERGE (start)-[r:BELONGS_TO_VENDOR]->(end)
        SET r.graph_layer = "inventory", r.updated_at = datetime()
        RETURN count(row) AS processed
        """,
    }
    processed = {}
    for rel_type, file_name in RELATIONSHIP_FILES.items():
        rows = read_csv_rows(NEO4J_DIR / file_name)
        logger.info("Loading %s relationships from %s (%s rows)", rel_type, file_name, len(rows))
        processed[rel_type] = run_batched(conn, queries[rel_type], rows)
    return processed


def graph_counts(conn: Neo4jConnection) -> Dict[str, Dict[str, int]]:
    node_counts = {}
    for label in NODE_FILES:
        result = conn.execute_query(f"MATCH (n:{label}) RETURN count(n) AS count")
        node_counts[label] = int(result[0]["count"])

    relationship_counts = {}
    for rel_type in RELATIONSHIP_FILES:
        result = conn.execute_query(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) AS count")
        relationship_counts[rel_type] = int(result[0]["count"])

    return {"nodes": node_counts, "relationships": relationship_counts}


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


def status_from_report(report: Dict[str, Any]) -> str:
    if report["errors"]:
        return "FAIL"
    if any(check["status"] != "PASS" for check in report["csv_reference_checks"].values()):
        return "FAIL"
    expected = report["expected_counts"]
    graph = report["graph_counts_after_load"]
    for label, expected_count in expected["nodes"].items():
        if graph["nodes"].get(label) != expected_count:
            return "FAIL"
    for rel_type, expected_count in expected["relationships"].items():
        if graph["relationships"].get(rel_type) != expected_count:
            return "FAIL"
    if report["duplicate_device_ids"]:
        return "FAIL"
    return "PASS"


def main() -> None:
    report: Dict[str, Any] = {
        "report_id": "NEO4J-LOAD-INVENTORY-001",
        "report_type": "inventory_neo4j_load",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "import_directory": str(NEO4J_DIR),
        "expected_counts": expected_counts(),
        "csv_reference_checks": {},
        "nodes_processed": {},
        "relationships_processed": {},
        "graph_counts_after_load": {"nodes": {}, "relationships": {}},
        "duplicate_device_ids": [],
        "errors": [],
        "overall_status": "FAIL",
    }

    conn = Neo4jConnection()
    try:
        report["csv_reference_checks"] = validate_csv_references()
        conn.connect()
        logger.info("Creating inventory constraints.")
        load_constraints(conn)
        report["nodes_processed"] = load_nodes(conn)
        report["relationships_processed"] = load_relationships(conn)
        report["graph_counts_after_load"] = graph_counts(conn)
        report["duplicate_device_ids"] = duplicate_device_ids(conn)
    except Exception as exc:
        logger.error("Inventory load failed: %s", exc, exc_info=True)
        report["errors"].append(str(exc))
    finally:
        conn.close()

    report["overall_status"] = status_from_report(report)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info("Neo4j inventory load report written to: %s", REPORT_PATH)

    print("=== Inventory Neo4j Load Complete ===")
    print(f"Status: {report['overall_status']}")
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
