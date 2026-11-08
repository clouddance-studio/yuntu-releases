"""Release data and file invariants; never executes a package or contacts a service."""
import hashlib
import re
from pathlib import Path, PurePosixPath

FIXED_TARGET = {"version": "1.0.0-beta", "channel": "beta", "windowsFileVersion": "1.0.0.0"}
CONNECTOR_FILES = {"editor-api.py", "editor-mcp.py", "test-editor-mcp.py"}
LISTING_FACTS = {
    "reservedProductName", "storeProductId", "publisherDisplayName", "packageIdentity",
    "confirmedWindowsRequirements", "availableMarkets", "pricing", "publicStoreUrl",
    "publicWebsiteUrl", "supportContact", "privacyPolicyUrl", "licenseTerms",
}


def sha256_file(file):
    digest = hashlib.sha256()
    with file.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_connector(root, provenance):
    errors = []
    files = provenance.get("files")
    if not isinstance(files, dict) or set(files) != CONNECTOR_FILES:
        return ["Connector manifest must name exactly both runtime scripts and their protocol test"]
    if provenance.get("format") != "yuntu-mcp-source-snapshot/1" or not re.fullmatch(r"[0-9a-f]{40}", provenance.get("sourceCommit", "")):
        errors.append("Invalid connector source identity")
    directory = root.resolve() / "integrations/mcp"
    for name, identity in files.items():
        file = (directory / name).resolve()
        if not file.is_relative_to(directory) or not file.is_file():
            errors.append("Missing or escaped connector file: " + name)
            continue
        if not isinstance(identity, dict) or type(identity.get("bytes")) is not int or identity["bytes"] <= 0 or not re.fullmatch(r"[0-9a-f]{64}", identity.get("sha256", "")):
            errors.append("Invalid connector file identity: " + name)
        elif file.stat().st_size != identity["bytes"] or sha256_file(file) != identity["sha256"]:
            errors.append("Connector snapshot changed without provenance: " + name)
    return errors


def validate_listing_facts(facts, require_ready):
    if not isinstance(facts, dict) or set(facts) != LISTING_FACTS:
        return ["Store listing must retain every required fact field"]
    if require_ready and any(value is None or value == "" or value == [] or value == {} for value in facts.values()):
        return ["Final listing facts are incomplete"]
    return []


def validate_assets(root, assets, version, primary_channel):
    if primary_channel != "microsoft-store-msix":
        return ["Missing or unsupported final artifact distribution channel"]
    if not isinstance(assets, list) or not assets:
        return ["No final approved artifacts are recorded"]
    prefix = f"releases/{version}/windows-x64/"
    archive = root.resolve() / prefix
    errors, seen, packages = [], set(), 0
    for asset in assets:
        if not isinstance(asset, dict) or not isinstance(asset.get("path"), str):
            errors.append("Invalid final artifact entry")
            continue
        name = asset["path"]
        portable = PurePosixPath(name)
        if not name.startswith(prefix) or "\\" in name or ":" in name or ".." in portable.parts or portable.as_posix() != name:
            errors.append("Final artifact is outside the fixed version archive: " + name)
            continue
        key = name.casefold()
        if key in seen:
            errors.append("Duplicate final artifact: " + name)
            continue
        seen.add(key)
        file = (root / name).resolve()
        if not file.is_relative_to(archive) or not file.is_file():
            errors.append("Final artifact missing or escaped archive: " + name)
            continue
        if type(asset.get("bytes")) is not int or asset["bytes"] <= 0 or not isinstance(asset.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", asset["sha256"]):
            errors.append("Invalid final artifact identity: " + name)
            continue
        if file.stat().st_size != asset["bytes"] or sha256_file(file) != asset["sha256"]:
            errors.append("Final artifact checksum mismatch: " + name)
        elif file.suffix.lower() in {".msix", ".msixbundle", ".msixupload"}:
            packages += 1
    if primary_channel == "microsoft-store-msix" and not packages:
        errors.append("No verified-byte MSIX submission package is recorded; notes or EXE files cannot replace it")
    return errors
