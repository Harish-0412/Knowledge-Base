from pathlib import Path

path = Path("scripts/loaders/inventory_entity_mapper.py")
text = path.read_text(encoding="utf-8")

replacements = {
    "        return 0, 0, 0, [], [err]\n\n    # Map name (lowercase) to entity_id and normalized_name (lowercase) to entity_id for double-safety lookup":
        "        return 0, 0, 0, 0, 0, [], [err]\n\n    # Both Entity.name and Entity.normalized_name participate in exact matching.",
    "            name_to_id[str(r[\"name\"]).lower().strip()] = entity_id":
        "            name_to_id[normalize_lookup_name(r[\"name\"])] = entity_id",
    "            name_to_id[str(r[\"normalized_name\"]).lower().strip()] = entity_id":
        "            name_to_id[normalize_lookup_name(r[\"normalized_name\"])] = entity_id",
    "    logger.info(f\"Loaded {len(name_to_id)} entity mapping keys from database.\")":
        "    logger.info(f\"Loaded {len(name_to_id)} normalized entity name keys from database.\")",
}

for old, new in replacements.items():
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one exact replacement target, found {count}: {old!r}")
    text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8", newline="")
