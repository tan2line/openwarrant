"""Behavioral tests for failure gates, run provenance, and independent review."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import evalkit as e


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.pack = e.read(e.ROOT/"data/cases.json")
        self.rubric = e.read(e.ROOT/"data/rubric.json")
        self.reference = e.read(e.ROOT/"data/reference.outputs.json")

    def run_reference(self):
        return e.run(self.pack, self.rubric, self.reference)

    def reviews(self, receipt):
        return [{"receipt_sha256": receipt["receipt_sha256"], "reviewer_id": who,
                 "reviews": [{"case_id": r["case_id"], "verdict": "pass",
                              "rationale": "TEST FIXTURE: structured scope and sources inspected."}
                             for r in receipt["results"]]} for who in ("test-a", "test-b")]

    def test_reference_never_authorizes(self):
        r = self.run_reference()
        self.assertEqual(r["summary"]["automated_passes"], 25)
        self.assertEqual(r["authorization"]["status"], "NOT_ISSUED")
        self.assertEqual(r["human_review"]["status"], "PENDING")

    def test_improving_average_does_not_hide_regressions(self):
        a = e.run(self.pack, self.rubric, e.read(e.ROOT/"data/baseline.outputs.json"))
        b = e.run(self.pack, self.rubric, e.read(e.ROOT/"data/candidate.outputs.json"))
        self.assertEqual(a["summary"]["automated_passes"], 20)
        self.assertEqual(b["summary"]["automated_passes"], 21)
        changes = e.compare(a, b)
        self.assertEqual(changes["regression_cases"], 2)
        self.assertEqual(changes["improvement_cases"], 3)
        self.assertEqual(b["summary"]["automated_gate"], "BLOCKED")

    def test_missing_output_fails_not_dropped(self):
        self.reference["outputs"].pop()
        r = self.run_reference()
        self.assertEqual(r["summary"]["cases"], 25)
        self.assertEqual(r["summary"]["failed_cases"], 1)

    def test_duplicate_and_unknown_output_rejected(self):
        for mode in ("duplicate", "unknown"):
            s = copy.deepcopy(self.reference)
            extra = copy.deepcopy(s["outputs"][0])
            if mode == "unknown":
                extra["case_id"] = "unknown"
            s["outputs"].append(extra)
            with self.assertRaises(ValueError):
                e.run(self.pack, self.rubric, s)

    def test_bad_structures_are_scored_as_failures(self):
        for key, val in (("facts", "bad"), ("flags", [{}]), ("summary", None),
                         ("facts", ["bad"]), ("actions", [None])):
            s = copy.deepcopy(self.reference)
            s["outputs"][0][key] = val
            r = e.run(self.pack, self.rubric, s)
            self.assertFalse(r["results"][0]["automated_pass"])

    def test_semantic_limit_is_explicit(self):
        # Structured checks cannot establish the truth of arbitrary prose.
        self.reference["outputs"][0]["summary"] = "An unsupported assertion in fluent prose."
        r = self.run_reference()
        self.assertTrue(r["results"][0]["automated_pass"])
        self.assertEqual(r["human_review"]["status"], "PENDING")

    def test_policy_change_prevents_misleading_comparison(self):
        a = self.run_reference()
        self.pack["version"] = "0.2.0"
        b = self.run_reference()
        with self.assertRaisesRegex(ValueError, "Incomparable"):
            e.compare(a, b)

    def test_tampered_receipt_rejected(self):
        r = self.run_reference()
        r["summary"]["automated_passes"] = 0
        with self.assertRaisesRegex(ValueError, "digest"):
            e.verify_receipt(r)

    def test_holdout_coverage(self):
        r = e.run(self.pack, self.rubric, self.reference, "holdout")
        self.assertEqual(r["summary"]["cases"], 10)
        self.assertTrue(all(x["split"] == "holdout" for x in r["results"]))

    def test_two_passing_reviews_still_do_not_authorize(self):
        r = self.run_reference()
        result = e.reconcile(r, self.reviews(r))
        self.assertEqual(result["status"], "READY_FOR_ACCOUNTABLE_REVIEW")
        self.assertEqual(result["authorization_status"], "NOT_ISSUED")

    def test_disagreement_requires_adjudication(self):
        r = self.run_reference()
        reviews = self.reviews(r)
        reviews[1]["reviews"][0]["verdict"] = "fail"
        result = e.reconcile(r, reviews)
        self.assertEqual(result["status"], "PENDING_ADJUDICATION")
        adj = {"receipt_sha256": r["receipt_sha256"], "adjudicator_id": "test-c",
               "decisions": [{"case_id": "C01", "verdict": "fail", "rationale": "TEST: consequential omission."}]}
        result = e.reconcile(r, reviews, adj)
        self.assertEqual(result["status"], "BLOCKED")

    def test_agreed_uncertainty_is_not_pass(self):
        r = self.run_reference()
        reviews = self.reviews(r)
        for review in reviews:
            review["reviews"][0]["verdict"] = "uncertain"
        result = e.reconcile(r, reviews)
        self.assertEqual(result["raw_agreement"], 1)
        self.assertEqual(result["unresolved_cases"], ["C01"])

    def test_duplicate_reviewer_incomplete_or_wrong_run_rejected(self):
        r = self.run_reference()
        for mode in ("duplicate", "missing", "wrong-run", "no-rationale"):
            reviews = self.reviews(r)
            if mode == "duplicate": reviews[1]["reviewer_id"] = "test-a"
            if mode == "missing": reviews[1]["reviews"].pop()
            if mode == "wrong-run": reviews[1]["receipt_sha256"] = "bad"
            if mode == "no-rationale": reviews[1]["reviews"][0]["rationale"] = " "
            with self.assertRaises(ValueError): e.reconcile(r, reviews)

    def test_human_pass_does_not_override_automated_failure(self):
        r = e.run(self.pack, self.rubric, e.read(e.ROOT/"data/baseline.outputs.json"))
        result = e.reconcile(r, self.reviews(r))
        self.assertEqual(result["status"], "BLOCKED")

    def test_export_inputs_excludes_reference_answers(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/"inputs.json"
            self.assertEqual(e.main(["inputs", "--out", str(path)]), 0)
            result = e.read(path)
            self.assertEqual(len(result["cases"]), 15)
            self.assertTrue(all(set(c) == {"id", "task", "sources"} for c in result["cases"]))

    def test_html_embedded_data_cannot_break_script(self):
        r = self.run_reference()
        r["results"][0]["output"]["summary"] = "</script><script>alert(1)</script>"
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"review.html"
            e.render(r, self.pack, p)
            self.assertNotIn("</script><script>alert(1)", p.read_text())


if __name__ == "__main__":
    unittest.main()
