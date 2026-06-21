"""Merge the additive Layer 1.1 expansion into a Neo4j-ready entity CSV."""

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "layer1" / "entities.csv"
EXPANSION = ROOT / "data" / "layer1" / "entity_expansion.csv"
OUTPUT = ROOT / "data" / "layer1" / "entities_v1_1.csv"

ID_HEADER = "entity_id:ID(Entity)"
LABEL_HEADER = ":LABEL"


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no header")
        return reader.fieldnames, list(reader)


def main() -> None:
    base_headers, base_rows = read_rows(BASE)
    expansion_headers, expansion_rows = read_rows(EXPANSION)

    expected_expansion_headers = [
        "entity_id", "name", "normalized_name", "type", "subtype", "layer",
        "aliases", "knowledge_category", "concept_scope", "vendor",
        "verification_status", "source_file", "status",
    ]
    if expansion_headers != expected_expansion_headers:
        raise ValueError("entity_expansion.csv does not match the required Layer 1.1 schema")

    seen_ids = {row[ID_HEADER].strip() for row in base_rows}
    seen_names = {row["name"].strip().casefold() for row in base_rows}
    seen_normalized = {row["normalized_name"].strip().casefold() for row in base_rows}

    converted_rows: list[dict[str, str]] = []
    for row in expansion_rows:
        entity_id = row["entity_id"].strip()
        name = row["name"].strip()
        normalized = row["normalized_name"].strip().casefold()
        if not entity_id or not name or not normalized:
            raise ValueError("Expansion rows require entity_id, name, and normalized_name")
        if entity_id in seen_ids or name.casefold() in seen_names or normalized in seen_normalized:
            raise ValueError(f"Duplicate expansion entity: {entity_id} / {name}")

        converted = {header: "" for header in base_headers}
        for header in base_headers:
            if header not in (ID_HEADER, LABEL_HEADER):
                converted[header] = row.get(header, "")
        converted[ID_HEADER] = entity_id
        converted[LABEL_HEADER] = f"Entity;{row['type'].strip()}"
        converted_rows.append(converted)

        seen_ids.add(entity_id)
        seen_names.add(name.casefold())
        seen_normalized.add(normalized)

    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=base_headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(base_rows)
        writer.writerows(converted_rows)

    print(f"Wrote {len(base_rows)} base + {len(converted_rows)} new = "
          f"{len(base_rows) + len(converted_rows)} entities to {OUTPUT}")


if __name__ == "__main__":
    main()
