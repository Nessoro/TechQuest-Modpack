"""Validate submitted, reviewable runtime evidence; never fabricate acceptance."""
import json
from pathlib import Path
from scripts.smoke_dragonrise_server import expected_recipes, recipe_fingerprint, validate_report

CHECKS = {
    "client_with_dragonrise", "workstation_and_jei", "survival_each_tier",
    "vehicle_deployment", "ammunition_and_repair", "generator_fuel_and_retrieval",
    "multiplayer_synchronization", "existing_world", "optional_absence",
    "client_server_packaging", "windows_installer_update",
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def evidence_ref(row):
    return (isinstance(row, dict) and row.get("result") == "pass"
            and isinstance(row.get("evidence"), str) and bool(row["evidence"].strip()))


def validate_acceptance(directory, expected, fingerprint):
    """All evidence must refer to the exact recipe bundle and be reviewed in PR."""
    if not directory.is_dir():
        return {"server_decode_verified": False, "runtime_verified": False,
                "obtainable_coverage_percent": None, "acceptance_blockers": ["No runtime evidence submitted"]}
    blockers = []
    server_ok = False
    try:
        if (directory / "recipe-fingerprint.txt").read_text().strip() != fingerprint:
            raise ValueError("Server recipe fingerprint mismatch")
        if read(directory / "expected.json") != expected:
            raise ValueError("Server expected recipe list mismatch")
        reports = {}
        for phase, present in (("absent", False), ("present_existing_world", True), ("present_restart", True)):
            reports[phase] = read(directory / (phase + ".json"))
            validate_report(reports[phase], present, expected)
        original = set(reports["absent"]["original_sbw_recipe_ids"])
        for phase in ("present_existing_world", "present_restart"):
            if not original <= set(reports[phase]["original_sbw_recipe_ids"]):
                raise ValueError("Original SBW recipe IDs disappeared")
        server_ok = True
    except (OSError, ValueError, KeyError, TypeError) as exc:
        blockers.append("Server decoding: " + str(exc))
    proven = set()
    try:
        manual = read(directory / "manual-acceptance.json")
        if manual["recipe_fingerprint"] != fingerprint:
            raise ValueError("Manual evidence is stale")
        if not evidence_ref(manual["review"]):
            raise ValueError("Missing review evidence")
        if set(manual["checks"]) != CHECKS or not all(evidence_ref(v) for v in manual["checks"].values()):
            raise ValueError("Manual runtime checklist incomplete")
        rows = manual["obtainability"]
        if set(rows) != set(expected):
            raise ValueError("Obtainability entries do not match recipe inventory")
        proven = {rid for rid, row in rows.items() if evidence_ref(row)}
        if proven != set(expected):
            blockers.append("Some recipes have no positive obtainability evidence")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        blockers.append("Manual acceptance: " + str(exc))
    complete = server_ok and not blockers and proven == set(expected)
    return {"server_decode_verified": server_ok, "runtime_verified": complete,
            "obtainable_coverage_percent": 100.0 * len(proven) / len(expected) if server_ok and proven else None,
            "acceptance_blockers": blockers}


def current_acceptance(directory):
    return validate_acceptance(Path(directory), expected_recipes(), recipe_fingerprint())
