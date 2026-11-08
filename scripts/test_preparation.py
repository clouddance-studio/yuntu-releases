"""Readiness checks cannot mistake a valid draft for a release approval."""
import copy
import json
import unittest
from check_preparation import ROOT, validate_readiness, identity_mismatches


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

    def test_removing_the_channel_cannot_disable_msix_package_checks(self):
        del self.record["primaryChannel"]
        self.assertTrue(any("unsupported release channel" in error for error in validate_readiness(self.record)[0]))

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

    def test_beta_three_cannot_be_used_as_the_fixed_first_beta(self):
        self.record["finalIdentity"] = {"version": "1.0.0-beta.3", "channel": "beta", "windowsFileVersion": "1.0.0.3"}
        errors, _ = validate_readiness(self.record)
        self.assertTrue(any("user-fixed release version" in error for error in errors))
        self.assertTrue(any("user-fixed release windowsFileVersion" in error for error in errors))

    def test_newer_beta_executable_also_cannot_replace_the_fixed_release(self):
        observed_build = {"version": "1.0.1-beta", "channel": "beta", "windowsFileVersion": "1.0.1.0"}
        errors = identity_mismatches(observed_build, self.record["releaseTarget"], "Actual editor executable")
        self.assertEqual(len(errors), 2)

    def test_branch_and_editor_identity_must_match_the_fixed_target(self):
        self.record["branch"] = "release/1.0.0-beta.3"
        self.assertTrue(any("branch does not match" in error for error in validate_readiness(self.record)[0]))
        target = self.record["releaseTarget"]
        self.assertEqual(identity_mismatches(dict(target), target, "Editor"), [])
        wrong = dict(target, version="1.0.0")
        self.assertTrue(identity_mismatches(wrong, target, "Editor"))

    def test_retargeting_the_record_and_branch_together_still_cannot_change_the_user_version(self):
        self.record["releaseTarget"].update(version="1.0.0-beta.3", windowsFileVersion="1.0.0.3")
        self.record["branch"] = "release/1.0.0-beta.3"
        errors, _ = validate_readiness(self.record)
        self.assertTrue(any("must remain 1.0.0-beta" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
