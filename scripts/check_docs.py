#!/usr/bin/env python3
"""Check design artifacts; this never runs or grades the proposed application."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


def load_json(path: Path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError(f"non-JSON numeric constant: {value}")

    return json.loads(path.read_text(), object_pairs_hook=pairs, parse_constant=reject_constant)


def check(root: Path) -> tuple[list[str], dict]:
    errors = []
    stats = {}
    required = [
        "README.md", "AGENTS.md", "docs/REQUIREMENTS.md", "docs/GOVERNANCE.md",
        "docs/SCENARIOS.md", "docs/ARCHITECTURE.md", "docs/DATA_MODEL.md",
        "docs/RUNTIME.md", "docs/API.md", "docs/DEVELOPMENT.md",
        "docs/THREAT_MODEL.md", "docs/DECISIONS.md", "docs/ROADMAP.md",
        "docs/VERIFICATION.md", "docs/REVIEW.md", "docs/REVIEW_GUIDE.md",
        "docs/COSTS.md", "docs/SOURCES.md", "contracts/openapi.json",
        "contracts/examples.json", "evals/scenarios.json", "pricing/rates.json",
        "pricing/scenarios.json", "requirements-docs.txt", "requirements-docs.lock",
    ]
    for name in required:
        if not (root / name).is_file():
            errors.append(f"missing required artifact: {name}")
    if errors:
        return errors, stats

    markdown = [root / "README.md", root / "AGENTS.md", *sorted((root / "docs").glob("*.md"))]
    link_count = 0
    secret = re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|AKIA[A-Z0-9]{16}|sk-[A-Za-z0-9]{32,})")
    all_text = ""
    for path in markdown:
        content = path.read_text()
        all_text += "\n" + content
        relative = path.relative_to(root)
        if not content.endswith("\n"):
            errors.append(f"{relative}: missing final newline")
        fences = re.findall(r"(?m)^\s*```", content)
        if len(fences) % 2:
            errors.append(f"{relative}: unbalanced code fences")
        if secret.search(content):
            errors.append(f"{relative}: possible credential; manual inspection required")
        if "/Users/" in content or "金石易服" in content:
            errors.append(f"{relative}: local/private-context marker in public artifact")
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", content):
            target = target.strip().strip("<>").split(' "', 1)[0]
            parsed = urlsplit(target)
            if parsed.scheme in ("http", "https", "mailto") or not parsed.path:
                continue
            link_count += 1
            if parsed.scheme or parsed.path.startswith("/"):
                errors.append(f"{relative}: nonportable local link {target}")
                continue
            resolved = (path.parent / unquote(parsed.path)).resolve()
            if not resolved.is_relative_to(root) or not resolved.is_file():
                errors.append(f"{relative}: broken/out-of-root link {target}")
    stats.update(markdown_files=len(markdown), local_file_links=link_count)

    req_text = (root / "docs/REQUIREMENTS.md").read_text()
    req_ids = re.findall(r"(?m)^#{2,4}\s+(REQ-\d{3})\b", req_text)
    policy_text = (root / "docs/GOVERNANCE.md").read_text()
    policy_ids = re.findall(r"(?m)^#{2,4}\s+(POL-\d{3})\b", policy_text)
    expected_req = {f"REQ-{i:03d}" for i in range(1, 15)}
    expected_policy = {f"POL-{i:03d}" for i in range(1, 11)}
    if set(req_ids) != expected_req or len(req_ids) != len(expected_req):
        errors.append("requirements: expected exactly one definition for REQ-001..014")
    if set(policy_ids) != expected_policy or len(policy_ids) != len(expected_policy):
        errors.append("governance: expected exactly one definition for POL-001..010")
    unknown_req = set(re.findall(r"REQ-\d{3}", all_text)) - expected_req
    unknown_policy = set(re.findall(r"POL-\d{3}", all_text)) - expected_policy
    if unknown_req or unknown_policy:
        errors.append(f"undefined references: {sorted(unknown_req | unknown_policy)}")

    try:
        spec = load_json(root / "contracts/openapi.json")
        examples = load_json(root / "contracts/examples.json")
        suite = load_json(root / "evals/scenarios.json")
        load_json(root / "pricing/rates.json")
        load_json(root / "pricing/scenarios.json")
    except (ValueError, OSError) as exc:
        errors.append(f"JSON: {exc}")
        return errors, stats

    def pointer(value):
        current = spec
        for segment in value[2:].split("/"):
            current = current[segment.replace("~1", "/").replace("~0", "~")]
        return current

    def walk(value):
        if isinstance(value, dict):
            if "$ref" in value:
                reference = value["$ref"]
                if not reference.startswith("#/"):
                    errors.append(f"external schema reference is not offline-verifiable: {reference}")
                else:
                    try:
                        pointer(reference)
                    except (KeyError, TypeError):
                        errors.append(f"unresolved schema reference: {reference}")
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(spec)
    operations = []
    actual_routes = set()
    route_requirements = {}
    api_req = set()
    conditional_operations = {
        "updateWorkItem", "transitionWorkItem", "commandRun", "proposeSourceCorrection",
        "revokeSourceAccess", "respondSupportRequest", "fulfilSupportRequest",
        "revokeAuthorization", "executeAction", "reconcileAction", "withdrawRelease",
        "addParticipant", "removeParticipant", "requestOwnershipTransfer",
        "respondOwnershipTransfer", "resolveCorrection", "updateCapabilityOffer",
        "withdrawCapabilityOffer", "verifyOutcome", "reviseOutcome", "resolveFeedback",
        "reviseExperience", "confirmExperience", "reviseSkill", "confirmSkill",
        "resolveUsageRestriction", "confirmResourceLead", "supplementSupportRequest",
        "reviewEvaluation",
    }
    # These are design invariants derived from identity and concurrency requirements,
    # not optional annotations that a changed operation may disable itself.
    session_scheme = spec.get("components", {}).get("securitySchemes", {}).get("sessionCookie", {})
    if session_scheme != {"type": "apiKey", "in": "cookie", "name": "orgloop_session"}:
        errors.append("session cookie security scheme changed or missing")
    if_match = spec.get("components", {}).get("parameters", {}).get("IfMatch", {})
    if if_match.get("required") is not True or if_match.get("in") != "header" or if_match.get("name") != "If-Match":
        errors.append("If-Match must remain a required header precondition")
    for path, methods in spec.get("paths", {}).items():
        for method, operation in methods.items():
            if method not in {"get", "post", "patch", "put", "delete", "options", "head"}:
                continue
            operations.append(operation["operationId"])
            actual_routes.add((method.upper(), path))
            links = operation.get("x-requirements", [])
            route_requirements[(method.upper(), path)] = set(links)
            if not links or set(links) - expected_req:
                errors.append(f"{method} {path}: missing/unknown requirement mapping")
            api_req.update(links)
            params = {p.get("$ref", "") for p in operation.get("parameters", [])}
            expected_mutating = method not in {"get", "head", "options"} and operation["operationId"] not in {"searchContext", "searchResources"}
            if operation.get("x-mutating") != expected_mutating:
                errors.append(f"{method} {path}: incorrect mutating classification")
            if expected_mutating:
                for parameter in ("IdempotencyKey", "CsrfToken"):
                    if f"#/components/parameters/{parameter}" not in params:
                        errors.append(f"{method} {path}: missing {parameter}")
            security = operation.get("security", spec.get("security"))
            if operation["operationId"] in {"startLogin", "finishLogin"}:
                if security != []:
                    errors.append(f"{method} {path}: login must not require an existing session")
            elif not security or any(item != {"sessionCookie": []} for item in security):
                errors.append(f"{method} {path}: missing or bypassable effective session authentication")
            if operation["operationId"] in conditional_operations or method in {"patch", "put", "delete"}:
                if "#/components/parameters/IfMatch" not in params:
                    errors.append(f"{method} {path}: missing required optimistic concurrency precondition")
    if len(set(operations)) != len(operations):
        errors.append("OpenAPI: duplicate operationId")
    documented_routes = set(re.findall(r"\| `(GET|POST|PATCH|PUT|DELETE|HEAD|OPTIONS)` \| `([^`]+)` \|", (root / "docs/API.md").read_text()))
    if actual_routes != documented_routes:
        errors.append(f"API directory drift: undocumented={sorted(actual_routes-documented_routes)} stale={sorted(documented_routes-actual_routes)}")
    mapping_rows = re.findall(r"\| `(GET|POST|PATCH|PUT|DELETE|HEAD|OPTIONS)` \| `([^`]+)` \| [^|]* \| ([^|\n]*)\|", (root / "docs/API.md").read_text())
    if len(mapping_rows) != len(actual_routes):
        errors.append("API directory contains duplicate rows or missing per-route mappings")
    for method, path, mapped in mapping_rows:
        if route_requirements.get((method, path)) != set(re.findall(r"REQ-\d{3}", mapped)):
            errors.append(f"{method} {path}: per-route requirement mapping differs between API document and contract")
    if api_req != expected_req:
        # Frontend separation is partly architectural, but the contract must map it.
        errors.append(f"API requirement coverage missing: {sorted(expected_req-api_req)}")

    case_ids = []
    case_req = set()
    for case in suite.get("cases", []):
        case_ids.append(case.get("id"))
        case_req.update(case.get("requirements", []))
        for key in ("title", "given", "expected_behavior", "boundaries", "evidence_needed"):
            if not isinstance(case.get(key), str) or not case[key].strip():
                errors.append(f"{case.get('id')}: missing {key}")
        if set(case.get("requirements", [])) - expected_req or set(case.get("policies", [])) - expected_policy:
            errors.append(f"{case.get('id')}: undefined requirement or policy")
        if suite.get("application_implemented") is False and (case.get("execution_status") != "not_run" or case.get("last_run") is not None):
            errors.append(f"{case.get('id')}: unimplemented application cannot claim an executed result")
    scene_ids = re.findall(r"(?m)^## (SCN-\d{3})\b", (root / "docs/SCENARIOS.md").read_text())
    if len(case_ids) != len(set(case_ids)) or set(case_ids) != set(scene_ids):
        errors.append("scenario JSON and document IDs differ or contain duplicates")
    if case_req != expected_req:
        errors.append(f"scenario coverage missing: {sorted(expected_req-case_req)}")
    unknown_scene = set(re.findall(r"SCN-\d{3}", all_text)) - set(case_ids)
    if unknown_scene:
        errors.append(f"undefined scenarios: {sorted(unknown_scene)}")

    try:
        from jsonschema import Draft202012Validator, FormatChecker
        from openapi_spec_validator import validate_spec
    except ImportError:
        errors.append("install requirements-docs.lock in the project virtualenv")
        return errors, stats
    try:
        validate_spec(spec)
    except Exception as exc:
        errors.append(f"OpenAPI standard validation: {exc}")
    example_ids = set()
    valid_count = invalid_count = 0
    for example in examples.get("examples", []):
        name = example.get("id")
        if name in example_ids:
            errors.append(f"duplicate example: {name}")
        example_ids.add(name)
        try:
            pointer(example["schema_ref"])
            wrapper = {"$ref": example["schema_ref"], "components": spec["components"]}
            validation_errors = list(Draft202012Validator(wrapper, format_checker=FormatChecker()).iter_errors(example["value"]))
            passed = not validation_errors
            if passed != example["should_validate"]:
                detail = "; ".join(error.message for error in validation_errors[:2])
                errors.append(f"{name}: expected valid={example['should_validate']}, observed={passed}: {detail}")
            if example["should_validate"]:
                valid_count += 1
            else:
                invalid_count += 1
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{name}: malformed contract example: {exc}")
    if not valid_count or not invalid_count:
        errors.append("contract examples require both valid and rejected inputs")
    stats.update(requirements=len(req_ids), policies=len(policy_ids), scenarios=len(case_ids),
                 operations=len(operations), positive_examples=valid_count, negative_examples=invalid_count)
    return errors, stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json-report", type=Path)
    args = parser.parse_args()
    errors, stats = check(args.root.resolve())
    report = {"scope": "design_artifacts_only_not_application_validation", "passed": not errors, "counts": stats, "errors": errors}
    if args.json_report:
        args.json_report.parent.mkdir(parents=True, exist_ok=True)
        args.json_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
