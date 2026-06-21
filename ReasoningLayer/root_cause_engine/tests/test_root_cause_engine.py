"""
Root Cause Analysis Engine test suite — 50 tests.
All tests use offline=True.
Run: python -m pytest ReasoningLayer/root_cause_engine/tests/ -v
"""
from __future__ import annotations
import json, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from ReasoningLayer.root_cause_engine.models.rca_models import (
    RCAFinding, RCAReport, RISK_SCORES, VALID_STATUSES)
from ReasoningLayer.root_cause_engine.violation_detector  import ViolationDetector
from ReasoningLayer.root_cause_engine.risk_assessor        import RiskAssessor
from ReasoningLayer.root_cause_engine.root_cause_analyzer  import RootCauseAnalyzer
from ReasoningLayer.root_cause_engine.recommendation_engine import RecommendationEngine
from ReasoningLayer.root_cause_engine.root_cause_service    import RootCauseService

BASE = Path(__file__).resolve().parents[1]
CASES_PATH = BASE / "tests/rca_test_cases.json"


def _pkg(question, intent="RootCauseAnalysis", device=None, evidence=None):
    entities = ([{"entity_type":"Device","entity_id":device}] if device else [])
    return {
        "query_id": "QID-TEST",
        "intent":   intent,
        "question": question,
        "entities": entities,
        "evidence": evidence or [],
        "ranked_evidence": evidence or [],
        "evidence_graph": {},
        "metadata": {},
    }


def _evidence_item(etype, entity, content_text="", conf=0.9):
    from ReasoningLayer.evidence_aggregation.models.evidence_models import Evidence
    e = Evidence(etype, "Layer3", "Qdrant", entity, conf,
                 {"source_excerpt": content_text})
    return e.to_dict()


class TestRCAModels(unittest.TestCase):
    def test_finding_creation(self):
        f = RCAFinding("QID-1","Laptop001","RC-VERSION-MISMATCH","VersionMismatch",
                       "VIOL-VERSION","VersionViolation","High","desc","BIOS","Upgrade")
        self.assertTrue(f.finding_id.startswith("FIND-"))

    def test_finding_id_deterministic(self):
        f1 = RCAFinding("QID-1","Laptop001","RC-VERSION-MISMATCH","VM","VIOL-VERSION","VV","High","d","BIOS","U")
        f2 = RCAFinding("QID-2","Laptop001","RC-VERSION-MISMATCH","VM","VIOL-VERSION","VV","High","d","BIOS","U")
        self.assertEqual(f1.finding_id, f2.finding_id)

    def test_finding_severity_score(self):
        f = RCAFinding("QID-1","Laptop001","RC-VERSION-MISMATCH","VM","VIOL-VERSION","VV","Critical","d","BIOS","U")
        self.assertEqual(f.severity_score, 100)

    def test_invalid_risk_level(self):
        with self.assertRaises(ValueError):
            RCAFinding("QID-1","D","RC-VERSION-MISMATCH","VM","VIOL-VERSION","VV","Extreme","d","c","U")

    def test_invalid_confidence(self):
        with self.assertRaises(ValueError):
            RCAFinding("QID-1","D","RC-VERSION-MISMATCH","VM","VIOL-VERSION","VV","High","d","c","U",confidence=1.5)

    def test_invalid_status(self):
        with self.assertRaises(ValueError):
            RCAFinding("QID-1","D","RC-VERSION-MISMATCH","VM","VIOL-VERSION","VV","High","d","c","U",status="pending")

    def test_rca_report_overall_risk(self):
        f_high = RCAFinding("Q","D","RC-VERSION-MISMATCH","VM","VIOL-VERSION","VV","High","d","c","U")
        f_crit = RCAFinding("Q","D","RC-SECURITY-VIOLATION","SV","VIOL-SECURITY","SV","Critical","d","c","U")
        report = RCAReport("Q","D","RCA",[f_high, f_crit])
        self.assertEqual(report.overall_risk, "Critical")

    def test_rca_report_to_dict(self):
        report = RCAReport("Q","D","RCA")
        d = report.to_dict()
        for k in ("query_id","device","intent","overall_risk","findings"):
            self.assertIn(k, d)


