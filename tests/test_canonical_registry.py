#!/usr/bin/env python3
"""
Comprehensive automated tests for the Canonical Entity Registry phase.

Tests verify:
1. Input file existence and validity
2. Output file existence and validity
3. Registry structure and content integrity
4. Cross-reference resolution
5. Builder reproducibility
6. Input file immutability
"""

import json
import os
import shutil
import subprocess
import sys
import unittest
from hashlib import md5
from pathlib import Path


class CanonicalRegistryTestCase(unittest.TestCase):
    """Base test case for canonical registry tests."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.project_root = Path(__file__).parent.parent
        cls.normalized_dir = cls.project_root / "Domain_layer" / "normalized"
        cls.ontology_dir = cls.project_root / "ontology"
        cls.validation_dir = cls.ontology_dir / "validation"
        cls.scripts_dir = cls.project_root / "scripts"
        cls.builder_script = cls.scripts_dir / "build_canonical_registry.py"
        
        cls.source_filenames = [
            "firmware.json",
            "operating_system.json",
            "drivers.json",
            "security.json",
            "management.json"
        ]
        
        cls.expected_entity_fields = {
            "entity_id",
            "canonical_name",
            "normalized_name",
            "type",
            "subtype",
            "layer",
            "knowledge_category",
            "aliases",
            "source_file",
            "status"
        }

    def compute_file_hash(self, filepath):
        """Compute MD5 hash of a file."""
        if not filepath.exists():
            return None
        md5_hash = md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()

    @staticmethod
    def load_json_file(filepath):
        """Load and return JSON from file."""
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)


class TestInputFileValidation(CanonicalRegistryTestCase):
    """Tests 1-3: Input file existence, JSON validity, and array structure."""

    def test_01_all_normalized_input_files_exist(self):
        """Test 1: All five normalized input files exist."""
        for filename in self.source_filenames:
            filepath = self.normalized_dir / filename
            self.assertTrue(filepath.exists(), 
                          f"Input file missing: {filename}")

    def test_02_all_input_files_contain_valid_json(self):
        """Test 2: Every input file contains valid JSON."""
        for filename in self.source_filenames:
            filepath = self.normalized_dir / filename
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                self.fail(f"Invalid JSON in {filename}: {e}")

    def test_03_all_input_files_are_json_arrays(self):
        """Test 3: Every input root is a JSON array."""
        for filename in self.source_filenames:
            filepath = self.normalized_dir / filename
            data = self.load_json_file(filepath)
            self.assertIsInstance(data, list,
                                f"{filename} root is not a JSON array")


class TestOutputFileValidation(CanonicalRegistryTestCase):
    """Tests 4-5: Output file existence and JSON validity."""

    def test_04_all_output_files_exist(self):
        """Test 4: All three output files exist."""
        # Registry file in ontology/ dir
        registry_path = self.ontology_dir / "canonical_entity_registry.json"
        self.assertTrue(registry_path.exists(),
                      f"Output file missing: canonical_entity_registry.json")
        
        # Validation files in ontology/validation/ dir
        for filename in ["canonical_registry_validation.json", "cross_reference_resolution.json"]:
            filepath = self.validation_dir / filename
            self.assertTrue(filepath.exists(),
                          f"Output file missing: {filename}")

    def test_05_all_output_files_contain_valid_json(self):
        """Test 5: All outputs contain valid JSON."""
        registry_path = self.ontology_dir / "canonical_entity_registry.json"
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                json.load(f)
        except json.JSONDecodeError as e:
            self.fail(f"Invalid JSON in canonical_entity_registry.json: {e}")
        
        for filename in ["canonical_registry_validation.json", "cross_reference_resolution.json"]:
            filepath = self.validation_dir / filename
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                self.fail(f"Invalid JSON in {filename}: {e}")


class TestRegistryStructureAndContent(CanonicalRegistryTestCase):
    """Tests 6-16: Registry structure, uniqueness, and field requirements."""

    @classmethod
    def setUpClass(cls):
        """Load registry and validation data."""
        super().setUpClass()
        registry_path = cls.ontology_dir / "canonical_entity_registry.json"
        validation_path = cls.validation_dir / "canonical_registry_validation.json"
        cls.registry = cls.load_json_file(registry_path)
        cls.validation_report = cls.load_json_file(validation_path)
        
        # Load all source data
        cls.all_source_entities = {}
        for filename in cls.source_filenames:
            filepath = cls.normalized_dir / filename
            data = cls.load_json_file(filepath)
            cls.all_source_entities[filename] = data

    def test_06_one_entry_per_source_entity(self):
        """Test 6: Registry contains exactly one entry for every source entity."""
        total_source = sum(len(entities) for entities in self.all_source_entities.values())
        registry_count = self.registry.get("entity_count", 0)
        self.assertEqual(registry_count, total_source,
                        f"Registry count {registry_count} != source count {total_source}")

    def test_07_total_source_count_equals_entity_count(self):
        """Test 7: Total source count equals registry entity_count."""
        total_source = self.validation_report.get("source_entity_count", 0)
        registry_entity_count = self.validation_report.get("registry_entity_count", 0)
        self.assertEqual(total_source, registry_entity_count,
                        f"Source count {total_source} != registry count {registry_entity_count}")

    def test_08_each_source_entity_id_appears_exactly_once(self):
        """Test 8: Every source entity_id appears exactly once in registry."""
        entity_id_counts = {}
        for entity in self.registry.get("entities", []):
            entity_id = entity.get("entity_id")
            entity_id_counts[entity_id] = entity_id_counts.get(entity_id, 0) + 1
        
        for entity_id, count in entity_id_counts.items():
            self.assertEqual(count, 1,
                           f"Entity ID {entity_id} appears {count} times")

    def test_09_no_unexpected_registry_entity_ids(self):
        """Test 9: No unexpected registry entity_id exists."""
        source_entity_ids = set()
        for entities in self.all_source_entities.values():
            for entity in entities:
                source_entity_ids.add(entity.get("entity_id"))
        
        registry_entity_ids = {e.get("entity_id") for e in self.registry.get("entities", [])}
        unexpected = registry_entity_ids - source_entity_ids
        self.assertEqual(len(unexpected), 0,
                        f"Unexpected entity IDs in registry: {unexpected}")

    def test_10_registry_entities_have_required_fields(self):
        """Test 10: Every registry entity has all required fields."""
        missing_fields_list = []
        for entity in self.registry.get("entities", []):
            entity_id = entity.get("entity_id", "UNKNOWN")
            missing = self.expected_entity_fields - set(entity.keys())
            if missing:
                missing_fields_list.append({
                    "entity_id": entity_id,
                    "missing_fields": list(missing)
                })
        
        self.assertEqual(len(missing_fields_list), 0,
                        f"Entities with missing fields: {missing_fields_list}")

    def test_11_entity_ids_are_globally_unique(self):
        """Test 11: Every entity_id is globally unique."""
        entity_ids = [e.get("entity_id") for e in self.registry.get("entities", [])]
        duplicates = [eid for eid in set(entity_ids) if entity_ids.count(eid) > 1]
        self.assertEqual(len(duplicates), 0,
                        f"Duplicate entity IDs: {duplicates}")

    def test_12_normalized_names_are_non_empty(self):
        """Test 12: Every normalized_name is non-empty."""
        non_empty_normalized = all(
            entity.get("normalized_name", "").strip()
            for entity in self.registry.get("entities", [])
        )
        self.assertTrue(non_empty_normalized,
                       "Some entities have empty normalized_name")

    def test_13_source_files_are_valid(self):
        """Test 13: Every source_file is one of the five expected filenames."""
        valid_filenames = set(self.source_filenames)
        invalid_sources = []
        for entity in self.registry.get("entities", []):
            source_file = entity.get("source_file")
            if source_file not in valid_filenames:
                invalid_sources.append({
                    "entity_id": entity.get("entity_id"),
                    "source_file": source_file
                })
        
        self.assertEqual(len(invalid_sources), 0,
                        f"Entities with invalid source_file: {invalid_sources}")

    def test_14_aliases_are_non_empty_string_lists(self):
        """Test 14: aliases is always a list of non-empty strings."""
        invalid_aliases = []
        for entity in self.registry.get("entities", []):
            aliases = entity.get("aliases")
            entity_id = entity.get("entity_id")
            
            if not isinstance(aliases, list):
                invalid_aliases.append({
                    "entity_id": entity_id,
                    "issue": "aliases is not a list"
                })
                continue
            
            for alias in aliases:
                if not isinstance(alias, str) or not alias.strip():
                    invalid_aliases.append({
                        "entity_id": entity_id,
                        "alias": alias,
                        "issue": "alias is not a non-empty string"
                    })
        
        self.assertEqual(len(invalid_aliases), 0,
                        f"Invalid aliases found: {invalid_aliases}")

    def test_15_no_alias_duplicates_after_normalization(self):
        """Test 15: No alias duplicates exist after normalization."""
        duplicate_aliases = []
        
        def normalize_for_lookup(value):
            import re
            if not isinstance(value, str):
                return ""
            normalized = value.casefold()
            normalized = normalized.strip()
            normalized = normalized.replace("_", " ")
            normalized = re.sub(r"(\w)-(\w)", r"\1 \2", normalized)
            normalized = re.sub(r"\s+", " ", normalized)
            return normalized
        
        for entity in self.registry.get("entities", []):
            aliases = entity.get("aliases", [])
            entity_id = entity.get("entity_id")
            normalized_aliases = [normalize_for_lookup(a) for a in aliases]
            
            seen = set()
            for norm_alias in normalized_aliases:
                if norm_alias in seen:
                    duplicate_aliases.append({
                        "entity_id": entity_id,
                        "normalized_alias": norm_alias
                    })
                seen.add(norm_alias)
        
        self.assertEqual(len(duplicate_aliases), 0,
                        f"Duplicate normalized aliases: {duplicate_aliases}")

    def test_16_registry_and_validation_report_counts_match(self):
        """Test 16: Registry report counts equal their corresponding arrays."""
        registry_entity_count = self.registry.get("entity_count", 0)
        entities_length = len(self.registry.get("entities", []))
        self.assertEqual(registry_entity_count, entities_length,
                        f"entity_count {registry_entity_count} != entities array length {entities_length}")


class TestCrossReferenceValidation(CanonicalRegistryTestCase):
    """Tests 17-24: Cross-reference resolution validation."""

    @classmethod
    def setUpClass(cls):
        """Load cross-reference data."""
        super().setUpClass()
        registry_path = cls.ontology_dir / "canonical_entity_registry.json"
        cross_ref_path = cls.validation_dir / "cross_reference_resolution.json"
        cls.registry = cls.load_json_file(registry_path)
        cls.cross_ref_report = cls.load_json_file(cross_ref_path)

    def test_17_cross_reference_report_counts_match_arrays(self):
        """Test 17: Cross-reference report counts equal their corresponding arrays."""
        report = self.cross_ref_report
        self.assertEqual(report.get("resolved_count", 0),
                        len(report.get("resolved_references", [])),
                        "resolved_count mismatch")
        self.assertEqual(report.get("unresolved_count", 0),
                        len(report.get("unresolved_references", [])),
                        "unresolved_count mismatch")
        self.assertEqual(report.get("ambiguous_count", 0),
                        len(report.get("ambiguous_references", [])),
                        "ambiguous_count mismatch")
        self.assertEqual(report.get("invalid_count", 0),
                        len(report.get("invalid_references", [])),
                        "invalid_count mismatch")

    def test_18_total_references_equation_holds(self):
        """Test 18: total_references = resolved + unresolved + ambiguous + invalid."""
        report = self.cross_ref_report
        total = (report.get("resolved_count", 0) +
                 report.get("unresolved_count", 0) +
                 report.get("ambiguous_count", 0) +
                 report.get("invalid_count", 0))
        reported_total = report.get("total_references", 0)
        self.assertEqual(total, reported_total,
                        f"Sum of categories {total} != total_references {reported_total}")

    def test_19_resolution_rate_is_correct(self):
        """Test 19: Recalculate resolution_rate and verify it matches the report."""
        report = self.cross_ref_report
        resolved = report.get("resolved_count", 0)
        invalid = report.get("invalid_count", 0)
        total = report.get("total_references", 0)
        
        valid_references = total - invalid
        if valid_references > 0:
            calculated_rate = round((resolved / valid_references) * 100, 2)
        else:
            calculated_rate = 0.0
        
        reported_rate = report.get("resolution_rate", 0.0)
        self.assertAlmostEqual(calculated_rate, reported_rate, places=2,
                              msg=f"Calculated rate {calculated_rate} != reported {reported_rate}")

    def test_20_resolved_references_have_valid_entity_ids(self):
        """Test 20: Every resolved reference has valid source and target entity IDs."""
        registry_entity_ids = {e.get("entity_id") for e in self.registry.get("entities", [])}
        
        invalid_refs = []
        for ref in self.cross_ref_report.get("resolved_references", []):
            source_id = ref.get("source_entity_id")
            target_id = ref.get("target_entity_id")
            
            if source_id not in registry_entity_ids:
                invalid_refs.append({
                    "reference": ref.get("reference_value"),
                    "issue": f"source_entity_id {source_id} not in registry"
                })
            if target_id not in registry_entity_ids:
                invalid_refs.append({
                    "reference": ref.get("reference_value"),
                    "issue": f"target_entity_id {target_id} not in registry"
                })
        
        self.assertEqual(len(invalid_refs), 0,
                        f"Invalid resolved references: {invalid_refs}")

    def test_21_resolved_target_ids_exist_in_registry(self):
        """Test 21: Every resolved target ID exists in the registry."""
        registry_entity_ids = {e.get("entity_id") for e in self.registry.get("entities", [])}
        
        missing_targets = []
        for ref in self.cross_ref_report.get("resolved_references", []):
            target_id = ref.get("target_entity_id")
            if target_id not in registry_entity_ids:
                missing_targets.append({
                    "source": ref.get("source_entity_id"),
                    "target": target_id,
                    "reference": ref.get("reference_value")
                })
        
        self.assertEqual(len(missing_targets), 0,
                        f"Resolved references with missing targets: {missing_targets}")

    def test_22_ambiguous_references_have_multiple_candidates(self):
        """Test 22: Every ambiguous reference contains at least two candidate IDs."""
        invalid_ambiguous = []
        for ref in self.cross_ref_report.get("ambiguous_references", []):
            candidates = ref.get("candidate_entity_ids", [])
            if len(candidates) < 2:
                invalid_ambiguous.append({
                    "source": ref.get("source_entity_id"),
                    "reference": ref.get("reference_value"),
                    "candidates": candidates
                })
        
        self.assertEqual(len(invalid_ambiguous), 0,
                        f"Ambiguous references without multiple candidates: {invalid_ambiguous}")

    def test_23_unresolved_references_have_reason(self):
        """Test 23: Every unresolved reference has non-empty reference_value and reason."""
        invalid_unresolved = []
        for ref in self.cross_ref_report.get("unresolved_references", []):
            ref_value = ref.get("reference_value", "").strip()
            reason = ref.get("reason", "").strip()
            
            if not ref_value or not reason:
                invalid_unresolved.append({
                    "source": ref.get("source_entity_id"),
                    "has_value": bool(ref_value),
                    "has_reason": bool(reason)
                })
        
        self.assertEqual(len(invalid_unresolved), 0,
                        f"Unresolved references with missing value or reason: {invalid_unresolved}")

    def test_24_self_references_have_identical_ids(self):
        """Test 24: Every self-reference has identical source and target IDs."""
        invalid_self_refs = []
        for ref in self.cross_ref_report.get("self_references", []):
            source_id = ref.get("source_entity_id")
            target_id = ref.get("target_entity_id")
            
            if source_id != target_id:
                invalid_self_refs.append({
                    "source": source_id,
                    "target": target_id,
                    "reference": ref.get("reference_value")
                })
        
        self.assertEqual(len(invalid_self_refs), 0,
                        f"Self-references with non-identical IDs: {invalid_self_refs}")


class TestRegistryAndValidationConsistency(CanonicalRegistryTestCase):
    """Test 25: Registry status and validation status consistency."""

    @classmethod
    def setUpClass(cls):
        """Load registry and validation data."""
        super().setUpClass()
        registry_path = cls.ontology_dir / "canonical_entity_registry.json"
        validation_path = cls.validation_dir / "canonical_registry_validation.json"
        cls.registry = cls.load_json_file(registry_path)
        cls.validation_report = cls.load_json_file(validation_path)

    def test_25_registry_and_validation_status_are_consistent(self):
        """Test 25: Registry status and validation status are logically consistent."""
        registry_status = self.registry.get("status", "")
        validation_status = self.validation_report.get("status", "")
        
        status_mapping = {
            "PASS": "valid",
            "PASS_WITH_WARNINGS": "valid_with_warnings",
            "FAIL": "invalid"
        }
        
        expected_registry_status = status_mapping.get(validation_status, "")
        self.assertEqual(registry_status, expected_registry_status,
                        f"Registry status {registry_status} inconsistent with validation status {validation_status}")


class TestBuilderReproducibility(CanonicalRegistryTestCase):
    """Tests 26-28: Builder reproducibility and input file immutability."""

    def test_26_builder_does_not_modify_normalized_inputs(self):
        """Test 26: Running the builder does not modify normalized input files."""
        before_hashes = {}
        for filename in self.source_filenames:
            filepath = self.normalized_dir / filename
            before_hashes[filename] = self.compute_file_hash(filepath)
        
        result = subprocess.run(
            [sys.executable, str(self.builder_script)],
            cwd=str(self.project_root),
            capture_output=True,
            timeout=60
        )
        self.assertEqual(result.returncode, 0,
                        f"Builder failed: {result.stderr.decode()}")
        
        after_hashes = {}
        for filename in self.source_filenames:
            filepath = self.normalized_dir / filename
            after_hashes[filename] = self.compute_file_hash(filepath)
        
        for filename in self.source_filenames:
            self.assertEqual(before_hashes[filename], after_hashes[filename],
                           f"Input file {filename} was modified during build")

    def test_27_builder_produces_logically_identical_entries_on_second_run(self):
        """Test 27: Running builder twice produces logically identical registry entries."""
        registry_path = self.ontology_dir / "canonical_entity_registry.json"
        
        registry_run1 = self.load_json_file(registry_path)
        entities_run1 = {e.get("entity_id"): e for e in registry_run1.get("entities", [])}
        
        result = subprocess.run(
            [sys.executable, str(self.builder_script)],
            cwd=str(self.project_root),
            capture_output=True,
            timeout=60
        )
        self.assertEqual(result.returncode, 0,
                        f"Second builder run failed: {result.stderr.decode()}")
        
        registry_run2 = self.load_json_file(registry_path)
        entities_run2 = {e.get("entity_id"): e for e in registry_run2.get("entities", [])}
        
        self.assertEqual(len(entities_run1), len(entities_run2),
                        f"Entity count changed: {len(entities_run1)} -> {len(entities_run2)}")
        
        for entity_id, entity_run1 in entities_run1.items():
            self.assertIn(entity_id, entities_run2,
                         f"Entity {entity_id} missing in second run")
            entity_run2 = entities_run2[entity_id]
            
            for field in ["canonical_name", "normalized_name", "type", "subtype",
                         "layer", "knowledge_category", "source_file", "status"]:
                self.assertEqual(entity_run1.get(field), entity_run2.get(field),
                               f"Field {field} differs for entity {entity_id}")
            
            aliases1 = set(entity_run1.get("aliases", []))
            aliases2 = set(entity_run2.get("aliases", []))
            self.assertEqual(aliases1, aliases2,
                           f"Aliases differ for entity {entity_id}")

    def test_28_builder_exits_successfully_with_valid_inputs(self):
        """Test 28: The builder exits successfully when inputs are valid."""
        result = subprocess.run(
            [sys.executable, str(self.builder_script)],
            cwd=str(self.project_root),
            capture_output=True,
            timeout=60
        )
        self.assertEqual(result.returncode, 0,
                        f"Builder failed with exit code {result.returncode}\n"
                        f"stderr: {result.stderr.decode()}")
        
        registry_path = self.ontology_dir / "canonical_entity_registry.json"
        self.assertTrue(registry_path.exists(),
                      f"Output file canonical_entity_registry.json not created")
        
        for filename in ["canonical_registry_validation.json", "cross_reference_resolution.json"]:
            filepath = self.validation_dir / filename
            self.assertTrue(filepath.exists(),
                          f"Output file {filename} not created")


class TestValidationReportStructure(CanonicalRegistryTestCase):
    """Validation report structure tests."""

    @classmethod
    def setUpClass(cls):
        """Load validation data."""
        super().setUpClass()
        validation_path = cls.validation_dir / "canonical_registry_validation.json"
        cls.validation_report = cls.load_json_file(validation_path)

    def test_validation_report_has_required_fields(self):
        """Verify validation report has required fields."""
        required_fields = {
            "registry_file",
            "status",
            "source_entity_count",
            "registry_entity_count",
            "source_file_counts",
            "errors",
            "warnings"
        }
        
        missing = required_fields - set(self.validation_report.keys())
        self.assertEqual(len(missing), 0,
                        f"Validation report missing fields: {missing}")


class TestCrossReferenceReportStructure(CanonicalRegistryTestCase):
    """Cross-reference report structure tests."""

    @classmethod
    def setUpClass(cls):
        """Load cross-reference data."""
        super().setUpClass()
        cross_ref_path = cls.validation_dir / "cross_reference_resolution.json"
        cls.cross_ref_report = cls.load_json_file(cross_ref_path)

    def test_cross_reference_report_has_required_fields(self):
        """Verify cross-reference report has required fields."""
        required_fields = {
            "status",
            "total_references",
            "resolved_count",
            "unresolved_count",
            "ambiguous_count",
            "invalid_count",
            "resolution_rate"
        }
        
        missing = required_fields - set(self.cross_ref_report.keys())
        self.assertEqual(len(missing), 0,
                        f"Cross-reference report missing fields: {missing}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
