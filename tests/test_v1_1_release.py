import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class V11ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parent.parent
        cls.release = cls.root / "ontology" / "releases" / "v1.1-candidate"
        cls.neo4j = cls.root / "neo4j" / "import" / "v1.1-candidate"
        cls.registry = json.loads((cls.release / "canonical_entity_registry.json").read_text(encoding="utf-8"))
        cls.cross = json.loads((cls.release / "cross_references_v1.1.json").read_text(encoding="utf-8"))
        cls.manifest = json.loads((cls.neo4j / "import_manifest.json").read_text(encoding="utf-8"))

    def test_configurable_paths_and_exit_code(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "v1.1-candidate"
            neo = Path(temp) / "neo4j" / "v1.1-candidate"
            result = subprocess.run([sys.executable, str(self.root / "scripts/build_canonical_registry.py"),
                "--input-dir", str(self.root / "Domain_layer/working/v1.1"), "--output-dir", str(output),
                "--neo4j-output-dir", str(neo), "--registry-version", "1.1.0", "--schema-version", "1.1.0"],
                cwd=self.root, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertTrue((output / "validation/release_validation.json").exists())

    def test_stable_existing_ids_and_new_ids_unique(self):
        frozen = {}
        for path in (self.root / "Domain_layer/normalized").glob("*.json"):
            frozen.update({e["name"]: e["entity_id"] for e in json.loads(path.read_text(encoding="utf-8"))})
        current = {e["canonical_name"]: e["entity_id"] for e in self.registry["entities"]}
        self.assertTrue(all(current[name] == entity_id for name, entity_id in frozen.items()))
        ids = [e["entity_id"] for e in self.registry["entities"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_metadata_and_granularity_alias_rules(self):
        required = {"concept_scope", "vendor", "verification_status", "provenance"}
        self.assertTrue(all(required <= set(e) and isinstance(e["provenance"], list) for e in self.registry["entities"]))
        by_name = {e["canonical_name"]: e for e in self.registry["entities"]}
        for parent, child in [("Windows", "Windows 10"), ("Windows", "Windows 11"), ("Linux", "Linux Kernel"), ("Ubuntu", "Ubuntu Pro")]:
            self.assertNotIn(child.casefold(), {a.casefold() for a in by_name[parent]["aliases"]})

    def test_reference_classification_complete_and_safe(self):
        refs = self.cross["references"]
        self.assertEqual(len(refs), self.cross["total_references"])
        self.assertTrue(all(r["status"] in {"resolved", "external", "deferred", "rejected", "ambiguous", "requires_human_review"} for r in refs))
        self.assertFalse(any(r["status"] == "resolved" and r["source_entity_id"] == r["target_entity_id"] for r in refs))
        self.assertFalse(any(r["status"] == "ambiguous" and r.get("target_entity_id") for r in refs))

    def test_change_report(self):
        report = json.loads((self.release / "v1.0_to_v1.1_changes.json").read_text(encoding="utf-8"))
        self.assertEqual(report["changed_entity_ids"], [])
        self.assertEqual(len(report["added_entities"]), 28)
        self.assertEqual(report["removed_entities"], [])

    def test_json_and_csv_outputs(self):
        for path in self.release.rglob("*.json"): json.loads(path.read_text(encoding="utf-8"))
        for name in ("entities.csv", "resolved_references.csv", "external_references.csv"):
            with (self.neo4j / name).open(encoding="utf-8", newline="") as handle: list(csv.reader(handle))

    def test_neo4j_counts_ids_labels_and_relationship_type(self):
        ids = {e["entity_id"] for e in self.registry["entities"]}
        with (self.neo4j / "entities.csv").open(encoding="utf-8", newline="") as handle: nodes = list(csv.DictReader(handle))
        with (self.neo4j / "resolved_references.csv").open(encoding="utf-8", newline="") as handle: refs = list(csv.DictReader(handle))
        self.assertEqual(len(nodes), self.registry["entity_count"])
        self.assertEqual(len(refs), self.manifest["resolved_staging_relationship_count"])
        self.assertTrue(all(r[":START_ID(Entity)"] in ids and r[":END_ID(Entity)"] in ids and r[":TYPE"] == "RELATED_TO" for r in refs))
        labels = {"Entity", "Firmware", "OperatingSystem", "Driver", "SecurityComponent", "ManagementTool"}
        self.assertTrue(all(set(row[":LABEL"].split(";")) <= labels for row in nodes))

    def test_constraints_manifest_and_checksums(self):
        cypher = (self.neo4j / "neo4j_constraints.cypher").read_text(encoding="utf-8")
        self.assertIn("IF NOT EXISTS", cypher)
        self.assertNotIn("DELETE", cypher.upper())
        for name, expected in self.manifest["checksums"].items():
            self.assertEqual(hashlib.sha256((self.neo4j / name).read_bytes()).hexdigest(), expected)

    def test_deterministic_repeated_generation(self):
        with tempfile.TemporaryDirectory() as temp:
            release = Path(temp) / "v1.1-candidate"
            neo4j = Path(temp) / "neo4j" / "v1.1-candidate"
            command = [sys.executable, str(self.root / "scripts/build_canonical_registry.py"),
                "--input-dir", str(self.root / "Domain_layer/working/v1.1"), "--output-dir", str(release),
                "--neo4j-output-dir", str(neo4j), "--registry-version", "1.1.0", "--schema-version", "1.1.0"]
            first = subprocess.run(command, cwd=self.root, capture_output=True, timeout=60)
            self.assertEqual(first.returncode, 0, first.stderr.decode())
            before = {p.relative_to(release): p.read_bytes() for p in release.rglob("*") if p.is_file()}
            second = subprocess.run(command, cwd=self.root, capture_output=True, timeout=60)
            self.assertEqual(second.returncode, 0, second.stderr.decode())
            after = {p.relative_to(release): p.read_bytes() for p in release.rglob("*") if p.is_file()}
            self.assertEqual(before, after)

    def test_release_validation_status(self):
        validation = json.loads((self.release / "validation/release_validation.json").read_text(encoding="utf-8"))
        self.assertEqual(validation["status"], "READY_WITH_WARNINGS")
        self.assertTrue(validation["frozen_v1_0_unchanged"])


if __name__ == "__main__":
    unittest.main()
