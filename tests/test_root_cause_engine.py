# file: tests/test_root_cause_engine.py
import sys
import unittest
from pathlib import Path

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ComplianceEngine.root_cause_engine import RootCauseEngine

class TestRootCauseEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = RootCauseEngine()
        cls.device_id = "DEV-000002"
        # Generate data once for assertions
        cls.violations = cls.engine.generate_root_causes(cls.device_id)
        cls.summary = cls.engine.generate_summary(cls.device_id)
        cls.llm_context = cls.engine.generate_llm_context(cls.device_id)

    @classmethod
    def tearDownClass(cls):
        cls.engine.close()

    def test_01_violations_returned(self):
        # We expect a list of violations (each represents a non-compliant status)
        self.assertIsInstance(self.violations, list)
        for v in self.violations:
            self.assertEqual(v.get("device_id"), self.device_id)
            self.assertNotEqual(v.get("status"), "COMPLIANT")
            
            # Check fields
            self.assertIn("rule_id", v)
            self.assertIn("severity", v)
            self.assertIn("status", v)
            self.assertIn("affected_component", v)
            self.assertIn("required_component", v)
            self.assertIn("required_version", v)
            self.assertIn("installed_version", v)
            self.assertIn("expected", v)
            self.assertIn("actual", v)
            
            # Verify impact & category exist, root_cause is non-empty
            self.assertIn("impact", v)
            self.assertIsInstance(v.get("impact"), str)
            self.assertNotEqual(v.get("impact"), "")
            
            self.assertIn("category", v)
            self.assertIsInstance(v.get("category"), str)
            self.assertIn(v.get("category"), ["Firmware", "OperatingSystem", "Driver", "Security", "Management", "Hardware", "Unknown"])
            
            self.assertIn("root_cause", v)
            self.assertIsInstance(v.get("root_cause"), str)
            self.assertTrue(len(v.get("root_cause").strip()) > 0)

    def test_02_summary_generated(self):
        self.assertIsInstance(self.summary, dict)
        self.assertEqual(self.summary.get("device_id"), self.device_id)
        self.assertIn("critical_count", self.summary)
        self.assertIn("warning_count", self.summary)
        self.assertIn("non_compliant_count", self.summary)
        self.assertIn("overall_status", self.summary)

        # Dynamic validation without hardcoding values
        critical = self.summary.get("critical_count")
        warning = self.summary.get("warning_count")
        non_compliant = self.summary.get("non_compliant_count")
        
        self.assertGreaterEqual(critical, 0)
        self.assertGreaterEqual(warning, 0)
        self.assertGreaterEqual(non_compliant, 0)

        # Reconcile counts
        total_violations = len(self.violations)
        self.assertEqual(critical + warning + non_compliant, total_violations)

    def test_03_overall_status_logic_works(self):
        critical = self.summary.get("critical_count")
        warning = self.summary.get("warning_count")
        non_compliant = self.summary.get("non_compliant_count")
        overall = self.summary.get("overall_status")

        if critical > 0:
            self.assertEqual(overall, "CRITICAL")
        elif warning > 0:
            self.assertEqual(overall, "WARNING")
        elif non_compliant > 0:
            self.assertEqual(overall, "NON_COMPLIANT")
        else:
            self.assertEqual(overall, "COMPLIANT")

    def test_04_llm_context_generated(self):
        self.assertIsInstance(self.llm_context, dict)
        self.assertEqual(self.llm_context.get("device_id"), self.device_id)
        self.assertIn("overall_status", self.llm_context)
        self.assertIsInstance(self.llm_context.get("critical_findings"), list)
        self.assertIsInstance(self.llm_context.get("warning_findings"), list)
        self.assertIsInstance(self.llm_context.get("root_causes"), list)
        
        # Verify lists contents match findings
        for finding in self.llm_context.get("critical_findings"):
            self.assertIsInstance(finding, str)
            self.assertTrue(len(finding) > 0)
            
        for finding in self.llm_context.get("warning_findings"):
            self.assertIsInstance(finding, str)
            self.assertTrue(len(finding) > 0)

if __name__ == "__main__":
    unittest.main()
