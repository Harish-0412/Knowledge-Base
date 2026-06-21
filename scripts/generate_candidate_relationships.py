#!/usr/bin/env python3
"""
Candidate Relationship Generation Engine.

Generates deterministic, evidence-traceable candidate relationship instances
from approved RC2 entities using resolved cross-references and explicit declarations.
"""

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

RELATIONSHIP_ID_PREFIX = "REL-CAND-"
EVIDENCE_ID_PREFIX = "EVID-CAND-"

DOMAIN_CATEGORIES = {
    "Driver": "driver_relationships.json",
    "Firmware": "firmware_relationships.json",
    "Management": "management_relationships.json",
    "Operating System": "operating_system_relationships.json",
    "Security": "security_relationships.json",
}

RISK_LEVELS = {
    "IS_A": "low",
    "PART_OF": "low",
    "IMPLEMENTS": "medium",
    "USES": "medium",
    "INITIALIZES": "medium",
    "ENABLES": "medium",
    "MANAGES": "medium",
    "MONITORS": "medium",
    "PROTECTS": "medium",
    "CONFIGURES": "medium",
    "UPDATES": "medium",
    "RUNS_ON": "medium",
    "INSTALLED_ON": "medium",
    "REQUIRES": "high",
    "DEPENDS_ON": "high",
    "REPLACES": "high",
    "DEPRECATED_BY": "high",
    "SUPPORTS": "high",
    "COMPATIBLE_WITH": "high",
    "CONFLICTS_WITH": "high",
}


def sha256_hash(data: str, length: int = 12) -> str:
    """Generate deterministic SHA256-based hash."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:length].upper()


def canonical_json(obj: Any) -> str:
    """Generate canonical JSON string for hashing."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def load_json_file(path: Path) -> Any:
    """Load JSON file with error handling."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"ERROR: Failed to load {path}: {e}", file=sys.stderr)
        raise


def save_json_file(path: Path, data: Any, pretty: bool = True) -> None:
    """Save JSON file with optional pretty-printing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        if pretty:
            json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            json.dump(data, f, ensure_ascii=False)
        f.write("\n")


