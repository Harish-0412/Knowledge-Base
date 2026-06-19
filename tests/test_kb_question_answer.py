#!/usr/bin/env python3
"""Grounded QA tests whose expected answers come directly from RC2 data."""

import json
import sys
import unittest
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.kb_question_answer import KnowledgeBaseQA


class TestKnowledgeBaseQA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parent.parent
        cls.registry_path = cls.root / "ontology/releases/v1.1-rc2/canonical_entity_registry.json"
        cls.domain_path = cls.root / "Domain_layer/working/v1.1"
        cls.qa = KnowledgeBaseQA(cls.root, cls.registry_path, cls.domain_path)
        cls.registry = json.loads(cls.registry_path.read_text(encoding="utf-8"))
        cls.registry_by_id = {entity["entity_id"]: entity for entity in cls.registry["entities"]}
        cls.domain_by_id = {}
        for path in cls.domain_path.glob("*.json"):
            cls.domain_by_id.update({entity["entity_id"]: entity for entity in json.loads(path.read_text(encoding="utf-8"))})

    def test_uses_real_rc2_sources(self):
        self.assertEqual(self.qa.registry_path.resolve(), self.registry_path.resolve())
        self.assertEqual(self.qa.domain_layer_path.resolve(), self.domain_path.resolve())
        self.assertEqual(len(self.qa.registry["entities"]), 54)
        self.assertEqual(set(self.registry_by_id), set(self.domain_by_id))

    def test_every_definition_is_exactly_grounded(self):
        for entity_id, registry_entity in self.registry_by_id.items():
            with self.subTest(entity_id=entity_id):
                source = self.domain_by_id[entity_id]
                result = self.qa.answer_question(f"What is {registry_entity['canonical_name']}?")
                self.assertEqual(result["answer_status"], "answered")
                self.assertEqual(result["matched_entity_id"], entity_id)
                self.assertEqual(result["answer"], f"{registry_entity['canonical_name']}: {source['description']}")
                self.assertEqual(result["evidence_fields"], ["canonical_name", "description"])

    def test_every_purpose_is_exactly_grounded(self):
        for entity_id, registry_entity in self.registry_by_id.items():
            with self.subTest(entity_id=entity_id):
                source = self.domain_by_id[entity_id]
                result = self.qa.answer_question(f"What is the purpose of {registry_entity['canonical_name']}?")
                self.assertEqual(result["matched_entity_id"], entity_id)
                self.assertEqual(result["answer"], f"{registry_entity['canonical_name']} purpose: {source['purpose']}")
                self.assertEqual(result["evidence_fields"], ["purpose"])

    def test_every_classification_and_type_is_registry_grounded(self):
        for entity_id, entity in self.registry_by_id.items():
            with self.subTest(entity_id=entity_id, question="layer"):
                result = self.qa.answer_question(f"Which layer contains {entity['canonical_name']}?")
                self.assertEqual(result["answer"], f"{entity['canonical_name']} is in the {entity['layer']}.")
            with self.subTest(entity_id=entity_id, question="type"):
                result = self.qa.answer_question(f"What type of entity is {entity['canonical_name']}?")
                self.assertEqual(result["answer"], f"{entity['canonical_name']} has type '{entity['type']}' and subtype '{entity['subtype']}'.")

    def test_every_unique_alias_resolves_without_invention(self):
        aliases = defaultdict(list)
        for entity in self.registry["entities"]:
            for alias in entity["aliases"]:
                aliases[self.qa.normalize_text(alias)].append((alias, entity))
        for matches in aliases.values():
            if len(matches) != 1:
                continue
            alias, entity = matches[0]
            with self.subTest(alias=alias):
                result = self.qa.answer_question(f"What does {alias} refer to?")
                self.assertEqual(result["matched_entity_id"], entity["entity_id"])
                expected = f"{alias} refers to {entity['canonical_name']}."
                if entity["aliases"]:
                    expected += f" Other aliases include: {', '.join(entity['aliases'])}."
                self.assertEqual(result["answer"], expected)

    def test_related_entity_answers_copy_source_values(self):
        for entity_id, source in self.domain_by_id.items():
            if not source.get("related_entities"):
                continue
            entity = self.registry_by_id[entity_id]
            with self.subTest(entity_id=entity_id):
                result = self.qa.answer_question(f"Which concepts are related to {entity['canonical_name']}?")
                expected = f"Related concepts for {entity['canonical_name']}: {', '.join(source['related_entities'])}"
                self.assertEqual(result["answer"], expected)
                self.assertEqual(result["evidence_fields"], ["related_entities"])

    def test_keyword_answers_are_built_from_stored_keywords(self):
        keyword = "measured boot"
        expected = sorted({self.registry_by_id[eid]["canonical_name"] for eid, source in self.domain_by_id.items()
                           if keyword in {self.qa.normalize_text(value) for value in source.get("keywords", [])}})
        result = self.qa.answer_question("Which entities relate to measured boot?")
        self.assertEqual(result["answer"], ", ".join(expected))
        self.assertEqual(sorted(result["candidate_entity_ids"]), sorted(
            eid for eid, source in self.domain_by_id.items()
            if keyword in {self.qa.normalize_text(value) for value in source.get("keywords", [])}))

    def test_cross_domain_answer_uses_actual_firmware_references(self):
        expected = set()
        for entity_id, source in self.domain_by_id.items():
            if self.registry_by_id[entity_id]["knowledge_category"] != "Firmware":
                continue
            for reference in source.get("related_entities", []):
                matches, _ = self.qa.find_entity(reference)
                if len(matches) == 1 and matches[0]["knowledge_category"] == "Security":
                    expected.add(matches[0]["canonical_name"])
        result = self.qa.answer_question("Which security concepts are referenced by firmware entities?")
        self.assertEqual(result["answer"], ", ".join(sorted(expected)))

    def test_unsupported_compatibility_never_invents_an_answer(self):
        result = self.qa.answer_question("Does BIOS support Windows 11?")
        self.assertEqual(result["answer_status"], "unsupported_by_current_kb")
        self.assertIsNone(result["matched_entity_id"])
        self.assertEqual(result["evidence_fields"], [])
        self.assertEqual(result["confidence"], 0.0)

    def test_unknown_entity_returns_not_found(self):
        result = self.qa.answer_question("What is Entity-That-Is-Not-In-The-Knowledge-Base?")
        self.assertEqual(result["answer_status"], "not_found")
        self.assertIsNone(result["matched_entity_id"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
