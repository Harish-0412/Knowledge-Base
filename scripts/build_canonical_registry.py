#!/usr/bin/env python3
import json
import os
import re
import sys
from pathlib import Path

def normalize_for_lookup(value):
    if not isinstance(value, str):
        return ""
    # Unicode-safe case folding
    normalized = value.casefold()
    # Trim whitespace
    normalized = normalized.strip()
    # Replace underscores with spaces
    normalized = normalized.replace("_", " ")
    # Treat hyphens surrounded by words as separators
    normalized = re.sub(r"(\w)-(\w)", r"\1 \2", normalized)
    # Collapse repeated whitespace
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized

def clean_aliases(aliases, canonical_name):
    cleaned = []
    seen_normalized = set()
    if not isinstance(aliases, list):
        return []
    for alias in aliases:
        if not isinstance(alias, str) or not alias.strip():
            continue
        trimmed = alias.strip()
        norm = normalize_for_lookup(trimmed)
        if not norm or norm in seen_normalized or norm == normalize_for_lookup(canonical_name):
            continue
        seen_normalized.add(norm)
        cleaned.append(trimmed)
    # Sort deterministically
    cleaned.sort()
    return cleaned

def main():
    # Define paths
    project_root = Path(__file__).parent.parent
    normalized_dir = project_root / "Domain_layer" / "working" / "v1.1"
    ontology_dir = project_root / "ontology"
    validation_dir = ontology_dir / "validation"
    
    # Create directories if they don't exist
    ontology_dir.mkdir(parents=True, exist_ok=True)
    validation_dir.mkdir(parents=True, exist_ok=True)
    
    # Define the source files
    source_files = [
        "firmware.json",
        "operating_system.json",
        "drivers.json",
        "security.json",
        "management.json"
    ]
    
    # Load and validate source files
    all_entities = []
    source_entity_counts = {}
    errors = []
    warnings = []
    
    for filename in source_files:
        filepath = normalized_dir / filename
        if not filepath.exists():
            errors.append(f"Missing source file: {filename}")
            continue
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON in {filename}: {e}")
            continue
        
        if not isinstance(data, list):
            errors.append(f"{filename} does not contain a JSON array")
            continue
        
        entity_count = 0
        for idx, entity in enumerate(data):
            if not isinstance(entity, dict):
                errors.append(f"Element {idx} in {filename} is not a JSON object")
                continue
            
            # Add source file info for later
            entity["_source_file"] = filename
            all_entities.append(entity)
            entity_count += 1
        
        source_entity_counts[filename] = entity_count
    
    # Build canonical registry
    registry = {
        "registry_version": "1.0.0",
        "schema_version": "1.0.0",
        "status": "draft",
        "source_files": [],
        "entity_count": 0,
        "entities": []
    }
    
    registry_entities = []
    duplicate_entity_ids = []
    duplicate_normalized_names = []
    missing_required_fields = []
    invalid_alias_values = []
    entity_id_map = {}
    canonical_name_map = {}
    alias_map = {}  # normalized alias to list of entity IDs
    
    for entity in all_entities:
        source_file = entity["_source_file"]
        entity_id = entity.get("entity_id", "")
        name = entity.get("name", "")
        entity_type = entity.get("type", "")
        subtype = entity.get("subtype", "")
        layer = entity.get("layer", "")
        knowledge_category = entity.get("knowledge_category", "")
        aliases = entity.get("aliases", [])
        
        # Check required fields
        missing_fields = []
        if not entity_id:
            missing_fields.append("entity_id")
        if not name:
            missing_fields.append("name")
        if not entity_type:
            missing_fields.append("type")
        if not subtype:
            missing_fields.append("subtype")
        if not layer:
            missing_fields.append("layer")
        if not knowledge_category:
            missing_fields.append("knowledge_category")
        
        if missing_fields:
            missing_required_fields.append({
                "entity_id": entity_id,
                "canonical_name": name,
                "source_file": source_file,
                "missing_fields": missing_fields
            })
            errors.append(f"Entity {entity_id} in {source_file} missing required fields: {missing_fields}")
            continue
        
        # Check for duplicate entity IDs
        if entity_id in entity_id_map:
            duplicate_entity_ids.append({
                "entity_id": entity_id,
                "source_files": [entity_id_map[entity_id]["source_file"], source_file]
            })
            errors.append(f"Duplicate entity ID {entity_id} in {source_file} and {entity_id_map[entity_id]['source_file']}")
            continue
        entity_id_map[entity_id] = {"source_file": source_file, "name": name}
        
        # Check normalized canonical name
        normalized_name = normalize_for_lookup(name)
        if normalized_name in canonical_name_map:
            duplicate_normalized_names.append({
                "normalized_name": normalized_name,
                "entities": [
                    {"entity_id": canonical_name_map[normalized_name]["entity_id"], "source_file": canonical_name_map[normalized_name]["source_file"]},
                    {"entity_id": entity_id, "source_file": source_file}
                ]
            })
            errors.append(f"Duplicate normalized canonical name '{normalized_name}' for {entity_id} in {source_file}")
        canonical_name_map[normalized_name] = {"entity_id": entity_id, "source_file": source_file}
        
        # Clean aliases
        cleaned_aliases = clean_aliases(aliases, name)
        # Check for invalid aliases
        if isinstance(aliases, list):
            for alias in aliases:
                if not isinstance(alias, str) or not alias.strip():
                    invalid_alias_values.append({
                        "entity_id": entity_id,
                        "canonical_name": name,
                        "source_file": source_file,
                        "alias": alias
                    })
        
        # Map aliases
        for alias in cleaned_aliases:
            norm_alias = normalize_for_lookup(alias)
            if norm_alias not in alias_map:
                alias_map[norm_alias] = []
            alias_map[norm_alias].append(entity_id)
        
        # Create registry entry
        registry_entry = {
            "entity_id": entity_id,
            "canonical_name": name,
            "normalized_name": normalized_name,
            "type": entity_type,
            "subtype": subtype,
            "layer": layer,
            "knowledge_category": knowledge_category,
            "aliases": cleaned_aliases,
            "source_file": source_file,
            "status": "active"
        }
        registry_entities.append(registry_entry)
    
    # Sort registry entities by entity_id
    registry_entities.sort(key=lambda x: x["entity_id"])
    registry["entities"] = registry_entities
    registry["entity_count"] = len(registry_entities)
    registry["source_files"] = list(source_entity_counts.keys())
    
    # Check alias collisions
    alias_collisions = []
    alias_canonical_name_collisions = []
    for norm_alias, entity_ids in alias_map.items():
        if len(entity_ids) > 1:
            # Alias collision between multiple entities
            colliding_entities = []
            for eid in entity_ids:
                colliding_entities.append({
                    "entity_id": eid,
                    "source_file": entity_id_map[eid]["source_file"],
                    "canonical_name": entity_id_map[eid]["name"]
                })
            alias_collisions.append({
                "normalized_alias": norm_alias,
                "entities": colliding_entities
            })
            warnings.append(f"Alias '{norm_alias}' collides between entities: {entity_ids}")
        
        # Check if alias matches another entity's canonical name
        if norm_alias in canonical_name_map:
            canonical_eid = canonical_name_map[norm_alias]["entity_id"]
            for eid in entity_ids:
                if eid != canonical_eid:
                    alias_canonical_name_collisions.append({
                        "alias_entity_id": eid,
                        "alias_canonical_name": entity_id_map[eid]["name"],
                        "alias_source_file": entity_id_map[eid]["source_file"],
                        "canonical_entity_id": canonical_eid,
                        "canonical_name": entity_id_map[canonical_eid]["name"],
                        "canonical_source_file": entity_id_map[canonical_eid]["source_file"]
                    })
                    warnings.append(f"Entity {eid}'s alias matches canonical name of {canonical_eid}")
    
    # Determine registry status
    total_source_entities = sum(source_entity_counts.values())
    count_mismatch = total_source_entities != len(registry_entities)
    if count_mismatch:
        errors.append(f"Source entity count ({total_source_entities}) does not match registry count ({len(registry_entities)})")
    
    if errors:
        registry["status"] = "invalid"
        validation_status = "FAIL"
    elif warnings:
        registry["status"] = "valid_with_warnings"
        validation_status = "PASS_WITH_WARNINGS"
    else:
        registry["status"] = "valid"
        validation_status = "PASS"
    
    # Write canonical entity registry
    registry_path = ontology_dir / "canonical_entity_registry.json"
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)
    
    # Write validation report
    validation_report = {
        "registry_file": "canonical_entity_registry.json",
        "status": validation_status,
        "source_entity_count": total_source_entities,
        "registry_entity_count": len(registry_entities),
        "source_file_counts": source_entity_counts,
        "errors": errors,
        "warnings": warnings,
        "duplicate_entity_ids": duplicate_entity_ids,
        "duplicate_canonical_names": duplicate_normalized_names,
        "alias_collisions": alias_collisions,
        "alias_canonical_name_collisions": alias_canonical_name_collisions,
        "missing_required_fields": missing_required_fields,
        "invalid_alias_values": invalid_alias_values,
        "count_mismatch": count_mismatch,
        "summary": f"Processed {total_source_entities} entities from {len(source_entity_counts)} files. Validation status: {validation_status}"
    }
    validation_path = validation_dir / "canonical_registry_validation.json"
    with open(validation_path, "w", encoding="utf-8") as f:
        json.dump(validation_report, f, indent=2, ensure_ascii=False)
    
    # Cross-reference resolution
    resolved_references = []
    unresolved_references = []
    ambiguous_references = []
    invalid_references = []
    self_references = []
    total_references = 0
    
    # Build lookup maps for resolution
    exact_canonical_map = {e["canonical_name"]: e for e in registry_entities}
    normalized_canonical_map = {e["normalized_name"]: e for e in registry_entities}
    exact_alias_map = {}  # exact alias to list of entities
    normalized_alias_map = {}  # normalized alias to list of entities
    
    for e in registry_entities:
        for alias in e["aliases"]:
            if alias not in exact_alias_map:
                exact_alias_map[alias] = []
            exact_alias_map[alias].append(e)
        norm_aliases = [normalize_for_lookup(a) for a in e["aliases"]]
        for norm_alias in norm_aliases:
            if norm_alias not in normalized_alias_map:
                normalized_alias_map[norm_alias] = []
            normalized_alias_map[norm_alias].append(e)
    
    # Resolve each reference
    for entity in all_entities:
        source_entity_id = entity.get("entity_id", "")
        source_entity_name = entity.get("name", "")
        source_file = entity.get("_source_file", "")
        related_entities = entity.get("related_entities", [])
        
        if not isinstance(related_entities, list):
            continue
        
        for ref in related_entities:
            total_references += 1
            if not isinstance(ref, str) or not ref.strip():
                invalid_references.append({
                    "source_entity_id": source_entity_id,
                    "source_entity_name": source_entity_name,
                    "source_file": source_file,
                    "reference_value": ref,
                    "reason": "Reference is not a non-empty string"
                })
                continue
            
            # Try to resolve in order
            matched_by = None
            target_entity = None
            
            # 1. Exact case-sensitive canonical-name match
            if ref in exact_canonical_map:
                target_entity = exact_canonical_map[ref]
                matched_by = "exact_canonical_name"
            else:
                # 2. Unique normalized canonical-name match
                norm_ref = normalize_for_lookup(ref)
                if norm_ref in normalized_canonical_map:
                    target_entity = normalized_canonical_map[norm_ref]
                    matched_by = "normalized_canonical_name"
                else:
                    # 3. Exact case-sensitive alias match
                    if ref in exact_alias_map:
                        candidates = exact_alias_map[ref]
                        if len(candidates) == 1:
                            target_entity = candidates[0]
                            matched_by = "exact_alias"
                        else:
                            # Ambiguous
                            ambiguous_references.append({
                                "source_entity_id": source_entity_id,
                                "source_entity_name": source_entity_name,
                                "source_file": source_file,
                                "reference_value": ref,
                                "candidate_entity_ids": [c["entity_id"] for c in candidates],
                                "candidate_canonical_names": [c["canonical_name"] for c in candidates],
                                "reason": "Multiple entities matched exact alias"
                            })
                            continue
                    else:
                        # 4. Unique normalized alias match
                        if norm_ref in normalized_alias_map:
                            candidates = normalized_alias_map[norm_ref]
                            if len(candidates) == 1:
                                target_entity = candidates[0]
                                matched_by = "normalized_alias"
                            else:
                                # Ambiguous
                                ambiguous_references.append({
                                    "source_entity_id": source_entity_id,
                                    "source_entity_name": source_entity_name,
                                    "source_file": source_file,
                                    "reference_value": ref,
                                    "candidate_entity_ids": [c["entity_id"] for c in candidates],
                                    "candidate_canonical_names": [c["canonical_name"] for c in candidates],
                                    "reason": "Multiple entities matched normalized alias"
                                })
                                continue
                        else:
                            # Unresolved
                            unresolved_references.append({
                                "source_entity_id": source_entity_id,
                                "source_entity_name": source_entity_name,
                                "source_file": source_file,
                                "reference_value": ref,
                                "reason": "No canonical name or alias matched"
                            })
                            continue
            
            # Check for self-reference
            if target_entity["entity_id"] == source_entity_id:
                self_references.append({
                    "source_entity_id": source_entity_id,
                    "source_entity_name": source_entity_name,
                    "source_file": source_file,
                    "reference_value": ref,
                    "target_entity_id": target_entity["entity_id"],
                    "target_canonical_name": target_entity["canonical_name"],
                    "target_source_file": target_entity["source_file"]
                })
                warnings.append(f"Self-reference detected for {source_entity_id}")
            
            # Add to resolved
            resolved_references.append({
                "source_entity_id": source_entity_id,
                "source_entity_name": source_entity_name,
                "source_file": source_file,
                "reference_value": ref,
                "target_entity_id": target_entity["entity_id"],
                "target_canonical_name": target_entity["canonical_name"],
                "target_source_file": target_entity["source_file"],
                "matched_by": matched_by
            })
    
    # Calculate resolution rate
    valid_references = total_references - len(invalid_references)
    if valid_references > 0:
        resolution_rate = round((len(resolved_references) / valid_references) * 100, 2)
    else:
        resolution_rate = 0.0
    
    # Determine cross-reference status
    if errors:
        cross_ref_status = "FAIL"
    elif unresolved_references or ambiguous_references or invalid_references or self_references:
        cross_ref_status = "PASS_WITH_WARNINGS"
    else:
        cross_ref_status = "PASS"
    
    # Sort all report collections
    resolved_references.sort(key=lambda x: (x["source_entity_id"], x["reference_value"]))
    unresolved_references.sort(key=lambda x: (x["source_entity_id"], x["reference_value"]))
    ambiguous_references.sort(key=lambda x: (x["source_entity_id"], x["reference_value"]))
    invalid_references.sort(key=lambda x: (x["source_entity_id"], x["reference_value"]))
    self_references.sort(key=lambda x: (x["source_entity_id"], x["reference_value"]))
    
    # Write cross-reference resolution report
    cross_ref_report = {
        "status": cross_ref_status,
        "total_references": total_references,
        "resolved_count": len(resolved_references),
        "unresolved_count": len(unresolved_references),
        "ambiguous_count": len(ambiguous_references),
        "invalid_count": len(invalid_references),
        "self_reference_count": len(self_references),
        "resolution_rate": resolution_rate,
        "resolved_references": resolved_references,
        "unresolved_references": unresolved_references,
        "ambiguous_references": ambiguous_references,
        "invalid_references": invalid_references,
        "self_references": self_references,
        "summary": f"Processed {total_references} references. Resolved: {len(resolved_references)}, Unresolved: {len(unresolved_references)}, Ambiguous: {len(ambiguous_references)}, Invalid: {len(invalid_references)}, Self-references: {len(self_references)}. Resolution rate: {resolution_rate}%"
    }
    cross_ref_path = validation_dir / "cross_reference_resolution.json"
    with open(cross_ref_path, "w", encoding="utf-8") as f:
        json.dump(cross_ref_report, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("="*60)
    print("Canonical Entity Registry Build Summary")
    print("="*60)
    print(f"Source files processed: {len(source_entity_counts)}")
    print(f"Source entity counts per file:")
    for filename, count in source_entity_counts.items():
        print(f"  {filename}: {count}")
    print(f"Total source entities: {total_source_entities}")
    print(f"Total registry entities: {len(registry_entities)}")
    print(f"Registry validation status: {validation_status}")
    print(f"Duplicate entity ID count: {len(duplicate_entity_ids)}")
    print(f"Duplicate canonical name count: {len(duplicate_normalized_names)}")
    print(f"Alias collision count: {len(alias_collisions)}")
    print(f"\nCross-reference resolution:")
    print(f"Total related-entity references: {total_references}")
    print(f"Resolved references: {len(resolved_references)}")
    print(f"Unresolved references: {len(unresolved_references)}")
    print(f"Ambiguous references: {len(ambiguous_references)}")
    print(f"Invalid references: {len(invalid_references)}")
    print(f"Resolution rate: {resolution_rate}%")
    print(f"\nWarnings requiring manual review: {len(warnings)}")
    if warnings:
        for w in warnings[:10]:
            print(f"  - {w}")
        if len(warnings) > 10:
            print(f"  ... and {len(warnings)-10} more")
    print("\nGenerated files:")
    print(f"  - {registry_path}")
    print(f"  - {validation_path}")
    print(f"  - {cross_ref_path}")
    print(f"\nPhase ready to freeze: {'Yes' if validation_status in ('PASS', 'PASS_WITH_WARNINGS') else 'No'}")
    print("="*60)
    
    # Exit with non-zero if fatal errors
    if errors:
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