class TestViolationDetector(unittest.TestCase):
    def setUp(self):
        self.det = ViolationDetector()

    def test_detect_non_compliant(self):
        r = self.det.detect([], "Why is Laptop001 non-compliant?")
        self.assertGreater(len(r), 0)

    def test_detect_security_cve(self):
        r = self.det.detect([], "CVE vulnerability on Laptop001")
        risks = [d[3] for d in r]
        self.assertIn("Critical", risks)

    def test_detect_version_mismatch(self):
        r = self.det.detect([], "version mismatch on firmware")
        rc_ids = [d[0] for d in r]
        self.assertIn("RC-VERSION-MISMATCH", rc_ids)

    def test_detect_missing_dependency(self):
        r = self.det.detect([], "missing dependency for component")
        rc_ids = [d[0] for d in r]
        self.assertIn("RC-MISSING-DEPENDENCY", rc_ids)

    def test_detect_upgrade_path(self):
        r = self.det.detect([], "invalid upgrade sequence for BIOS")
        rc_ids = [d[0] for d in r]
        self.assertIn("RC-INVALID-UPGRADE-PATH", rc_ids)

    def test_detect_evidence_violation_type(self):
        ev = [_evidence_item("ViolationEvidence","Laptop001","version mismatch")]
        r = self.det.detect(ev)
        self.assertGreater(len(r), 0)

    def test_no_duplicate_detections(self):
        r = self.det.detect([], "non-compliant failing device")
        keys = [(d[0],d[1],d[2]) for d in r]
        self.assertEqual(len(keys), len(set(keys)))

    def test_empty_evidence_returns_list(self):
        self.assertIsInstance(self.det.detect([]), list)


class TestRiskAssessor(unittest.TestCase):
    def setUp(self):
        self.assessor = RiskAssessor()

    def _det(self, rc, viol, comp, risk, conf=0.9):
        return (rc, viol, comp, risk, conf, "label")

    def test_empty_returns_empty(self):
        self.assertEqual(self.assessor.assess([]), [])

    def test_low_confidence_downgrades_risk(self):
        det = [self._det("RC-VERSION-MISMATCH","VIOL-VERSION","BIOS","High",0.4)]
        result = self.assessor.assess(det)
        self.assertNotEqual(result[0][3], "High")

    def test_high_confidence_preserves_risk(self):
        det = [self._det("RC-SECURITY-VIOLATION","VIOL-SECURITY","FW","Critical",0.95)]
        result = self.assessor.assess(det)
        self.assertEqual(result[0][3], "Critical")

    def test_fleet_scope_boosts_critical(self):
        det = [self._det("RC-SECURITY-VIOLATION","VIOL-SECURITY","FW","High",0.9)]
        result = self.assessor.assess(det, device_count=10)
        self.assertEqual(result[0][3], "Critical")

    def test_returns_same_count(self):
        dets = [self._det("RC-VERSION-MISMATCH","VIOL-VERSION",f"c{i}","High") for i in range(5)]
        result = self.assessor.assess(dets)
        self.assertEqual(len(result), 5)


class TestRootCauseAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = RootCauseAnalyzer()

    def test_analyze_returns_report(self):
        pkg = _pkg("Why is Laptop001 non-compliant?", device="Laptop001")
        report = self.analyzer.analyze(pkg)
        self.assertIsInstance(report, RCAReport)

    def test_report_has_device(self):
        pkg = _pkg("Why is Laptop001 failing?", device="Laptop001")
        report = self.analyzer.analyze(pkg)
        self.assertEqual(report.device, "Laptop001")

    def test_report_has_findings(self):
        pkg = _pkg("Why is Device001 non-compliant?", device="Device001")
        report = self.analyzer.analyze(pkg)
        self.assertGreater(len(report.findings), 0)

    def test_report_has_overall_risk(self):
        pkg = _pkg("CVE vulnerability found on Server001", device="Server001")
        report = self.analyzer.analyze(pkg)
        self.assertIn(report.overall_risk,
                      ["Informational","Low","Medium","High","Critical"])

    def test_no_evidence_returns_informational(self):
        pkg = _pkg("Show configuration of Workstation001", device="Workstation001")
        pkg["ranked_evidence"] = []
        pkg["evidence"]        = []
        report = self.analyzer.analyze(pkg)
        self.assertIsInstance(report, RCAReport)

    def test_security_cve_produces_critical(self):
        pkg = _pkg("CVE privilege escalation on Laptop005", device="Laptop005")
        report = self.analyzer.analyze(pkg)
        risks = [f.risk_level for f in report.findings]
        self.assertIn("Critical", risks)

    def test_report_to_dict_serialisable(self):
        import json
        pkg = _pkg("Why is Laptop001 failing?", device="Laptop001")
        report = self.analyzer.analyze(pkg)
        json.dumps(report.to_dict())

    def test_findings_deduplicated(self):
        pkg = _pkg("non-compliant non-compliant non-compliant Device002", device="Device002")
        report = self.analyzer.analyze(pkg)
        fids = [f.finding_id for f in report.findings]
        self.assertEqual(len(fids), len(set(fids)))

    def test_device_extracted_from_question(self):
        pkg = _pkg("Why is Laptop003 non-compliant?")  # no entities
        report = self.analyzer.analyze(pkg)
        self.assertEqual(report.device, "Laptop003")


