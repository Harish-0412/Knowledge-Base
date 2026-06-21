# file: tests/test_recommendation_engine.py
import sys
import unittest
from pathlib import Path

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ComplianceEngine.recommendation_engine import RecommendationEngine

class TestRecommendationEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = RecommendationEngine()
        cls.device_id = "DEV-000002"
        cls.recommendations = cls.engine.generate_recommendations(cls.device_id)
        cls.llm_context = cls.engine.generate_llm_recommendation_context(cls.device_id)

    @classmethod
    def tearDownClass(cls):
        cls.engine.close()

    def test_01_recommendations_returned(self):
        self.assertIsInstance(self.recommendations, list)
        
        for rec in self.recommendations:
            self.assertIn("rule_id", rec)
            
            # Check for category, priority, risk_level
            self.assertIn("category", rec)
            self.assertIsInstance(rec.get("category"), str)
            self.assertIn(rec.get("category"), ["Firmware", "OperatingSystem", "Driver", "Security", "Management", "Hardware", "Unknown"])
            
            self.assertIn("priority", rec)
            self.assertIn(rec.get("priority"), ["HIGH", "MEDIUM", "LOW"])
            
            self.assertIn("risk_level", rec)
            self.assertIn(rec.get("risk_level"), ["HIGH", "MEDIUM", "LOW"])
            
            # Check summary exists
            self.assertIn("summary", rec)
            self.assertIsInstance(rec.get("summary"), str)
            self.assertTrue(len(rec.get("summary").strip()) > 0)
            
            # Check immediate_actions, verification_steps, follow_up_actions exist and are lists of strings
            self.assertIn("immediate_actions", rec)
            self.assertIsInstance(rec.get("immediate_actions"), list)
            self.assertTrue(len(rec.get("immediate_actions")) > 0)
            for action in rec.get("immediate_actions"):
                self.assertIsInstance(action, str)
                self.assertTrue(len(action.strip()) > 0)
                
            self.assertIn("verification_steps", rec)
            self.assertIsInstance(rec.get("verification_steps"), list)
            self.assertTrue(len(rec.get("verification_steps")) > 0)
            for step in rec.get("verification_steps"):
                self.assertIsInstance(step, str)
                self.assertTrue(len(step.strip()) > 0)
                
            self.assertIn("follow_up_actions", rec)
            self.assertIsInstance(rec.get("follow_up_actions"), list)
            self.assertTrue(len(rec.get("follow_up_actions")) > 0)
            for follow in rec.get("follow_up_actions"):
                self.assertIsInstance(follow, str)
                self.assertTrue(len(follow.strip()) > 0)

    def test_02_llm_context_generated(self):
        self.assertIsInstance(self.llm_context, dict)
        self.assertEqual(self.llm_context.get("device_id"), self.device_id)
        self.assertIn("overall_status", self.llm_context)
        self.assertIsInstance(self.llm_context.get("high_priority_actions"), list)
        self.assertIsInstance(self.llm_context.get("recommendations"), list)
        
        # Verify that all elements in high_priority_actions are strings
        for action in self.llm_context.get("high_priority_actions"):
            self.assertIsInstance(action, str)
            self.assertTrue(len(action) > 0)

if __name__ == "__main__":
    unittest.main()
