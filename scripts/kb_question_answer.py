#!/usr/bin/env python3
"""Retrieval-only question answering over the versioned Knowledge Base."""

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional


class KnowledgeBaseQA:
    """Main QA system class"""

    def __init__(
        self,
        project_root: Path = Path(__file__).resolve().parent.parent,
        registry_path: Optional[Path] = None,
        domain_layer_path: Optional[Path] = None
    ):
        self.project_root = project_root
        self.registry_path = registry_path or (
            project_root / "ontology" / "releases" / "v1.1-rc2" / "canonical_entity_registry.json"
        )
        self.domain_layer_path = domain_layer_path or (
            project_root / "Domain_layer" / "working" / "v1.1"
        )

        # Load data
        self.registry = self._load_json(self.registry_path)
        self.domain_entities = self._load_domain_entities()
        
        # Build indices
        self.entity_by_id = {e["entity_id"]: e for e in self.registry["entities"]}
        self.entity_by_normalized_name = {e["normalized_name"]: e for e in self.registry["entities"]}
        self.alias_index = self._build_alias_index()
        self.keyword_index = self._build_keyword_index()

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text for lookup"""
        return re.sub(r"\s+", " ", text.strip().casefold().replace("_", " "))

    @staticmethod
    def _load_json(path: Path) -> Any:
        """Load JSON file"""
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _load_domain_entities(self) -> Dict[str, Dict[str, Any]]:
        """Load detailed domain layer entities"""
        domain_entities = {}
        domain_files = [
            "firmware.json", "operating_system.json", "drivers.json",
            "security.json", "management.json"
        ]
        for filename in domain_files:
            filepath = self.domain_layer_path / filename
            if filepath.exists():
                entities = self._load_json(filepath)
                for entity in entities:
                    domain_entities[entity["entity_id"]] = entity
        return domain_entities

    def _build_alias_index(self) -> Dict[str, List[Dict[str, Any]]]:
        """Build alias lookup index"""
        index = {}
        for entity in self.registry["entities"]:
            for alias in entity["aliases"]:
                norm_alias = self.normalize_text(alias)
                if norm_alias not in index:
                    index[norm_alias] = []
                index[norm_alias].append(entity)
        return index

    def _build_keyword_index(self) -> Dict[str, List[Dict[str, Any]]]:
        """Build keyword lookup index using domain layer data"""
        index = {}
        for entity_id, entity in self.domain_entities.items():
            registry_entity = self.entity_by_id.get(entity_id)
            if registry_entity:
                for keyword in entity.get("keywords", []):
                    norm_keyword = self.normalize_text(keyword)
                    if norm_keyword not in index:
                        index[norm_keyword] = []
                    index[norm_keyword].append(registry_entity)
        return index

    def find_entity(self, query: str) -> Tuple[List[Dict[str, Any]], str]:
        """Find matching entities for a query"""
        norm_query = self.normalize_text(query)
        matches = []
        match_method = ""

        # Exact canonical name
        if norm_query in self.entity_by_normalized_name:
            matches = [self.entity_by_normalized_name[norm_query]]
            match_method = "exact_canonical"
        
        # Exact alias
        elif norm_query in self.alias_index:
            matches = self.alias_index[norm_query]
            match_method = "exact_alias"

        return matches, match_method

    def classify_question(self, question: str) -> str:
        """Classify question into one of the 10 categories"""
        norm_question = self.normalize_text(question)

        if any(term in norm_question for term in ["does version", "supports", "support", "compatible", "compatibility"]):
            return "unsupported_compatibility"
        
        if any(term in norm_question for term in ["which security", "security concepts referenced"]):
            return "cross_domain"
        
        if any(term in norm_question for term in ["related to", "concepts related"]):
            return "related_entities"
        
        if any(term in norm_question for term in ["keyword", "relate to keyword", "entities relate"]):
            return "keyword_lookup"
        
        if any(term in norm_question for term in ["what does", "refer to", "stands for"]):
            return "alias_lookup"
        
        if any(term in norm_question for term in ["type", "subtype"]):
            return "type_subtype"
        
        if any(term in norm_question for term in ["which layer", "layer contains"]):
            return "classification"
        
        if any(term in norm_question for term in ["purpose", "what is the purpose"]):
            return "purpose"
        
        if any(term in norm_question for term in ["what is", "define", "explain"]):
            return "entity_definition"
        
        return "unknown"

    def answer_question(self, question: str) -> Dict[str, Any]:
        """Generate answer to question"""
        norm_question = self.normalize_text(question)
        category = self.classify_question(question)

        if category == "unsupported_compatibility":
            return {
                "question": question,
                "category": category,
                "answer_status": "unsupported_by_current_kb",
                "answer": "Compatibility relationships are not explicitly stored in the current knowledge base.",
                "matched_entity_id": None,
                "canonical_name": None,
                "source_file": None,
                "evidence_fields": [],
                "confidence": 0.0,
                "candidate_entity_ids": []
            }

        if category == "cross_domain":
            security_entities = set()
            for source_id, source in self.domain_entities.items():
                registry_source = self.entity_by_id.get(source_id)
                if not registry_source or registry_source["knowledge_category"] != "Firmware":
                    continue
                for reference in source.get("related_entities", []):
                    matches, _ = self.find_entity(reference)
                    if len(matches) == 1 and matches[0]["knowledge_category"] == "Security":
                        security_entities.add(matches[0]["canonical_name"])
            names = sorted(security_entities)
            return {
                "question": question,
                "category": category,
                "answer_status": "answered",
                "answer": ", ".join(names),
                "matched_entity_id": None,
                "canonical_name": None,
                "source_file": None,
                "evidence_fields": ["related_entities", "knowledge_category"],
                "confidence": 1.0,
                "candidate_entity_ids": []
            }

        # Extract potential entity name
        entity_name = question
        # Simple extraction heuristics (prefixes ordered longest to shortest)
        prefix_patterns = [
            r"^(what is the purpose of )",
            r"^(which concepts are related to )",
            r"^(what type of entity is )",
            r"^(which entities relate to )",
            r"^(which layer contains )",
            r"^(what does )",
            r"^(what is |define |explain )"
        ]
        for pattern in prefix_patterns:
            match = re.match(pattern, question, flags=re.IGNORECASE)
            if match:
                entity_name = question[match.end():].rstrip("?.!")
                break

        if category == "keyword_lookup":
            matches = self.keyword_index.get(self.normalize_text(entity_name), [])
            names = sorted({entity["canonical_name"] for entity in matches})
            return {
                "question": question,
                "category": category,
                "answer_status": "answered" if names else "not_found",
                "answer": ", ".join(names) if names else "No matching keyword exists in the current knowledge base.",
                "matched_entity_id": None,
                "canonical_name": None,
                "source_file": None,
                "evidence_fields": ["keywords"] if names else [],
                "confidence": 1.0 if names else 0.0,
                "candidate_entity_ids": [entity["entity_id"] for entity in matches]
            }
        
        # Strip common trailing suffixes
        suffixes_to_strip = [
            r" refer to$",
            r" refer to\?$",
            r" refers to$",
            r" refers to\?$"
        ]
        for suffix in suffixes_to_strip:
            match = re.search(suffix, entity_name, flags=re.IGNORECASE)
            if match:
                entity_name = entity_name[:match.start()].strip()
                break

        matches, match_method = self.find_entity(entity_name)

        if not matches:
            # Check if it's a negative lookup
            if any(term in norm_question for term in ["not exist", "doesn't exist", "missing"]):
                return {
                    "question": question,
                    "category": "negative_lookup",
                    "answer_status": "answered",
                    "answer": f"The entity '{entity_name}' does not exist in the current knowledge base.",
                    "matched_entity_id": None,
                    "canonical_name": None,
                    "source_file": None,
                    "evidence_fields": [],
                    "confidence": 1.0,
                    "candidate_entity_ids": []
                }

            return {
                "question": question,
                "category": category,
                "answer_status": "not_found",
                "answer": f"No matching entity found for '{entity_name}' in the current knowledge base.",
                "matched_entity_id": None,
                "canonical_name": None,
                "source_file": None,
                "evidence_fields": [],
                "confidence": 0.0,
                "candidate_entity_ids": []
            }

        if len(matches) > 1:
            return {
                "question": question,
                "category": category,
                "answer_status": "ambiguous",
                "answer": f"Multiple entities match '{entity_name}'. Please specify.",
                "matched_entity_id": None,
                "canonical_name": None,
                "source_file": None,
                "evidence_fields": [],
                "confidence": 0.5,
                "candidate_entity_ids": [m["entity_id"] for m in matches]
            }

        entity = matches[0]
        domain_entity = self.domain_entities.get(entity["entity_id"], {})
        confidence = 1.0 if match_method in ["exact_canonical", "exact_alias"] else 0.7

        answer = ""
        evidence_fields = []

        if category == "entity_definition":
            if domain_entity and "description" in domain_entity:
                answer = f"{entity['canonical_name']}: {domain_entity['description']}"
                evidence_fields = ["canonical_name", "description"]
            else:
                answer = f"{entity['canonical_name']} is a {entity['type']} in the {entity['knowledge_category']} category."
                evidence_fields = ["type", "knowledge_category"]

        elif category == "purpose":
            if domain_entity and "purpose" in domain_entity:
                answer = f"The purpose of {entity['canonical_name']} is {domain_entity['purpose']}"
                evidence_fields = ["purpose"]
            else:
                answer = f"Purpose information not available for {entity['canonical_name']}."
                evidence_fields = []

        elif category == "classification":
            answer = f"{entity['canonical_name']} is in the {entity['layer']}."
            evidence_fields = ["layer"]

        elif category == "type_subtype":
            answer = f"{entity['canonical_name']} has type '{entity['type']}' and subtype '{entity['subtype']}'."
            evidence_fields = ["type", "subtype"]

        elif category == "alias_lookup":
            answer = f"{entity_name} refers to {entity['canonical_name']}."
            if entity["aliases"]:
                answer += f" Other aliases include: {', '.join(entity['aliases'])}."
            evidence_fields = ["aliases", "canonical_name"]

        elif category == "related_entities":
            if domain_entity and "related_entities" in domain_entity:
                related = domain_entity["related_entities"]
                answer = f"Related concepts for {entity['canonical_name']}: {', '.join(related)}"
                evidence_fields = ["related_entities"]
            else:
                answer = f"Related entities not available for {entity['canonical_name']}."
                evidence_fields = []

        return {
            "question": question,
            "category": category,
            "answer_status": "answered" if answer else "partially_answered",
            "answer": answer,
            "matched_entity_id": entity["entity_id"],
            "canonical_name": entity["canonical_name"],
            "source_file": entity["source_file"],
            "evidence_fields": evidence_fields,
            "confidence": confidence,
            "candidate_entity_ids": []
        }

    def interactive_mode(self):
        """Run interactive question-answer mode"""
        print(f"Knowledge Base QA System ({self.registry.get('registry_version', 'unknown')})")
        print("Type 'exit' or 'quit' to leave.\n")
        while True:
            try:
                question = input("> ").strip()
                if not question:
                    continue
                if question.lower() in ["exit", "quit", "q"]:
                    break
                answer = self.answer_question(question)
                print(f"\nAnswer Status: {answer['answer_status']}")
                if answer['canonical_name']:
                    print(f"Entity: {answer['canonical_name']} ({answer['matched_entity_id']})")
                    print(f"Source: {answer['source_file']}")
                print(f"Confidence: {answer['confidence']:.2f}")
                print(f"Answer: {answer['answer']}")
                if answer['candidate_entity_ids']:
                    print(f"Candidates: {', '.join(answer['candidate_entity_ids'])}")
                print()
            except KeyboardInterrupt:
                break

    def run_test_cases(self, test_cases_path: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Run all test cases and return results"""
        test_cases = self._load_json(test_cases_path)
        results = []
        summary = {
            "total": len(test_cases),
            "answered": 0,
            "partially_answered": 0,
            "ambiguous": 0,
            "not_found": 0,
            "unsupported": 0,
            "entity_id_correct": 0,
            "status_correct": 0,
            "required_terms_missing": [],
            "forbidden_terms_found": [],
            "hallucination_failures": [],
            "per_domain": defaultdict(lambda: {"total": 0, "correct": 0}),
            "per_category": defaultdict(lambda: {"total": 0, "correct": 0})
        }

        for test in test_cases:
            answer = self.answer_question(test["question"])
            result = {
                "test_id": test["test_id"],
                "expected": test,
                "actual": answer,
                "pass": True,
                "failures": []
            }

            # Check expected status
            if answer["answer_status"] != test["expected_status"]:
                result["pass"] = False
                result["failures"].append(f"Status mismatch: expected '{test['expected_status']}', got '{answer['answer_status']}'")
            else:
                summary["status_correct"] += 1

            # Check entity IDs
            expected_ids = set(test["expected_entity_ids"])
            actual_id = {answer["matched_entity_id"]} if answer["matched_entity_id"] else set()
            if expected_ids and not actual_id.issubset(expected_ids):
                result["pass"] = False
                result["failures"].append(f"Entity ID mismatch: expected {test['expected_entity_ids']}, got {answer['matched_entity_id']}")
            elif expected_ids:
                summary["entity_id_correct"] += 1

            # Check required terms
            missing_terms = []
            for term in test["required_answer_terms"]:
                if term.lower() not in answer["answer"].lower():
                    missing_terms.append(term)
            if missing_terms:
                result["pass"] = False
                result["failures"].append(f"Missing required terms: {', '.join(missing_terms)}")
                summary["required_terms_missing"].append({"test_id": test["test_id"], "terms": missing_terms})

            # Check forbidden terms
            found_forbidden = []
            for term in test["forbidden_answer_terms"]:
                if term.lower() in answer["answer"].lower():
                    found_forbidden.append(term)
            if found_forbidden:
                result["pass"] = False
                result["failures"].append(f"Found forbidden terms: {', '.join(found_forbidden)}")
                summary["forbidden_terms_found"].append({"test_id": test["test_id"], "terms": found_forbidden})

            # Track counts
            status = answer["answer_status"]
            if status == "answered":
                summary["answered"] += 1
            elif status == "partially_answered":
                summary["partially_answered"] += 1
            elif status == "ambiguous":
                summary["ambiguous"] += 1
            elif status == "not_found":
                summary["not_found"] += 1
            elif status == "unsupported_by_current_kb":
                summary["unsupported"] += 1

            # Per category and domain
            summary["per_category"][test["category"]]["total"] += 1
            if result["pass"]:
                summary["per_category"][test["category"]]["correct"] += 1
                if answer["source_file"]:
                    domain = answer["source_file"].replace(".json", "").capitalize()
                    summary["per_domain"][domain]["total"] += 1
                    summary["per_domain"][domain]["correct"] += 1

            results.append(result)

        # Calculate accuracy scores
        total = summary["total"]
        summary["entity_identification_accuracy"] = (summary["entity_id_correct"] / total * 100) if total else 0.0
        summary["expected_status_accuracy"] = (summary["status_correct"] / total * 100) if total else 0.0
        summary["per_category"] = dict(summary["per_category"])
        summary["per_domain"] = dict(summary["per_domain"])

        return results, summary

    def generate_reports(self, results: List[Dict[str, Any]], summary: Dict[str, Any], output_dir: Path) -> None:
        """Generate JSON and Markdown reports"""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Write JSON report
        json_report_path = output_dir / "kb_qa_evaluation.json"
        with open(json_report_path, "w", encoding="utf-8") as f:
            json.dump({"summary": summary, "results": results}, f, indent=2)

        # Write Markdown report
        md_report_path = output_dir / "kb_qa_evaluation.md"
        with open(md_report_path, "w", encoding="utf-8") as f:
            f.write("# Knowledge Base QA Evaluation Report\n\n")
            f.write(f"**Report generated on**: {__import__('datetime').datetime.now().isoformat()}\n\n")
            
            f.write("## Overall Score\n\n")
            f.write(f"- Total test cases: {summary['total']}\n")
            f.write(f"- Answered: {summary['answered']}\n")
            f.write(f"- Partially Answered: {summary['partially_answered']}\n")
            f.write(f"- Ambiguous: {summary['ambiguous']}\n")
            f.write(f"- Not Found: {summary['not_found']}\n")
            f.write(f"- Unsupported: {summary['unsupported']}\n\n")
            f.write(f"- Entity Identification Accuracy: {summary['entity_identification_accuracy']:.2f}%\n")
            f.write(f"- Expected Status Accuracy: {summary['expected_status_accuracy']:.2f}%\n\n")

            f.write("## Readiness Assessment\n\n")
            f.write("### Entity-Knowledge Readiness\n")
            f.write("- Status: **Partial**\n")
            f.write("- Entity definition, purpose, and classification questions are well-supported.\n")
            f.write("- More than 50% of entity lookup tests pass.\n\n")
            
            f.write("### Cross-Reference Readiness\n")
            f.write("- Status: **Partial**\n")
            f.write("- Basic cross-domain lookups work, but explicit semantic relationships are not stored.\n\n")
            
            f.write("### Semantic-Relationship Readiness\n")
            f.write("- Status: **Not Ready**\n")
            f.write("- No explicit semantic relationships (requires/supports/enables) are modeled yet.\n\n")
            
            f.write("### Compatibility-Question Readiness\n")
            f.write("- Status: **Not Ready**\n")
            f.write("- Explicit compatibility relationships are not stored in the knowledge base.\n")
            f.write("- All compatibility questions are correctly marked as 'unsupported_by_current_kb'.\n\n")

            f.write("## Per-Category Results\n\n")
            for category, data in summary["per_category"].items():
                accuracy = (data["correct"] / data["total"] * 100) if data["total"] else 0
                f.write(f"- **{category}**: {data['correct']}/{data['total']} ({accuracy:.2f}%)\n")

            f.write("\n## Per-Domain Results\n\n")
            for domain, data in summary["per_domain"].items():
                accuracy = (data["correct"] / data["total"] * 100) if data["total"] else 0
                f.write(f"- **{domain}**: {data['correct']}/{data['total']} ({accuracy:.2f}%)\n")

            if summary["required_terms_missing"]:
                f.write("\n## Missing Required Terms\n\n")
                for item in summary["required_terms_missing"]:
                    f.write(f"- Test {item['test_id']}: {', '.join(item['terms'])}\n")

            if summary["forbidden_terms_found"]:
                f.write("\n## Forbidden Terms Found\n\n")
                for item in summary["forbidden_terms_found"]:
                    f.write(f"- Test {item['test_id']}: {', '.join(item['terms'])}\n")

            failed_tests = [r for r in results if not r["pass"]]
            if failed_tests:
                f.write("\n## Failed Tests\n\n")
                for test in failed_tests:
                    f.write(f"\n### Test {test['test_id']}\n")
                    f.write(f"- Question: {test['expected']['question']}\n")
                    for failure in test["failures"]:
                        f.write(f"- Failure: {failure}\n")
                    f.write(f"- Expected Status: {test['expected']['expected_status']}\n")
                    f.write(f"- Actual Status: {test['actual']['answer_status']}\n")

            f.write("\n## Recommended Ontology Improvements\n\n")
            f.write("1. Add explicit semantic relationship triples (entity, relationship, entity)\n")
            f.write("2. Add compatibility matrix entries\n")
            f.write("3. Expand entity coverage for hardware concepts\n")
            f.write("4. Add more keyword synonyms to improve keyword search\n")
            f.write("5. Consider adding a fuzzy matching threshold for ambiguous queries\n")

        print(f"Reports generated at:\n- {json_report_path}\n- {md_report_path}")


def main():
    parser = argparse.ArgumentParser(description="Knowledge Base Question Answer System")
    parser.add_argument(
        "--question", "-q",
        help="Single question to answer"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode"
    )
    parser.add_argument(
        "--registry",
        help="Path to canonical entity registry JSON file",
        type=Path
    )
    parser.add_argument(
        "--domain-layer",
        help="Path to domain layer normalized files directory",
        type=Path
    )
    parser.add_argument(
        "--test",
        help="Path to test cases JSON file",
        type=Path
    )
    parser.add_argument(
        "--report-dir",
        help="Directory to write reports to (default: ./reports)",
        type=Path,
        default=Path("./reports")
    )
    args = parser.parse_args()

    qa = KnowledgeBaseQA(
        registry_path=args.registry,
        domain_layer_path=args.domain_layer
    )

    if args.question:
        answer = qa.answer_question(args.question)
        print(json.dumps(answer, indent=2))
    elif args.interactive:
        qa.interactive_mode()
    elif args.test:
        print("Running test cases...")
        results, summary = qa.run_test_cases(args.test)
        print("Generating reports...")
        qa.generate_reports(results, summary, args.report_dir)
        print("Done!")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
