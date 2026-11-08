"""Readiness checks cannot mistake a valid draft for a release approval."""
import copy
import json
import unittest
from check_preparation import ROOT, validate_readiness


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads((ROOT / "docs/release/readiness.json").read_text(encoding="utf8"))

    def test_pending_preparation_can_be_valid_without_claiming_readiness(self):
        errors, pending = validate_readiness(self.record)
        self.assertEqual(errors, [])
        self.assertIn("domain-and-public-website", pending)
        self.assertTrue(validate_readiness(self.record, require_ready=True)[0])

    def test_removing_an_unfinished_gate_cannot_clear_it(self):
        self.record["gates"] = [g for g in self.record["gates"] if g["id"] != "editor-acceptance"]
        self.assertTrue(any("Missing release gates" in error for error in validate_readiness(self.record)[0]))

    def test_ready_without_evidence_is_invalid(self):
        self.record["gates"][0]["status"] = "ready"
        self.assertTrue(any("actual evidence" in error for error in validate_readiness(self.record)[0]))

    def test_gate_approvals_do_not_replace_final_identity_or_artifacts(self):
        candidate = copy.deepcopy(self.record)
        for gate in candidate["gates"]:
            gate.update(status="ready", evidence="test-only-evidence")
        errors, pending = validate_readiness(candidate, require_ready=True)
        self.assertEqual(pending, [])
        self.assertIn("Final accepted identity is not recorded", errors)
        self.assertIn("No final approved artifacts are recorded", errors)


if __name__ == "__main__":
    unittest.main()
