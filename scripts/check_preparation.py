"""Read-only release-material checks. Requires Python 3.11+; never publishes."""
import argparse
import json
import re
import sys
import tomllib
from pathlib import Path
from urllib.parse import unquote, urlsplit
from release_checks import FIXED_TARGET, validate_assets, validate_connector, validate_listing_facts

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_GATES = {
    "editor-acceptance", "frozen-identity-and-artifacts", "store-account-and-product",
    "msix-package-and-channel", "requirements-install-and-upgrade", "domain-and-public-website",
    "support-privacy-and-terms", "skill-mcp-installed-client-pairing", "distribution-rights-and-notices",
    "listing-markets-and-real-assets", "user-overall-review-and-publication-scope",
}


def inside(root, name):
    target = (root / name).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError("Preparation path escapes repository: " + str(name))
    return target


def validate_readiness(record, require_ready=False):
    errors, pending, seen = [], [], set()
    if not isinstance(record, dict):
        return ["Readiness record must be an object"], []
    if record.get("format") != "yuntu-release-readiness/1":
        errors.append("Unsupported readiness format")
    if record.get("primaryChannel") != "microsoft-store-msix":
        errors.append("Missing or unsupported release channel; this preparation uses Microsoft Store MSIX")
    target = record.get("releaseTarget", {})
    if not isinstance(target, dict) or any(target.get(key) != value for key, value in FIXED_TARGET.items()):
        errors.append("Release target must remain 1.0.0-beta / beta / 1.0.0.0 as fixed by the user")
    target = FIXED_TARGET
    if record.get("branch") != "release/" + target["version"]:
        errors.append("Release branch does not match the user-fixed version")
    if isinstance(record.get("finalIdentity"), dict):
        errors.extend(identity_mismatches(record["finalIdentity"], target, "Final build identity"))
    for gate in record.get("gates", []):
        identity = gate.get("id")
        if not isinstance(identity, str) or identity in seen:
            errors.append("Missing or repeated release gate")
        seen.add(identity)
        if gate.get("status") not in {"pending", "ready"}:
            errors.append("Invalid gate status: " + str(identity))
        elif gate["status"] == "pending":
            pending.append(identity)
            if not gate.get("reason"):
                errors.append("Pending gate needs its reason: " + identity)
        elif not isinstance(gate.get("evidence"), str) or not gate["evidence"].strip():
            errors.append("Ready gate needs actual evidence: " + identity)
    if REQUIRED_GATES - seen:
        errors.append("Missing release gates: " + ", ".join(sorted(REQUIRED_GATES - seen)))
    if require_ready:
        if pending:
            errors.append("Release is not ready: pending gates remain")
        identity = record.get("finalIdentity")
        if not isinstance(identity, dict):
            errors.append("Final accepted identity is not recorded")
        else:
            for key in ("version", "channel", "windowsFileVersion", "sourceCommit", "buildId"):
                if not isinstance(identity.get(key), str) or not identity[key].strip():
                    errors.append("Missing final identity field: " + key)
            if not re.fullmatch(r"[0-9a-f]{40}", identity.get("sourceCommit", "")):
                errors.append("Final editor source commit must be a full SHA")
        if not record.get("approvedAssets"):
            errors.append("No final approved artifacts are recorded")
    return errors, pending


def identity_mismatches(identity, target, label):
    return [label + " does not match the user-fixed release " + key
            for key in ("version", "channel", "windowsFileVersion") if identity.get(key) != target.get(key)]


