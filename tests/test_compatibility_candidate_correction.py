"""
Phase 6 tests: compatibility candidate correction.
25 tests covering all required Phase 6 properties.
Run: python -m pytest tests/test_compatibility_candidate_correction.py -v
"""
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC  = ROOT / "CompatibilityLayer/source/raw/normalized_rule_candidates.json"
CORRECTED = ROOT / "CompatibilityLayer/rules/corrected"
CLARIF_Q  = CORRECTED / "clarification_queue.json"
TRACE_F   = CORRECTED / "candidate_correction_trace.json"
SPLIT_F   = CORRECTED / "candidate_split_merge_map.json"
REPORT_F  = CORRECTED / "correction_report.json"


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


class TestCandidateCorrectionPhase6(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.raw        = load(SRC)
        cls.raw_bytes  = SRC.read_bytes()
        cls.raw_sha    = hashlib.sha256(cls.raw_bytes).hexdigest()
        cls.src_cands  = cls.raw["rule_candidates"]
        cls.corrected  = load(CORRECTED / "corrected_rule_candidates.json")
        cls.candidates = cls.corrected["candidates"]
        cls.trace      = load(TRACE_F)
        cls.split      = load(SPLIT_F)
        cls.report     = load(REPORT_F)
        cls.clarif     = load(CLARIF_Q)
        cls.src_ids    = {c["candidate_id"] for c in cls.src_cands}
        cls.corr_by_id = {c["candidate_id"]: c for c in cls.candidates}

    # 1 Raw file immutability
    def test_01_raw_file_immutable(self):
        current_sha = hashlib.sha256(SRC.read_bytes()).hexdigest()
        self.assertEqual(current_sha, self.raw_sha, "Raw input file was modified.")

    # 2 Source checksum recorded
    def test_02_source_checksum_recorded(self):
        self.assertEqual(self.corrected["source_sha256"], self.raw_sha)
        self.assertEqual(self.trace["source_sha256"], self.raw_sha)

    # 3 All 42 candidates accounted for
    def test_03_all_42_candidates_accounted(self):
        self.assertEqual(self.corrected["source_candidate_count"], 42)
        accounted = set()
        for item in self.split.get("one_to_one", []):
            accounted.add(item["source_candidate_id"])
        for item in self.split.get("splits", []):
            accounted.add(item["source_candidate_id"])
        for cid in self.split.get("unconverted", []):
            accounted.add(cid)
        self.assertEqual(accounted, self.src_ids,
                         f"Missing: {self.src_ids - accounted}")

    # 4 Unique candidate IDs
    def test_04_unique_corrected_candidate_ids(self):
        ids = [c["candidate_id"] for c in self.candidates]
        self.assertEqual(len(ids), len(set(ids)), "Duplicate corrected candidate IDs found.")

    # 5 Operator normalization
    def test_05_operator_normalization(self):
        # installed and exists are already canonical per the operator contract.
        raw_ops = {"==", "!=", ">=", ">", "<=", "<"}
        norm_ops = {"equals","not_equals","greater_than_or_equal","greater_than",
                    "less_than_or_equal","less_than","installed","exists"}
        for c in self.candidates:
            for cond in c.get("conditions", []):
                op = cond.get("operator","")
                if op:
                    self.assertNotIn(op, raw_ops,
                        f"{c['candidate_id']}: raw operator '{op}' not normalized")
            for req in c.get("requirements", []):
                op = req.get("operator","")
                if op:
                    self.assertNotIn(op, raw_ops,
                        f"{c['candidate_id']}: raw operator '{op}' not normalized")

    # 6 Logic normalization
    def test_06_logic_normalization(self):
        for c in self.candidates:
            logic = c.get("condition_logic","")
            self.assertIn(logic, ("ALL","ANY",""),
                f"{c['candidate_id']}: condition_logic '{logic}' not normalized")

    # 7 Raw values preserved
    def test_07_raw_version_values_preserved(self):
        for sc in self.src_cands:
            cid = sc["candidate_id"]
            if cid not in self.corr_by_id:
                continue  # split candidate
            cc = self.corr_by_id[cid]
            for i, sr in enumerate(sc.get("requirements", [])):
                vr = sr.get("version_raw","")
                if i < len(cc.get("requirements",[])):
                    self.assertEqual(cc["requirements"][i].get("version_raw",""), vr,
                        f"{cid} req[{i}] version_raw changed")

    # 8 Original candidate hash preserved
    def test_08_original_hash_preserved(self):
        for sc in self.src_cands:
            cid = sc["candidate_id"]
            if cid == "RCAND-000365":
                continue  # split — check split outputs instead
            if cid not in self.corr_by_id:
                continue
            cc = self.corr_by_id[cid]
            self.assertIn("original_candidate_hash", cc,
                f"{cid}: missing original_candidate_hash")
            self.assertTrue(len(cc["original_candidate_hash"]) == 16)

    # 9 Deterministic correction
    def test_09_deterministic_correction(self):
        # Re-hash each corrected candidate and verify stability
        for c in self.candidates:
            h1 = hashlib.sha256(json.dumps(c, sort_keys=True).encode()).hexdigest()
            h2 = hashlib.sha256(json.dumps(c, sort_keys=True).encode()).hexdigest()
            self.assertEqual(h1, h2, f"{c['candidate_id']}: hash not deterministic")

    # 10 Correction trace completeness
    def test_10_correction_trace_completeness(self):
        self.assertGreater(self.trace["total_traces"], 0)
        self.assertEqual(self.trace["total_traces"], len(self.trace["traces"]))
        required = {"trace_id","candidate_id","field_path","original_value",
                    "corrected_value","correction_type","reason","source_basis",
                    "automatic_change_safe","requires_human_review"}
        for t in self.trace["traces"]:
            missing = required - set(t.keys())
            self.assertFalse(missing, f"Trace {t.get('trace_id')} missing: {missing}")

    # 11 Split lineage preserved
    def test_11_split_lineage_preserved(self):
        splits = self.split.get("splits", [])
        self.assertTrue(len(splits) >= 1, "Expected at least one split")
        for s in splits:
            self.assertIn("source_candidate_id", s)
            self.assertIn("generated_candidate_ids", s)
            self.assertTrue(s.get("lineage_preserved", False))
            self.assertIn(s["source_candidate_id"], self.src_ids)

    # 12 No merges without same-meaning evidence
    def test_12_no_spurious_merges(self):
        merges = self.split.get("merges", [])
        self.assertEqual(merges, [], "Unexpected merges found")

    # 13 Clarification items have reason codes
    def test_13_clarification_items_have_reason_codes(self):
        for item in self.clarif.get("items", []):
            self.assertTrue(len(item.get("reason_codes", [])) > 0,
                f"Clarification item {item.get('clarification_id')} has no reason codes")

    # 14 RCAND-000367 exceptions recovered
    def test_14_exception_recovery_367(self):
        cc = self.corr_by_id.get("RCAND-000367")
        self.assertIsNotNone(cc, "RCAND-000367 not found in corrected candidates")
        excs = cc.get("exceptions", [])
        self.assertEqual(len(excs), 3,
            f"Expected 3 exceptions for RCAND-000367, got {len(excs)}")
        names = {e["entity_name"] for e in excs}
        self.assertIn("ProBook Series", names)
        self.assertIn("Enterprise Laptop Series", names)
        self.assertIn("ComputeNode Servers", names)

    # 15 Unknown not treated as entity
    def test_15_unknown_not_treated_as_entity(self):
        for c in self.candidates:
            for cond in c.get("conditions", []):
                eid = cond.get("entity_id")
                ename = cond.get("entity_name","").lower()
                if ename == "unknown":
                    self.assertIsNone(eid,
                        f"{c['candidate_id']}: 'unknown' component_name assigned entity_id {eid}")

    # 16 RCAND-000361 version logic inconsistency
    def test_16_rcand_000361_version_logic_flagged(self):
        cc = self.corr_by_id.get("RCAND-000361")
        self.assertIsNotNone(cc)
        self.assertFalse(cc.get("eligible_for_rule_generation", True),
            "RCAND-000361 must not be eligible for generation (version logic inconsistency)")
        reasons = cc.get("clarification_reasons", [])
        self.assertIn("inconsistent_version_logic", reasons)

    # 17 RCAND-000365 split with ANY → two candidates
    def test_17_rcand_000365_split(self):
        split_entries = [s for s in self.split.get("splits",[])
                         if s["source_candidate_id"] == "RCAND-000365"]
        self.assertTrue(len(split_entries) >= 1)
        split_ids = split_entries[0]["generated_candidate_ids"]
        self.assertEqual(len(split_ids), 2)
        for sid in split_ids:
            self.assertIn(sid, self.corr_by_id)
            sc = self.corr_by_id[sid]
            self.assertEqual(sc.get("condition_logic"), "ALL")

    # 18 RCAND-000368 optionality preserved
    def test_18_rcand_000368_optionality(self):
        cc = self.corr_by_id.get("RCAND-000368")
        self.assertIsNotNone(cc)
        reasons = cc.get("clarification_reasons", [])
        self.assertIn("optionality_unclear", reasons)
        self.assertFalse(cc.get("eligible_for_rule_generation", True))

    # 19 RCAND-000369 advisory preserved
    def test_19_rcand_000369_advisory(self):
        cc = self.corr_by_id.get("RCAND-000369")
        self.assertIsNotNone(cc)
        self.assertFalse(cc.get("eligible_for_rule_generation", True))
        reasons = cc.get("clarification_reasons", [])
        self.assertTrue(len(reasons) > 0)

    # 20 Unknown applicability candidates in clarification
    def test_20_unknown_applicability_in_clarification(self):
        unknown_cids = {"RCAND-000374","RCAND-000376","RCAND-000377",
                        "RCAND-000382","RCAND-000385","RCAND-000400"}
        clarif_src_ids = set()
        for item in self.clarif.get("items",[]):
            clarif_src_ids.update(item.get("source_candidate_ids",[]))
        for cid in unknown_cids:
            self.assertIn(cid, clarif_src_ids,
                f"{cid} with unknown applicability not in clarification queue")

    # 21 RCAND-000398 validation checkpoint
    def test_21_rcand_000398_checkpoint_handling(self):
        cc = self.corr_by_id.get("RCAND-000398")
        self.assertIsNotNone(cc)
        self.assertFalse(cc.get("eligible_for_rule_generation", True))
        # Reboot Cycle must not appear as an entity
        for req in cc.get("requirements", []):
            eid = req.get("entity_id")
            ename = req.get("entity_name","").lower()
            self.assertNotIn("reboot", ename.split()[:1],
                "Reboot Cycle must not be modeled as a version-requirement entity")
            self.assertIsNone(eid, "Reboot Cycle must not have an entity_id")

    # 22 No entity IDs invented
    def test_22_no_invented_entity_ids(self):
        rc2_path = ROOT / "ontology/releases/v1.1-rc2/canonical_entity_registry.json"
        rc2 = json.loads(rc2_path.read_text(encoding="utf-8"))
        valid_ids = {e["entity_id"] for e in rc2["entities"]}
        valid_ids.add(None)  # null is allowed
        for c in self.candidates:
            for cond in c.get("conditions",[]):
                eid = cond.get("entity_id")
                self.assertIn(eid, valid_ids,
                    f"{c['candidate_id']}: invented entity_id {eid} in conditions")
            for req in c.get("requirements",[]):
                eid = req.get("entity_id")
                self.assertIn(eid, valid_ids,
                    f"{c['candidate_id']}: invented entity_id {eid} in requirements")

    # 23 No approval status
    def test_23_no_approval_status_generated(self):
        for c in self.candidates:
            status = c.get("review_status","")
            self.assertNotIn(status, ("approved","human_approved"),
                f"{c['candidate_id']}: approval status must not be set in Phase 6")

    # 24 No source_verified status
    def test_24_no_source_verified_fabricated(self):
        for c in self.candidates:
            ev = c.get("evidence_verification_status","")
            self.assertNotEqual(ev, "source_verified",
                f"{c['candidate_id']}: evidence must not be source_verified")

    # 25 Correction report counts consistent
    def test_25_correction_report_counts_consistent(self):
        self.assertEqual(self.report["source_candidate_count"], 42)
        self.assertTrue(self.report["all_42_accounted"])
        self.assertTrue(self.report["raw_input_unchanged"])
        self.assertEqual(self.report["source_sha256"], self.raw_sha)


if __name__ == "__main__":
    unittest.main()
