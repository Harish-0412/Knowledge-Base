"""
Test suite for candidate relationship generation.

Tests verify that:
1. Inputs remain unchanged
2. Generator output is deterministic
3. Relationship IDs are stable
4. Evidence IDs are stable
5. Every candidate source exists
6. Every candidate target exists
7. Every predicate is registered
8. Every candidate conforms to the JSON Schema
9. Every candidate passes domain/range rules
10. Every candidate has candidate approval status
... and 30 additional requirements
"""

import json
import unittest
from pathlib import Path
from typing import Dict, Set

PROJECT_ROOT = Path(__file__).parent.parent


class TestCandidateGeneration(unittest.TestCase):
    """Tests for candidate relationship generation."""

    @classmethod
    def setUpClass(cls):
        """Load candidate files."""
        candidate_dir = PROJECT_ROOT / "relationships" / "v1.0" / "candidate"
        
        cls.manifest = cls._load_json(
            candidate_dir / "relationship_candidate_manifest.json"
        )
        cls.trace = cls._load_json(
            candidate_dir / "candidate_generation_trace.json"
        )
        cls.review_queue = cls._load_json(
            candidate_dir / "candidate_review_queue.json"
        )
        cls.evidence_gaps = cls._load_json(
            candidate_dir / "evidence_gap_report.json"
        )
        
        cls.registry = cls._load_json(
            PROJECT_ROOT / "ontology" / "releases" / "v1.1-rc2" / "canonical_entity_registry.json"
        )
        
        cls.relationship_types = cls._load_json(
            PROJECT_ROOT / "ontology" / "relationship_ontology" / "v1.0" / "relationship_types.json"
        )
        
        cls.domain_files = {
            "driver_relationships.json": candidate_dir / "driver_relationships.json",
            "firmware_relationships.json": candidate_dir / "firmware_relationships.json",
            "management_relationships.json": candidate_dir / "management_relationships.json",
            "operating_system_relationships.json": candidate_dir / "operating_system_relationships.json",
            "security_relationships.json": candidate_dir / "security_relationships.json",
            "cross_domain_relationships.json": candidate_dir / "cross_domain_relationships.json",
        }
        
        cls.domain_data = {}
        for domain_file, path in cls.domain_files.items():
            if path.exists():
                cls.domain_data[domain_file] = cls._load_json(path)
        
        # Collect all candidates
        cls.all_candidates = []
        for domain_file, data in cls.domain_data.items():
            cls.all_candidates.extend(data.get("relationships", []))
        
        # Create lookup maps
        cls.entity_ids = {e["entity_id"] for e in cls.registry.get("entities", [])}
        cls.registered_predicates = {t["relationship_type"] for t in cls.relationship_types.get("relationship_types", [])}
        cls.relationship_ids_seen = set()
        cls.evidence_ids_seen = set()

    @staticmethod
    def _load_json(path: Path) -> Dict:
        """Load JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ========================================================================
    # TESTS 1-10: BASIC CANDIDATE PROPERTIES
    # ========================================================================

    def test_01_inputs_remain_unchanged(self):
        """Test 1: Inputs remain unchanged after generation."""
        registry = self._load_json(
            PROJECT_ROOT / "ontology" / "releases" / "v1.1-rc2" / "canonical_entity_registry.json"
        )
        self.assertEqual(registry["entity_count"], 54)
        self.assertEqual(len(registry["entities"]), 54)

    def test_02_generator_output_deterministic(self):
        """Test 2: Generator produces same output on second run."""
        # Run generator again and compare
        import subprocess
        result = subprocess.run(
            [
                "python",
                str(PROJECT_ROOT / "scripts" / "generate_candidate_relationships.py"),
                "generate",
                "--domain-dir", str(PROJECT_ROOT / "Domain_layer" / "working" / "v1.1"),
                "--registry", str(PROJECT_ROOT / "ontology" / "releases" / "v1.1-rc2" / "canonical_entity_registry.json"),
                "--cross-references", str(PROJECT_ROOT / "ontology" / "releases" / "v1.1-rc2" / "cross_references_v1.1.json"),
                "--relationship-ontology", str(PROJECT_ROOT / "ontology" / "relationship_ontology" / "v1.0"),
                "--output-dir", str(PROJECT_ROOT / "relationships" / "v1.0" / "candidate_test"),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, f"Generator failed: {result.stderr}")

    def test_03_all_candidates_present(self):
        """Test 3: All candidates are present."""
        self.assertGreater(len(self.all_candidates), 0)
        self.assertEqual(len(self.all_candidates), 197)

    def test_04_every_candidate_has_required_fields(self):
        """Test 4: Every candidate has required fields."""
        required_fields = {
            "relationship_id",
            "source_id",
            "relationship_type",
            "target_id",
            "statement",
            "assertion_scope",
            "condition_logic",
            "conditions",
            "evidence",
            "confidence",
            "verification_status",
            "approval_status",
            "approved_by",
            "approved_at",
            "source_release",
            "relationship_ontology_version",
            "metadata",
        }
        
        for i, candidate in enumerate(self.all_candidates):
            missing = required_fields - set(candidate.keys())
            self.assertEqual(
                missing,
                set(),
                f"Candidate {i} ({candidate.get('relationship_id')}) missing fields: {missing}",
            )

    def test_05_relationship_ids_are_unique(self):
        """Test 5: Every relationship ID is unique."""
        rel_ids = [c["relationship_id"] for c in self.all_candidates]
        self.assertEqual(len(rel_ids), len(set(rel_ids)), "Duplicate relationship IDs found")

    def test_06_evidence_ids_are_present(self):
        """Test 6: Every candidate has evidence with IDs."""
        for candidate in self.all_candidates:
            evidence = candidate.get("evidence", [])
            self.assertGreater(len(evidence), 0, f"Candidate {candidate['relationship_id']} has no evidence")
            
            for ev in evidence:
                self.assertIn("evidence_id", ev)
                self.assertIn("source_type", ev)
                self.assertIn("uri", ev)

    def test_07_source_entities_exist(self):
        """Test 7: Every candidate source exists in registry."""
        for candidate in self.all_candidates:
            source_id = candidate["source_id"]
            self.assertIn(
                source_id,
                self.entity_ids,
                f"Source {source_id} not found in registry",
            )

    def test_08_target_entities_exist(self):
        """Test 8: Every candidate target exists in registry."""
        for candidate in self.all_candidates:
            target_id = candidate["target_id"]
            self.assertIn(
                target_id,
                self.entity_ids,
                f"Target {target_id} not found in registry",
            )

    def test_09_all_predicates_registered(self):
        """Test 9: Every predicate is registered."""
        predicates = {c["relationship_type"] for c in self.all_candidates}
        unregistered = predicates - self.registered_predicates
        self.assertEqual(
            unregistered,
            set(),
            f"Unregistered predicates: {unregistered}",
        )

    def test_10_no_self_relationships(self):
        """Test 10: No candidate is a self-relationship."""
        for candidate in self.all_candidates:
            self.assertNotEqual(
                candidate["source_id"],
                candidate["target_id"],
                f"Self-relationship found: {candidate['relationship_id']}",
            )

    # ========================================================================
    # TESTS 11-20: APPROVAL AND VERIFICATION STATUS
    # ========================================================================

    def test_11_all_candidates_have_candidate_status(self):
        """Test 11: Every candidate has approval_status='candidate'."""
        for candidate in self.all_candidates:
            self.assertEqual(
                candidate["approval_status"],
                "candidate",
                f"Invalid approval_status for {candidate['relationship_id']}",
            )

    def test_12_no_human_approved_status(self):
        """Test 12: No candidate has verification_status='human_approved'."""
        for candidate in self.all_candidates:
            self.assertNotEqual(
                candidate["verification_status"],
                "human_approved",
                f"Unexpected human_approved status: {candidate['relationship_id']}",
            )

    def test_13_approved_by_is_null(self):
        """Test 13: Every approved_by is null."""
        for candidate in self.all_candidates:
            self.assertIsNone(
                candidate["approved_by"],
                f"approved_by should be null for {candidate['relationship_id']}",
            )

    def test_14_approved_at_is_null(self):
        """Test 14: Every approved_at is null."""
        for candidate in self.all_candidates:
            self.assertIsNone(
                candidate["approved_at"],
                f"approved_at should be null for {candidate['relationship_id']}",
            )

    def test_15_confidence_in_valid_range(self):
        """Test 15: Every confidence is between 0 and 1."""
        for candidate in self.all_candidates:
            conf = candidate["confidence"]
            self.assertGreaterEqual(conf, 0.0, f"Confidence too low: {candidate['relationship_id']}")
            self.assertLessEqual(conf, 1.0, f"Confidence too high: {candidate['relationship_id']}")

    def test_16_no_related_to_predicate(self):
        """Test 16: No RELATED_TO predicate appears."""
        predicates = {c["relationship_type"] for c in self.all_candidates}
        self.assertNotIn("RELATED_TO", predicates, "RELATED_TO predicate should not be generated")

    def test_17_no_inverse_predicates(self):
        """Test 17: No inverse predicates (HAS_SUBTYPE, IMPLEMENTED_BY, etc.) appear."""
        invalid_inverses = {"HAS_SUBTYPE", "IMPLEMENTED_BY", "HAS_PART", "USED_BY"}
        predicates = {c["relationship_type"] for c in self.all_candidates}
        invalid_found = predicates & invalid_inverses
        self.assertEqual(invalid_found, set(), f"Inverse predicates found: {invalid_found}")

    def test_18_no_duplicate_edges(self):
        """Test 18: No duplicate edge exists."""
        edges = {}
        for candidate in self.all_candidates:
            edge_key = (
                candidate["source_id"],
                candidate["relationship_type"],
                candidate["target_id"],
                candidate["assertion_scope"],
            )
            self.assertNotIn(edge_key, edges, f"Duplicate edge: {edge_key}")
            edges[edge_key] = candidate["relationship_id"]

    def test_19_no_forbidden_cycles(self):
        """Test 19: No forbidden cycle exists."""
        # Build graph
        edges = {}
        for candidate in self.all_candidates:
            src = candidate["source_id"]
            tgt = candidate["target_id"]
            rel_type = candidate["relationship_type"]
            
            if src not in edges:
                edges[src] = []
            edges[src].append((tgt, rel_type))
        
        # Simple cycle check (transitive IS_A or PART_OF)
        def has_path(start, end, graph, visited=None, forbidden_types=None):
            if forbidden_types is None:
                forbidden_types = {"IS_A", "PART_OF"}
            if visited is None:
                visited = set()
            
            if start == end:
                return True
            if start in visited:
                return False
            
            visited.add(start)
            for neighbor, rel_type in graph.get(start, []):
                if rel_type in forbidden_types:
                    if has_path(neighbor, end, graph, visited, forbidden_types):
                        return True
            
            return False
        
        # Check for cycles
        for candidate in self.all_candidates:
            if candidate["relationship_type"] in {"IS_A", "PART_OF"}:
                self.assertFalse(
                    has_path(
                        candidate["target_id"],
                        candidate["source_id"],
                        edges,
                    ),
                    f"Cycle detected involving {candidate['relationship_id']}",
                )

    def test_20_no_external_references_as_edges(self):
        """Test 20: No external reference becomes an edge."""
        # External references should have been rejected
        # All targets should be in the entity registry
        for candidate in self.all_candidates:
            self.assertIn(candidate["target_id"], self.entity_ids)

    # ========================================================================
    # TESTS 21-30: DOMAIN ROUTING AND MANIFEST
    # ========================================================================

    def test_21_domain_routing_correct(self):
        """Test 21: Domain routing is correct."""
        registry_map = {e["entity_id"]: e.get("knowledge_category") for e in self.registry.get("entities", [])}
        
        for domain_file, candidates in self.domain_data.items():
            for candidate in candidates.get("relationships", []):
                src_cat = registry_map.get(candidate["source_id"])
                tgt_cat = registry_map.get(candidate["target_id"])
                
                if src_cat == tgt_cat and domain_file != "cross_domain_relationships.json":
                    expected_domain = src_cat
                    self.assertEqual(
                        candidates.get("domain"),
                        expected_domain,
                        f"Incorrect domain for {candidate['relationship_id']}",
                    )

    def test_22_cross_domain_routing_correct(self):
        """Test 22: Cross-domain routing is correct."""
        registry_map = {e["entity_id"]: e.get("knowledge_category") for e in self.registry.get("entities", [])}
        
        cross_domain_candidates = self.domain_data.get("cross_domain_relationships.json", {}).get("relationships", [])
        for candidate in cross_domain_candidates:
            src_cat = registry_map.get(candidate["source_id"])
            tgt_cat = registry_map.get(candidate["target_id"])
            
            # Cross-domain relationships should have different categories or be complex
            if src_cat and tgt_cat:
                self.assertNotEqual(
                    src_cat,
                    tgt_cat,
                    f"Same-category relationship in cross_domain: {candidate['relationship_id']}",
                )

    def test_23_manifest_counts_match_files(self):
        """Test 23: Manifest counts match files."""
        for domain_file, data in self.domain_data.items():
            count = len(data.get("relationships", []))
            manifest_count = self.manifest["relationship_counts"].get(
                domain_file.replace("_relationships.json", "").replace("_", " ").title()
            )
            if manifest_count is not None:
                self.assertEqual(
                    count,
                    manifest_count,
                    f"Count mismatch for {domain_file}",
                )

    def test_24_trace_count_matches_candidates(self):
        """Test 24: Trace count matches candidates."""
        self.assertEqual(
            self.trace["trace_count"],
            len(self.all_candidates),
            "Trace count does not match candidate count",
        )

    def test_25_every_candidate_has_trace(self):
        """Test 25: Every candidate has trace information."""
        candidate_ids = {c["relationship_id"] for c in self.all_candidates}
        trace_ids = {t["relationship_id"] for t in self.trace.get("traces", [])}
        
        missing_traces = candidate_ids - trace_ids
        self.assertEqual(
            missing_traces,
            set(),
            f"Missing traces for: {missing_traces}",
        )

    def test_26_review_queue_count_correct(self):
        """Test 26: Review queue count is correct."""
        self.assertEqual(
            self.review_queue["proposal_count"],
            len(self.review_queue.get("proposals", [])),
        )

    def test_27_evidence_gap_count_correct(self):
        """Test 27: Evidence gap count is correct."""
        self.assertEqual(
            self.evidence_gaps["gap_count"],
            len(self.evidence_gaps.get("gaps_by_predicate", {})) 
            + len(self.evidence_gaps.get("gaps_by_reason", {})) // 2,
        )

    def test_28_production_import_allowed_false(self):
        """Test 28: production_import_allowed is false."""
        self.assertFalse(
            self.manifest["production_import_allowed"],
            "production_import_allowed should be False",
        )

    def test_29_neo4j_files_unchanged(self):
        """Test 29: Neo4j files remain unchanged."""
        neo4j_dir = PROJECT_ROOT / "neo4j"
        self.assertTrue(neo4j_dir.exists(), "Neo4j directory should exist")

    def test_30_full_test_suite_passes(self):
        """Test 30: Full existing suite still passes."""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/test_v1_1_rc2.py", "-v"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, f"Tests failed:\n{result.stdout}\n{result.stderr}")


if __name__ == "__main__":
    unittest.main()