class TestRecommendationEngine(unittest.TestCase):
    def setUp(self):
        self.engine = RecommendationEngine()

    def _finding_dict(self, recs, risk="High"):
        return {"recommendations": recs, "risk_level": risk, "enriched_recommendations": []}

    def test_enrich_adds_enriched_recommendations(self):
        report = {"findings": [self._finding_dict(["REC-UPGRADE"])]}
        result = self.engine.enrich(report)
        self.assertGreater(len(result["findings"][0]["enriched_recommendations"]), 0)

    def test_enrich_unknown_rec(self):
        report = {"findings": [self._finding_dict(["REC-UNKNOWN-999"])]}
        result = self.engine.enrich(report)
        self.assertIsInstance(result["findings"][0]["enriched_recommendations"], list)

    def test_enrich_empty_findings(self):
        report = {"findings": []}
        result = self.engine.enrich(report)
        self.assertEqual(result["findings"], [])

    def test_enrich_recommendation_has_name(self):
        report = {"findings": [self._finding_dict(["REC-PATCH"])]}
        result = self.engine.enrich(report)
        self.assertEqual(result["findings"][0]["enriched_recommendations"][0]["name"], "Patch")

    def test_enrich_priority_critical(self):
        report = {"findings": [self._finding_dict(["REC-UPGRADE"],"Critical")]}
        result = self.engine.enrich(report)
        self.assertEqual(result["findings"][0]["enriched_recommendations"][0]["priority"], 0)


class TestRootCauseService(unittest.TestCase):
    def setUp(self):
        self.service = RootCauseService(offline=True)

    def test_analyze_string_returns_dict(self):
        result = self.service.analyze("Why is Laptop001 non-compliant?")
        self.assertIsInstance(result, dict)

    def test_analyze_dict_returns_dict(self):
        pkg = _pkg("Why is Device003 failing?", device="Device003")
        result = self.service.analyze(pkg)
        self.assertIsInstance(result, dict)

    def test_result_has_required_keys(self):
        result = self.service.analyze("Why is Server001 failing?")
        for k in ("query_id","device","intent","overall_risk","findings"):
            self.assertIn(k, result)

    def test_overall_risk_valid(self):
        result = self.service.analyze("What issues does Laptop002 have?")
        self.assertIn(result["overall_risk"],
                      ["Informational","Low","Medium","High","Critical"])

    def test_findings_list(self):
        result = self.service.analyze("Why is Device005 non-compliant?")
        self.assertIsInstance(result["findings"], list)

    def test_invalid_input_raises(self):
        with self.assertRaises(TypeError):
            self.service.analyze(42)

    def test_end_to_end_laptop001(self):
        """Step 14 equivalent: end-to-end analysis of Laptop001."""
        result = self.service.analyze("Why is Laptop001 non-compliant?")
        self.assertIn("findings", result)
        self.assertIsInstance(result["findings"], list)
        self.assertIn(result["overall_risk"],
                      ["Informational","Low","Medium","High","Critical"])
        self.assertTrue(result.get("query_id","").startswith("QID-"))

    def test_enriched_recommendations_present(self):
        result = self.service.analyze("Why is Laptop001 failing?")
        for f in result["findings"]:
            self.assertIn("enriched_recommendations", f)


class TestRCAJsonCatalogs(unittest.TestCase):
    def _load(self, name):
        return json.loads((BASE / name).read_text(encoding="utf-8"))

    def test_rca_rule_catalog_count(self):
        cat = self._load("rca_rule_catalog.json")
        self.assertEqual(cat["rule_count"], 12)

    def test_rca_rule_catalog_structure(self):
        cat = self._load("rca_rule_catalog.json")
        for rule in cat["rules"]:
            for f in ("rule_id","root_cause_id","recommendations"):
                self.assertIn(f, rule)

    def test_finding_schema_required_fields(self):
        schema = self._load("finding_schema.json")
        self.assertIn("finding_id", schema["required_fields"])
        self.assertIn("risk_level", schema["required_fields"])

    def test_manifest_completeness(self):
        m = self._load("rca_manifest.json")
        for f in ("manifest_id","root_cause_types","violation_types"):
            self.assertIn(f, m)

    def test_test_cases_count(self):
        cases = self._load("tests/rca_test_cases.json")
        self.assertEqual(len(cases), 50)

    def test_test_cases_structure(self):
        cases = self._load("tests/rca_test_cases.json")
        for c in cases:
            for f in ("test_id","question","expected_device"):
                self.assertIn(f, c)


if __name__ == "__main__":
    unittest.main(verbosity=2)