class CandidateGenerator:
    """Generates candidate relationships from RC2 entities."""

    def __init__(
        self,
        domain_dir: Path,
        registry_path: Path,
        cross_refs_path: Path,
        relationship_ontology_dir: Path,
        output_dir: Path,
        dry_run: bool = False,
    ):
        self.domain_dir = Path(domain_dir)
        self.registry_path = Path(registry_path)
        self.cross_refs_path = Path(cross_refs_path)
        self.relationship_ontology_dir = Path(relationship_ontology_dir)
        self.output_dir = Path(output_dir)
        self.dry_run = dry_run

        self.entities: Dict[str, Dict] = {}
        self.registry: Dict = {}
        self.cross_refs: Dict = {}
        self.relationship_types: Dict = {}

        self.candidates: Dict[str, List[Dict]] = defaultdict(list)
        self.review_queue: List[Dict] = []
        self.traces: List[Dict] = []
        self.evidence_gaps: List[Dict] = []
        self.relationship_ids_seen: Set[str] = set()
        self.evidence_ids_seen: Set[str] = set()

    def load_inputs(self) -> None:
        """Load all input files."""
        print("Loading entity data...")
        self._load_entity_files()

        print("Loading registry...")
        self.registry = load_json_file(self.registry_path)

        print("Loading cross-references...")
        self.cross_refs = load_json_file(self.cross_refs_path)

        print("Loading relationship ontology...")
        types_path = self.relationship_ontology_dir / "relationship_types.json"
        self.relationship_types = load_json_file(types_path)

    def _load_entity_files(self) -> None:
        """Load all domain entity files."""
        entity_files = [
            "firmware.json",
            "operating_system.json",
            "drivers.json",
            "security.json",
            "management.json",
        ]

        for filename in entity_files:
            filepath = self.domain_dir / filename
            data = load_json_file(filepath)
            for entity in data:
                entity_id = entity.get("entity_id")
                if entity_id:
                    self.entities[entity_id] = entity

    def generate(self) -> bool:
        """Generate all candidate relationships."""
        print("Generating candidate relationships...")

        self._generate_from_resolved_references()

        print(
            f"Generated {sum(len(v) for v in self.candidates.values())} candidates"
        )
        print(f"Review queue: {len(self.review_queue)} proposals")
        print(f"Evidence gaps: {len(self.evidence_gaps)}")

        return True

    def _generate_from_resolved_references(self) -> None:
        """Generate USES relationships from resolved cross-references."""
        references = self.cross_refs.get("references", [])
        resolved_refs = [r for r in references if r.get("status") == "resolved"]

        # Deduplicate by source+target pair
        seen_pairs: Set[tuple] = set()
        deduplicated_refs = []
        for ref in resolved_refs:
            pair = (ref.get("source_entity_id"), ref.get("target_entity_id"))
            if pair not in seen_pairs:
                deduplicated_refs.append(ref)
                seen_pairs.add(pair)

        print(f"Processing {len(deduplicated_refs)} resolved references (deduplicated from {len(resolved_refs)})")

        for ref in deduplicated_refs:
            source_id = ref.get("source_entity_id")
            target_id = ref.get("target_entity_id")
            reference_value = ref.get("reference_value", "")

            if not source_id or not target_id:
                continue

            if source_id not in self.entities or target_id not in self.entities:
                continue

            source_entity = self.entities[source_id]
            target_entity = self.entities[target_id]

            source_cat = source_entity.get("knowledge_category")
            target_cat = target_entity.get("knowledge_category")

            # Generate USES relationship
            rel_id = self._generate_relationship_id(
                source_id, "USES", target_id, []
            )

            source_name = source_entity.get("name", source_id)
            target_name = target_entity.get("name", target_id)

            candidate = {
                "relationship_id": rel_id,
                "source_id": source_id,
                "relationship_type": "USES",
                "target_id": target_id,
                "statement": f"{source_name} uses {target_name}.",
                "assertion_scope": "universal",
                "condition_logic": "ALL",
                "conditions": [],
                "evidence": [
                    self._create_evidence(
                        "knowledge_base_source",
                        source_id,
                        f"RC2 Cross-Reference: {reference_value}",
                        "ontology/releases/v1.1-rc2/cross_references_v1.1.json",
                        f"source_entity_id={source_id}; target_entity_id={target_id}; reference={reference_value}",
                        "Candidate relationship from approved cross-reference resolution",
                    )
                ],
                "confidence": 0.70,
                "verification_status": "review_required",
                "approval_status": "candidate",
                "approved_by": None,
                "approved_at": None,
                "source_release": "1.1.0-rc2",
                "relationship_ontology_version": "1.0.0",
                "metadata": {
                    "extraction_method": "approved_cross_reference",
                    "source_field": "cross_references",
                    "cross_reference_status": "resolved",
                    "reference_resolution_method": ref.get("resolution_method", "unknown"),
                    "routing_domain": self._get_domain_for_routing(
                        source_id, target_id
                    ),
                },
            }

            self._add_candidate(candidate, source_id, target_id, source_cat, target_cat)
            self._add_trace(
                rel_id,
                source_id,
                target_id,
                "USES",
                source_entity.get("source_file", ""),
                "cross_references",
                reference_value,
                "resolved",
                "approved_cross_reference",
                "Extracted from approved cross-reference with resolution",
                DOMAIN_CATEGORIES.get(source_cat, "cross_domain_relationships.json"),
            )

    def _generate_relationship_id(
        self, source_id: str, rel_type: str, target_id: str, conditions: List[Dict]
    ) -> str:
        """Generate stable, deterministic relationship ID."""
        canonical = {
            "source_id": source_id,
            "relationship_type": rel_type,
            "target_id": target_id,
            "conditions": sorted(
                [json.loads(canonical_json(c)) for c in conditions],
                key=lambda x: canonical_json(x),
            ),
        }
        hash_input = canonical_json(canonical)
        hash_value = sha256_hash(hash_input, 12)

        rel_id = f"{RELATIONSHIP_ID_PREFIX}{hash_value}"

        if rel_id in self.relationship_ids_seen:
            hash_value = sha256_hash(hash_input, 16)
            rel_id = f"{RELATIONSHIP_ID_PREFIX}{hash_value}"

        self.relationship_ids_seen.add(rel_id)
        return rel_id

    def _generate_evidence_id(self, source_type: str, source_id: str) -> str:
        """Generate stable evidence ID."""
        hash_input = f"{source_type}:{source_id}:{len(self.evidence_ids_seen)}"
        hash_value = sha256_hash(hash_input, 12)
        self.evidence_ids_seen.add(hash_value)
        return f"{EVIDENCE_ID_PREFIX}{hash_value}"

    def _create_evidence(
        self,
        source_type: str,
        source_id: str,
        title: str,
        uri: str,
        locator: str,
        notes: str,
    ) -> Dict:
        """Create evidence record."""
        evidence_id = self._generate_evidence_id(source_type, source_id)
        return {
            "evidence_id": evidence_id,
            "source_type": source_type,
            "source_id": source_id,
            "title": title,
            "uri": uri,
            "locator": locator,
            "notes": notes,
        }

    def _get_domain_for_routing(self, source_id: str, target_id: str) -> str:
        """Determine routing domain."""
        source_cat = self.entities.get(source_id, {}).get("knowledge_category")
        target_cat = self.entities.get(target_id, {}).get("knowledge_category")

        if source_cat == target_cat:
            return source_cat or "unknown"
        return "cross_domain"

    def _add_candidate(
        self,
        candidate: Dict,
        source_id: str,
        target_id: str,
        source_cat: str,
        target_cat: str,
    ) -> None:
        """Add candidate to appropriate domain file."""
        if source_cat == target_cat:
            domain_file = DOMAIN_CATEGORIES.get(source_cat, "cross_domain_relationships.json")
        else:
            domain_file = "cross_domain_relationships.json"

        self.candidates[domain_file].append(candidate)

    def _add_trace(
        self,
        rel_id: str,
        source_id: str,
        target_id: str,
        rel_type: str,
        source_file: str,
        source_field: str,
        source_text: str,
        cross_ref_status: str,
        extraction_method: str,
        confidence_reason: str,
        routing_file: str,
    ) -> None:
        """Add trace record."""
        self.traces.append(
            {
                "relationship_id": rel_id,
                "source_entity_id": source_id,
                "target_entity_id": target_id,
                "relationship_type": rel_type,
                "source_file": source_file,
                "source_field": source_field,
                "source_text": source_text[:100] if source_text else "",
                "cross_reference_status": cross_ref_status,
                "extraction_method": extraction_method,
                "confidence_reason": confidence_reason,
                "routing_file": routing_file,
            }
        )

    def write_outputs(self) -> None:
        """Write all output files."""
        if self.dry_run:
            print("DRY RUN: Not writing outputs")
            return

        print(f"Writing outputs to {self.output_dir}...")

        validation_dir = self.output_dir / "validation"
        validation_dir.mkdir(parents=True, exist_ok=True)

        # Write domain files
        for domain_file, candidates in self.candidates.items():
            filepath = self.output_dir / domain_file
            self._write_domain_file(filepath, candidates)

        # Write trace
        self._write_trace()

        # Write review queue
        self._write_review_queue()

        # Write evidence gaps
        self._write_evidence_gaps()

        # Write manifest
        self._write_manifest()

        print("Outputs written successfully")

    def _write_domain_file(self, filepath: Path, candidates: List[Dict]) -> None:
        """Write domain relationship file."""
        data = {
            "relationship_ontology_version": "1.0.0",
            "entity_registry_version": self.registry.get("registry_version", "1.1.0-rc2"),
            "status": "candidate",
            "domain": self._get_domain_from_filename(filepath.name),
            "relationship_count": len(candidates),
            "relationships": candidates,
        }
        save_json_file(filepath, data)
        print(f"  {filepath.name}: {len(candidates)} candidates")

    def _get_domain_from_filename(self, filename: str) -> str:
        """Extract domain name from filename."""
        return filename.replace("_relationships.json", "").replace("_", " ").title()

    def _write_trace(self) -> None:
        """Write generation trace."""
        data = {
            "relationship_ontology_version": "1.0.0",
            "entity_registry_version": self.registry.get("registry_version", "1.1.0-rc2"),
            "trace_count": len(self.traces),
            "traces": sorted(self.traces, key=lambda x: x["relationship_id"]),
        }
        save_json_file(self.output_dir / "candidate_generation_trace.json", data)

    def _write_review_queue(self) -> None:
        """Write review queue."""
        data = {
            "status": "requires_review",
            "proposal_count": len(self.review_queue),
            "proposals": sorted(
                self.review_queue, key=lambda x: x.get("proposal_id", "")
            ),
        }
        save_json_file(self.output_dir / "candidate_review_queue.json", data)

    def _write_evidence_gaps(self) -> None:
        """Write evidence gap report."""
        gaps_by_predicate = defaultdict(int)
        gaps_by_reason = defaultdict(int)

        for gap in self.evidence_gaps:
            gaps_by_predicate[gap.get("predicate", "unknown")] += 1
            gaps_by_reason[gap.get("reason", "unknown")] += 1

        data = {
            "gap_count": len(self.evidence_gaps),
            "gaps_by_predicate": dict(sorted(gaps_by_predicate.items())),
            "gaps_by_reason": dict(sorted(gaps_by_reason.items())),
            "high_risk_gaps": [
                g for g in self.evidence_gaps if g.get("risk_level") == "high"
            ],
            "recommended_research_priorities": [
                "REQUIRES relationships require strong authoritative evidence",
                "SUPPORTS relationships require explicit conditional support",
                "COMPATIBLE_WITH relationships require tested compatibility evidence",
                "CONFLICTS_WITH relationships require explicit conflict evidence",
                "REPLACES relationships require formal replacement evidence",
            ],
            "summary": f"{len(self.evidence_gaps)} gaps identified; prioritize high-risk predicates",
        }
        save_json_file(self.output_dir / "evidence_gap_report.json", data)

    def _write_manifest(self) -> None:
        """Write candidate release manifest."""
        total_candidates = sum(len(v) for v in self.candidates.values())
        counts_by_predicate = defaultdict(int)
        counts_by_risk = defaultdict(int)
        counts_by_status = defaultdict(int)

        for domain_candidates in self.candidates.values():
            for rel in domain_candidates:
                counts_by_predicate[rel["relationship_type"]] += 1
                counts_by_risk[RISK_LEVELS.get(rel["relationship_type"], "unknown")] += 1
                counts_by_status[rel["verification_status"]] += 1

        domain_counts = {
            self._get_domain_from_filename(domain_file): len(candidates)
            for domain_file, candidates in self.candidates.items()
        }

        data = {
            "candidate_release": "1.0.0-candidate",
            "relationship_ontology_version": "1.0.0",
            "entity_registry_version": self.registry.get("registry_version", "1.1.0-rc2"),
            "status": "CANDIDATE",
            "production_import_allowed": False,
            "relationship_counts": {
                "total": total_candidates,
                **domain_counts,
            },
            "counts_by_predicate": dict(sorted(counts_by_predicate.items())),
            "counts_by_risk": dict(sorted(counts_by_risk.items())),
            "counts_by_verification_status": dict(sorted(counts_by_status.items())),
            "review_queue_count": len(self.review_queue),
            "evidence_gap_count": len(self.evidence_gaps),
            "validation_status": "pending",
            "artifacts": sorted([
                "firmware_relationships.json",
                "operating_system_relationships.json",
                "driver_relationships.json",
                "security_relationships.json",
                "management_relationships.json",
                "cross_domain_relationships.json",
                "candidate_generation_trace.json",
                "candidate_review_queue.json",
                "evidence_gap_report.json",
            ]),
            "known_limitations": [
                "High-risk predicates withheld pending authoritative evidence",
                "RELATED_TO relationships not generated",
                "Inverse relationships not generated",
                "Transitive closure not computed",
            ],
            "safety_notice": "Candidate relationships only. Production Neo4j import forbidden until human approval and production validation PASS.",
        }
        save_json_file(self.output_dir / "relationship_candidate_manifest.json", data)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate candidate relationships from RC2 entities"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    gen_parser = subparsers.add_parser("generate", help="Generate candidates")
    gen_parser.add_argument("--domain-dir", required=True, help="Path to domain layer directory")
    gen_parser.add_argument("--registry", required=True, help="Path to canonical registry JSON")
    gen_parser.add_argument("--cross-references", required=True, help="Path to cross-references JSON")
    gen_parser.add_argument("--relationship-ontology", required=True, help="Path to relationship ontology directory")
    gen_parser.add_argument("--output-dir", required=True, help="Path to output directory")
    gen_parser.add_argument("--dry-run", action="store_true", help="Do not write outputs")

    args = parser.parse_args()

    if args.command == "generate":
        generator = CandidateGenerator(
            domain_dir=args.domain_dir,
            registry_path=args.registry,
            cross_refs_path=args.cross_references,
            relationship_ontology_dir=args.relationship_ontology,
            output_dir=args.output_dir,
            dry_run=args.dry_run,
        )

        try:
            generator.load_inputs()
            generator.generate()
            generator.write_outputs()
            print("SUCCESS: Candidate generation complete")
            return 0
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
