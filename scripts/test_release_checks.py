"""File checks use tiny synthetic fixtures, never real installers or user files."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from check_preparation import ROOT
from release_checks import CONNECTOR_FILES, FIXED_TARGET, validate_assets, validate_connector, validate_listing_facts


class ReleaseFileTests(unittest.TestCase):
    def setUp(self):
        base = Path(tempfile.gettempdir()).resolve()
        self.temp = tempfile.TemporaryDirectory(prefix="yuntu-release-review-", dir=base)
        self.root = Path(self.temp.name).resolve()
        self.assertEqual(self.root.parent, base)
        self.addCleanup(self.temp.cleanup)

    def asset(self, name, data=b"synthetic test bytes, not an application"):
        file = self.root / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(data)
        return {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

    def check_assets(self, assets):
        return validate_assets(self.root, assets, FIXED_TARGET["version"], "microsoft-store-msix")

    def test_exact_archive_hash_passes_but_corrupted_bytes_fail(self):
        item = self.asset("releases/1.0.0-beta/windows-x64/test.msix")
        self.assertEqual(self.check_assets([item]), [])
        self.assertTrue(validate_assets(self.root, [item], FIXED_TARGET["version"], None))
        (self.root / item["path"]).write_bytes(b"changed")
        self.assertTrue(any("checksum mismatch" in error for error in self.check_assets([item])))

    def test_prefix_cannot_hide_parent_traversal_or_windows_separators(self):
        outside = self.asset("releases/outside.msix")
        for bad in ["releases/1.0.0-beta/windows-x64/../../outside.msix", "releases/1.0.0-beta/windows-x64/..\\..\\outside.msix", "releases/1.0.0-beta.3/windows-x64/test.msix"]:
            item = dict(outside, path=bad)
            self.assertTrue(any("outside the fixed version" in error for error in self.check_assets([item])))
        self.assertTrue((self.root / outside["path"]).is_file())

    def test_notes_and_duplicate_case_paths_cannot_stand_in_for_a_package(self):
        note = self.asset("releases/1.0.0-beta/windows-x64/notes.md")
        self.assertTrue(any("MSIX submission package" in error for error in self.check_assets([note])))
        item = self.asset("releases/1.0.0-beta/windows-x64/test.msix")
        duplicate = dict(item, path=item["path"].replace("test.msix", "TEST.MSIX"))
        self.assertTrue(any("Duplicate" in error for error in self.check_assets([item, duplicate])))

    def test_connector_manifest_cannot_omit_the_required_helper(self):
        manifest = {"format": "yuntu-mcp-source-snapshot/1", "sourceCommit": "0" * 40, "files": {}}
        for name in CONNECTOR_FILES:
            item = self.asset("integrations/mcp/" + name, b"test connector fixture\n")
            manifest["files"][name] = {"sha256": item["sha256"], "bytes": item["bytes"]}
        self.assertEqual(validate_connector(self.root, manifest), [])
        missing = copy.deepcopy(manifest)
        del missing["files"]["editor-api.py"]
        self.assertTrue(validate_connector(self.root, missing))
        (self.root / "integrations/mcp/editor-api.py").unlink()
        self.assertTrue(any("Missing" in error for error in validate_connector(self.root, manifest)))

    def test_required_store_fields_cannot_disappear_or_stay_empty(self):
        facts = json.loads((ROOT / "docs/release/store-listing.en.json").read_text(encoding="utf8"))["requiredFacts"]
        self.assertEqual(validate_listing_facts(facts, False), [])
        self.assertTrue(validate_listing_facts({}, False))
        self.assertTrue(validate_listing_facts(facts, True))
        ready = {name: "test-only approved fact" for name in facts}
        self.assertEqual(validate_listing_facts(ready, True), [])
        ready["availableMarkets"] = []
        self.assertTrue(validate_listing_facts(ready, True))


if __name__ == "__main__":
    unittest.main()