def check(root=ROOT, require_ready=False, editor_identity=None, build_identity=None):
    errors = []
    record = json.loads((root / "docs/release/readiness.json").read_text(encoding="utf8"))
    failures, pending = validate_readiness(record, require_ready)
    errors.extend(failures)
    if editor_identity is not None:
        source = json.loads(Path(editor_identity).read_text(encoding="utf8"))
        errors.extend(identity_mismatches(source, record["releaseTarget"], "Editor release configuration"))
    elif require_ready:
        errors.append("Final release check requires --editor-identity pointing to the actual editor release configuration")
    if build_identity is not None:
        built = json.loads(Path(build_identity).read_text(encoding="utf8"))
        if built.get("format") != "yuntu-editor-build-identity/1" or built.get("product") != "Yuntu Editor" or built.get("profile") != "release":
            errors.append("Actual build identity must describe a release-profile Yuntu Editor executable")
        errors.extend(identity_mismatches(built, FIXED_TARGET, "Actual editor executable"))
    elif require_ready:
        errors.append("Final release check requires --build-identity captured from the actual executable --release-info")
    for name in record["preparedMaterials"]:
        if not inside(root, name).is_file():
            errors.append("Missing preparation material: " + name)
    for path in root.rglob("*.md"):
        relative = path.relative_to(root)
        if any(part in {".git", ".local", "releases", "__pycache__"} for part in relative.parts):
            continue
        data = path.read_bytes()
        if data.startswith(b"\xef\xbb\xbf"):
            errors.append("Unexpected BOM: " + str(relative))
        text = data.decode("utf8")
        for match in re.finditer(r"\[[^\]\n]+\]\(([^)]+)\)", re.sub(r"```.*?```", "", text, flags=re.S)):
            url = urlsplit(match[1])
            if url.scheme or not url.path:
                continue
            target = (path.parent / unquote(url.path)).resolve()
            if not target.is_relative_to(root.resolve()) or not target.exists():
                errors.append("Missing local link in " + str(relative) + ": " + match[1])
    provenance = json.loads((root / "integrations/mcp/source-provenance.json").read_text(encoding="utf8"))
    errors.extend(validate_connector(root, provenance))
    setup = (root / "docs/guides/ai-mcp.md").read_text(encoding="utf8")
    for block in re.findall(r"```toml\n(.*?)\n```", setup, flags=re.S):
        config = tomllib.loads(block)
        server = config["mcp_servers"]["yuntu"]
        if server["args"][0] != "-B" or "--info" not in server["args"]:
            errors.append("MCP configuration does not select a private discovery path")
    listing = json.loads((root / "docs/release/store-listing.en.json").read_text(encoding="utf8"))
    errors.extend(validate_listing_facts(listing.get("requiredFacts"), require_ready))
    if listing["locale"] != "en-US" or listing["status"] not in {"draft-not-for-submission", "approved-for-submission"}:
        errors.append("Unexpected Store copy locale or preparation state")
    # Editorial budgets, not an assertion about every Store submission field.
    if not 1 <= len(listing["shortDescription"]) <= 100:
        errors.append("Short description exceeds the 100-character editorial budget")
    if any(not feature or len(feature) > 200 for feature in listing["features"]):
        errors.append("A feature exceeds the 200-character editorial budget")
    if require_ready:
        if listing["status"] != "approved-for-submission":
            errors.append("Store listing draft has not been approved")
        if record.get("approvedAssets"):
            errors.extend(validate_assets(root, record["approvedAssets"], FIXED_TARGET["version"], record.get("primaryChannel")))
    return errors, pending


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--editor-identity", type=Path, help="Read and compare the actual editor packaging/release.json without changing it")
    parser.add_argument("--build-identity", type=Path, help="Read actual executable --release-info JSON; never execute an installer")
    args = parser.parse_args()
    try:
        errors, pending = check(require_ready=args.require_ready, editor_identity=args.editor_identity, build_identity=args.build_identity)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print("Preparation check failed: " + str(error), file=sys.stderr)
        return 1
    for error in errors:
        print("ERROR: " + error, file=sys.stderr)
    print("Pending release gates (not cleared by document checks): " + str(len(pending)))
    for identity in pending:
        print("  - " + identity)
    if errors:
        return 2 if args.require_ready else 1
    print("Preparation checks passed. No editor build, configuration change, or publication performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
