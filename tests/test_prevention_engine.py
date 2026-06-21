# file: tests/test_prevention_engine.py
import sys
import unittest
from pathlib import Path

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ComplianceEngine.prevention_engine import PreventionEngine

class TestPreventionEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = PreventionEngine()
        cls.device_id = "DEV-000002"
        cls.guidance = cls.engine.generate_prevention_guidance(cls.device_id)
        cls.summary = cls.engine.generate_prevention_summary(cls.device_id)
        cls.llm_context = cls.engine.generate_llm_prevention_context(cls.device_id)

    @classmethod
    def tearDownClass(cls):
        cls.engine.close()

    def test_01_guidance_records_returned(self):
        self.assertIsInstance(self.guidance, list)
        
        for g in self.guidance:
            self.assertIn("rule_id", g)
            
            # Check fields
            self.assertIn("category", g)
            self.assertIsInstance(g.get("category"), str)
            self.assertIn(g.get("category"), ["Firmware", "OperatingSystem", "Driver", "Security", "Management", "Hardware", "Unknown"])
            
            self.assertIn("priority", g)
            self.assertIn(g.get("priority"), ["HIGH", "MEDIUM", "LOW"])
            
            # Horizons lists checks
            for horizon in ["short_term", "medium_term", "long_term"]:
                self.assertIn(horizon, g)
                self.assertIsInstance(g.get(horizon), list)
                self.assertTrue(len(g.get(horizon)) > 0)
                for item in g.get(horizon):
                    self.assertIsInstance(item, str)
                    self.assertTrue(len(item.strip()) > 0)
                    
            # Controls and opportunities checks
            self.assertIn("governance_controls", g)
            self.assertIsInstance(g.get("governance_controls"), list)
            self.assertTrue(len(g.get("governance_controls")) > 0)
            for ctrl in g.get("governance_controls"):
                self.assertIsInstance(ctrl, str)
                self.assertTrue(len(ctrl.strip()) > 0)
                
            self.assertIn("automation_opportunities", g)
            self.assertIsInstance(g.get("automation_opportunities"), list)
            self.assertTrue(len(g.get("automation_opportunities")) > 0)
            for opp in g.get("automation_opportunities"):
                self.assertIsInstance(opp, str)
                self.assertTrue(len(opp.strip()) > 0)

    def test_02_prevention_summary_generated(self):
        self.assertIsInstance(self.summary, dict)
        self.assertEqual(self.summary.get("device_id"), self.device_id)
        
        self.assertIn("top_risks", self.summary)
        self.assertIsInstance(self.summary.get("top_risks"), list)
        for risk in self.summary.get("top_risks"):
            self.assertIsInstance(risk, str)
            self.assertTrue(len(risk) > 0)
            
        self.assertIn("recommended_programs", self.summary)
        self.assertIsInstance(self.summary.get("recommended_programs"), list)
        for prog in self.summary.get("recommended_programs"):
            self.assertIsInstance(prog, str)
            self.assertTrue(len(prog) > 0)
            
        self.assertIn("automation_candidates", self.summary)
        self.assertIsInstance(self.summary.get("automation_candidates"), list)
        for cand in self.summary.get("automation_candidates"):
            self.assertIsInstance(cand, str)
            self.assertTrue(len(cand) > 0)

    def test_03_llm_context_generated(self):
        self.assertIsInstance(self.llm_context, dict)
        self.assertEqual(self.llm_context.get("device_id"), self.device_id)
        self.assertIn("overall_status", self.llm_context)
        self.assertIsInstance(self.llm_context.get("high_priority_prevention"), list)
        self.assertIsInstance(self.llm_context.get("prevention_guidance"), list)
        
        for item in self.llm_context.get("high_priority_prevention"):
            self.assertIsInstance(item, str)
            self.assertTrue(len(item) > 0)

if __name__ == "__main__":
    unittest.main()
