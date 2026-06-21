import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOADERS = ROOT / "scripts" / "loaders"
sys.path.insert(0, str(LOADERS))

from inventory_entity_mapper import build_inventory_mappings, normalize_lookup_name


class FakeConnection:
    def __init__(self, entities, components):
        self.entities = entities
        self.components = components
        self.relationship_rows = []

    def execute_query(self, query, parameters=None):
        if "MATCH (e:Entity) RETURN" in query:
            return self.entities
        if "MATCH (c:ComponentInstance) RETURN" in query:
            return self.components
        if "UNWIND $batch" in query:
            self.relationship_rows.extend(parameters["batch"])
            return []
        raise AssertionError(f"Unexpected query: {query}")


def test_exact_name_precedes_existing_fallback_rules():
    entities = [
        {"entity_id": "OS-013", "name": "VMware ESXi", "normalized_name": "vmware esxi"},
        {"entity_id": "OS-003", "name": "Windows 11", "normalized_name": "windows 11"},
    ]
    components = [
        {"comp_id": "C-1", "comp_type": "os", "comp_name": "  VMWARE   esxi "},
        {"comp_id": "C-2", "comp_type": "os", "comp_name": "Windows 11 Enterprise"},
        {"comp_id": "C-3", "comp_type": "model", "comp_name": "Device Model"},
    ]
    conn = FakeConnection(entities, components)

    result = build_inventory_mappings(conn)

    mapped, exact, rule, unmapped, relationships, details, errors = result
    assert (mapped, exact, rule, unmapped, relationships) == (2, 1, 1, 1, 2)
    assert not errors
    assert details[0]["component_instance_id"] == "C-3"
    assert conn.relationship_rows == [
        {"component_instance_id": "C-1", "entity_id": "OS-013"},
        {"component_instance_id": "C-2", "entity_id": "OS-003"},
    ]


def test_layer1_1_inventory_projection():
    with (ROOT / "data" / "layer1" / "entities_v1_1.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        entity_rows = list(csv.DictReader(handle))

    entities = [
        {
            "entity_id": row["entity_id:ID(Entity)"],
            "name": row["name"],
            "normalized_name": row["normalized_name"],
        }
        for row in entity_rows
    ]

    inventory = json.loads((ROOT / "mock_inventory(2).json").read_text(encoding="utf-8"))
    components = [
        {
            "comp_id": component["component_instance_id"],
            "comp_type": component.get("component_type"),
            "comp_name": component.get("component_name"),
        }
        for device in inventory
        for component in device.get("components", [])
    ]

    conn = FakeConnection(entities, components)
    mapped, exact, rule, unmapped, relationships, details, errors = build_inventory_mappings(conn)

    assert len(components) == 262
    assert mapped == 222
    assert exact + rule == mapped
    assert unmapped == 40
    assert relationships == mapped
    assert {item["component_type"] for item in details} == {"model", "device_type"}
    assert not errors
    assert normalize_lookup_name(" VMware   ESXi ") == "vmware esxi"
