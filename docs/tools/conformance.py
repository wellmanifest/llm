#!/usr/bin/env python3
"""Dependency-free semantic conformance checks for wellmanifest/llm v1."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any

_TOOLS_DIR = str(Path(__file__).resolve().parent)
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

from schema_validators import (  # noqa: E402
    END,
    MAX_JSON_DEPTH,
    OPERATIONS,
    START,
    DuplicateKeyError,
    extract_marked_block,
    is_strict_int,
    load_strict_json,
    read_regular_utf8,
    validate_request_document,
    validate_response_document,
)

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "models"
ADAPTERS = ROOT / "docs" / "adapters"
PROFILE_ID_RE = re.compile(r"\A[a-z0-9][a-z0-9.-]*\Z")
SEMVER_RE = re.compile(r"\A[0-9]+\.[0-9]+\.[0-9]+\Z")
ADOPT_RE = re.compile(r"\Awellmanifest/[a-z0-9-]+\Z")
STEP_IDS = [
    "discover",
    "knowledge",
    "artifact",
    "observe",
    "research",
    "invoke",
    "validate",
    "receipt",
]
ADAPTER_FILES = {
    "codex": "AGENTS.md",
    "claude": "CLAUDE.md",
    "gemini": "GEMINI.md",
    "cursor": "subactor-first.mdc",
    "copilot": "copilot-instructions.md",
    "generic": "SUBACTOR.md",
}

__all__ = [
    "ADAPTER_FILES",
    "END",
    "OPERATIONS",
    "START",
    "assert_closed_object_schemas",
    "check_adapters",
    "check_profile",
    "check_required_by_schema",
    "check_schema",
    "load_json",
    "main",
    "marked_block",
    "validate_request_document",
    "validate_response_document",
]


def _rel_label(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    label = _rel_label(path)
    try:
        value = load_strict_json(path)
    except (OSError, UnicodeError, DuplicateKeyError, ValueError, TypeError) as exc:
        errors.append(f"{label}: invalid JSON: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{label}: top level must be an object")
        return {}
    return value


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def marked_block(path: Path, errors: list[str]) -> str:
    label = _rel_label(path)
    try:
        text = read_regular_utf8(path)
    except (OSError, UnicodeError, ValueError) as exc:
        errors.append(f"{label}: unreadable: {exc}")
        return ""
    require(text.count(START) == 1, f"{label}: start marker count must be one", errors)
    require(text.count(END) == 1, f"{label}: end marker count must be one", errors)
    block, marker_err = extract_marked_block(text)
    if marker_err is not None or block is None:
        if marker_err and "inverted" in marker_err:
            errors.append(f"{label}: {marker_err}")
        return ""
    for token in (
        "knowledge.resolve",
        "artifact.resolve",
        "research.plan",
        "validation.run",
        "receipt.write",
    ):
        require(token in block, f"{label}: marked block misses {token}", errors)
    return block


def assert_closed_object_schemas(
    schema: Any, label: str, errors: list[str]
) -> None:
    """Require every object subschema to declare explicit closed or bounded additionalProperties."""
    stack: list[tuple[Any, str, int]] = [(schema, label, 0)]
    while stack:
        node, where, depth = stack.pop()
        if depth > MAX_JSON_DEPTH:
            errors.append(f"{where}: schema nesting depth exceeds maximum ({MAX_JSON_DEPTH})")
            return
        if isinstance(node, dict):
            if node.get("type") == "object":
                addl = node.get("additionalProperties")
                bounded_map = isinstance(addl, dict) and is_strict_int(node.get("maxProperties"))
                if addl is not False and not bounded_map:
                    errors.append(f"{where}: object schema must close additionalProperties")
            for key, child in node.items():
                if isinstance(child, (dict, list)):
                    stack.append((child, f"{where}.{key}", depth + 1))
        elif isinstance(node, list):
            for idx, child in enumerate(node):
                if isinstance(child, (dict, list)):
                    stack.append((child, f"{where}[{idx}]", depth + 1))


def check_schema(
    path: Path, schema_id: str, document_schema: str, errors: list[str]
) -> None:
    value = load_json(path, errors)
    require(
        value.get("$schema") == "https://json-schema.org/draft/2020-12/schema",
        f"{path.name}: wrong JSON Schema dialect",
        errors,
    )
    require(value.get("$id") == schema_id, f"{path.name}: wrong $id", errors)
    require(value.get("type") == "object", f"{path.name}: root type must be object", errors)
    require(value.get("additionalProperties") is False, f"{path.name}: root must be closed", errors)
    assert_closed_object_schemas(value, path.name, errors)
    properties = value.get("properties")
    require(isinstance(properties, dict), f"{path.name}: properties must be an object", errors)
    schema_property = properties.get("schema", {}) if isinstance(properties, dict) else {}
    require(
        isinstance(schema_property, dict) and schema_property.get("const") == document_schema,
        f"{path.name}: document schema const mismatch",
        errors,
    )


def check_required_by_schema(
    document: Any, schema: Any, errors: list[str], where: str = "profile"
) -> None:
    """Enforce required and closed object properties declared in schema without recursion."""
    stack: list[tuple[Any, Any, str, int]] = [(document, schema, where, 0)]
    while stack:
        cur_doc, cur_schema, cur_where, depth = stack.pop()
        if depth > MAX_JSON_DEPTH:
            errors.append(f"{cur_where}: nesting depth exceeds maximum ({MAX_JSON_DEPTH})")
            return
        if not isinstance(cur_schema, dict):
            continue
        if cur_schema.get("type") == "object" and not isinstance(cur_doc, dict):
            errors.append(f"{cur_where}: expected object")
            continue
        if not isinstance(cur_doc, dict):
            continue
        if any(not isinstance(key, str) for key in cur_doc):
            errors.append(f"{cur_where}: object keys must be strings")
        str_keys = {key for key in cur_doc if isinstance(key, str)}
        for name in cur_schema.get("required", []):
            require(name in str_keys, f"{cur_where}: missing required '{name}'", errors)
        props = cur_schema.get("properties")
        if cur_schema.get("additionalProperties") is False and isinstance(props, dict):
            for extra in sorted(str_keys - set(props)):
                errors.append(f"{cur_where}: unknown property '{extra}'")
        if isinstance(props, dict):
            for name, child in reversed(list(props.items())):
                if name in str_keys:
                    stack.append((cur_doc[name], child, f"{cur_where}.{name}", depth + 1))


def _as_dict(parent: dict[str, Any], key: str) -> dict[str, Any]:
    val = parent.get(key)
    return val if isinstance(val, dict) else {}


def check_profile(profile_path: Path, errors: list[str]) -> dict[str, Any]:
    profile = load_json(profile_path, errors)
    schema_path = MODELS / "llm-profile.schema.json"
    if (profile_path.parent / "llm-profile.schema.json").is_file():
        schema_path = profile_path.parent / "llm-profile.schema.json"
    check_required_by_schema(profile, load_json(schema_path, errors), errors)
    require(
        profile.get("$schema") == "./llm-profile.schema.json",
        "profile: schema path mismatch",
        errors,
    )
    require(
        profile.get("schema") == "wellmanifest.llm-profile/v1",
        "profile: schema identity mismatch",
        errors,
    )
    profile_id = profile.get("profileId")
    require(
        isinstance(profile_id, str)
        and PROFILE_ID_RE.fullmatch(profile_id) is not None
        and profile_id == "subactor-first",
        "profile: profileId mismatch",
        errors,
    )
    version = profile.get("version")
    require(
        isinstance(version, str) and SEMVER_RE.fullmatch(version) is not None,
        "profile: version must be semantic version X.Y.Z",
        errors,
    )

    placement = _as_dict(profile, "placement")
    require(placement.get("home") == "wellmanifest", "profile: HOME must be wellmanifest", errors)
    require(placement.get("shape") == "domain_pack", "profile: SHAPE must be domain_pack", errors)
    require(
        placement.get("runtimeOwner") == "subactor",
        "profile: runtimeOwner must be subactor",
        errors,
    )
    adopt = placement.get("adopt")
    require(
        isinstance(adopt, list)
        and all(isinstance(x, str) and ADOPT_RE.fullmatch(x) for x in adopt)
        and len(adopt) == len(set(adopt)),
        "profile: placement.adopt must list unique wellmanifest/* standards",
        errors,
    )

    bootstrap = _as_dict(profile, "bootstrap")
    require(bootstrap.get("marker") == "SUBACTOR-FIRST", "profile: marker mismatch", errors)
    require(
        bootstrap.get("profileTarget") == ".wellmanifest/llm.json",
        "profile: profileTarget mismatch",
        errors,
    )

    transport = _as_dict(profile, "transport")
    require(transport.get("preferred") == "mcp", "profile: MCP must be preferred", errors)
    require(
        transport.get("fallbacks") == ["https", "cli", "file"],
        "profile: fallback order mismatch",
        errors,
    )
    require(
        transport.get("semanticEnvelope") == "application/json",
        "profile: semanticEnvelope must be application/json",
        errors,
    )

    workflow = profile.get("workflow")
    actual = (
        [step.get("operation") for step in workflow if isinstance(step, dict)]
        if isinstance(workflow, list)
        else []
    )
    require(actual == OPERATIONS, f"profile: operation order mismatch: {actual}", errors)
    if isinstance(workflow, list) and len(workflow) == len(OPERATIONS):
        for idx, step in enumerate(workflow):
            if not isinstance(step, dict):
                errors.append(f"profile.workflow[{idx}]: step must be an object")
                continue
            if any(not isinstance(key, str) for key in step):
                errors.append(f"profile.workflow[{idx}]: step keys must be strings")
            str_keys = {key for key in step if isinstance(key, str)}
            extra = str_keys - {"id", "operation", "required", "when"}
            require(
                not extra,
                f"profile.workflow[{idx}]: unknown step fields {sorted(extra)}",
                errors,
            )
            require(
                step.get("id") == STEP_IDS[idx],
                f"profile.workflow[{idx}]: step id mismatch",
                errors,
            )
            require(
                isinstance(step.get("required"), bool),
                f"profile.workflow[{idx}]: required must be boolean",
                errors,
            )
            if "when" in step:
                when = step.get("when")
                require(
                    isinstance(when, str) and bool(when.strip()),
                    f"profile.workflow[{idx}]: when must be non-empty string",
                    errors,
                )
        for index in (0, 1, 2, 4, 5, 6, 7):
            step_obj = workflow[index] if isinstance(workflow[index], dict) else {}
            require(
                step_obj.get("required") is True,
                f"profile: {OPERATIONS[index]} must be required",
                errors,
            )

    authority = _as_dict(profile, "authority")
    require(
        authority
        == {"llm": "advisory", "mutation": "external-grant", "merge": "trusted-validator"},
        "profile: authority boundary mismatch",
        errors,
    )
    security = _as_dict(profile, "security")
    require(
        security.get("credentials") == "out-of-context",
        "profile: credentials must remain out of context",
        errors,
    )
    require(
        security.get("secretReferences") == "opaque",
        "profile: secretReferences must be opaque",
        errors,
    )
    for key in ("secretsInContext", "secretsInUris", "secretsInLogs"):
        require(security.get(key) is False, f"profile: {key} must be false", errors)

    limits = _as_dict(profile, "limits")
    limit_bounds = (
        ("maxKnowledgeItems", 1, 50),
        ("maxContextBytes", 1024, 1048576),
        ("maxObservationSeconds", 1, 300),
        ("maxExternalQueries", 0, 20),
        ("maxInlineEvidenceBytes", 0, 65536),
    )
    for key, lo, hi in limit_bounds:
        val = limits.get(key)
        require(
            is_strict_int(val) and lo <= val <= hi,
            f"profile.limits.{key}: must be integer in {lo}..{hi}",
            errors,
        )

    receipt = _as_dict(profile, "receipt")
    for key in ("redacted", "immutableRefs", "recordRoute", "recordModel"):
        require(receipt.get(key) is True, f"profile.receipt.{key}: must be true", errors)
    return profile


def check_adapters(profile: dict[str, Any], errors: list[str]) -> None:
    bootstrap = _as_dict(profile, "bootstrap")
    targets = _as_dict(bootstrap, "adapterTargets")
    expected_targets = {
        "codex": "AGENTS.md",
        "claude": "CLAUDE.md",
        "gemini": "GEMINI.md",
        "cursor": ".cursor/rules/subactor-first.mdc",
        "copilot": ".github/copilot-instructions.md",
        "generic": "SUBACTOR.md",
    }
    require(targets == expected_targets, "profile: adapter target set mismatch", errors)
    require(
        bootstrap.get("schemaTargets")
        == {
            "profile": ".wellmanifest/llm-profile.schema.json",
            "request": ".wellmanifest/request.schema.json",
            "response": ".wellmanifest/response.schema.json",
        },
        "profile: installed schema target set mismatch",
        errors,
    )
    blocks = []
    for host, filename in ADAPTER_FILES.items():
        path = ADAPTERS / filename
        blocks.append(marked_block(path, errors))
        require(host in targets, f"profile: missing {host} adapter target", errors)
    nonempty = [block for block in blocks if block]
    require(
        len(nonempty) == len(ADAPTER_FILES) and len(set(nonempty)) == 1,
        "adapters: marked normative blocks must be identical",
        errors,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--all", action="store_true", help="check all bundled contracts (default)"
    )
    parser.add_argument(
        "--profile", type=Path, default=MODELS / "subactor-first.v1.json"
    )
    parser.add_argument("--request", type=Path, help="validate an llm-request/v1 JSON file")
    parser.add_argument("--response", type=Path, help="validate an llm-response/v1 JSON file")
    args = parser.parse_args(argv)
    profile_path = Path(os.path.abspath(args.profile))

    errors: list[str] = []
    if args.request is not None:
        doc = load_json(Path(os.path.abspath(args.request)), errors)
        if not errors:
            errors.extend(validate_request_document(doc))
    if args.response is not None:
        doc = load_json(Path(os.path.abspath(args.response)), errors)
        if not errors:
            errors.extend(validate_response_document(doc))
    if args.all or (args.request is None and args.response is None):
        check_schema(
            MODELS / "llm-profile.schema.json",
            "https://wellmanifest.dev/llm/v1/llm-profile.schema.json",
            "wellmanifest.llm-profile/v1",
            errors,
        )
        check_schema(
            MODELS / "request.schema.json",
            "https://wellmanifest.dev/llm/v1/request.schema.json",
            "wellmanifest.llm-request/v1",
            errors,
        )
        check_schema(
            MODELS / "response.schema.json",
            "https://wellmanifest.dev/llm/v1/response.schema.json",
            "wellmanifest.llm-response/v1",
            errors,
        )
        profile = check_profile(profile_path, errors)
        check_adapters(profile, errors)

    if errors:
        for error in errors:
            print(f"FAIL {error}", file=sys.stderr)
        print(f"FAIL wellmanifest/llm v1 ({len(errors)} finding(s))", file=sys.stderr)
        return 1
    print(f"PASS wellmanifest/llm v1 profile={profile_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
