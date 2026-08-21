#!/usr/bin/env python3
"""Dependency-free semantic conformance checks for wellmanifest/llm v1."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "models"
ADAPTERS = ROOT / "docs" / "adapters"
START = "<!-- SUBACTOR-FIRST:START wellmanifest/llm v1 -->"
END = "<!-- SUBACTOR-FIRST:END wellmanifest/llm v1 -->"
OPERATIONS = [
    "profile.resolve",
    "knowledge.resolve",
    "artifact.resolve",
    "observation.read",
    "research.plan",
    "llm.invoke",
    "validation.run",
    "receipt.write",
]
ADAPTER_FILES = {
    "codex": "AGENTS.md",
    "claude": "CLAUDE.md",
    "gemini": "GEMINI.md",
    "cursor": "subactor-first.mdc",
    "copilot": "copilot-instructions.md",
    "generic": "SUBACTOR.md",
}


def load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        label = str(path.relative_to(ROOT))
    except ValueError:
        label = str(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
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
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"{path.relative_to(ROOT)}: unreadable: {exc}")
        return ""
    require(
        text.count(START) == 1,
        f"{path.relative_to(ROOT)}: start marker count must be one",
        errors,
    )
    require(
        text.count(END) == 1,
        f"{path.relative_to(ROOT)}: end marker count must be one",
        errors,
    )
    if START not in text or END not in text:
        return ""
    block = text.split(START, 1)[1].split(END, 1)[0].strip()
    for token in (
        "knowledge.resolve",
        "artifact.resolve",
        "research.plan",
        "validation.run",
        "receipt.write",
    ):
        require(
            token in block,
            f"{path.relative_to(ROOT)}: marked block misses {token}",
            errors,
        )
    return block


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
    require(
        value.get("type") == "object", f"{path.name}: root type must be object", errors
    )
    require(
        value.get("additionalProperties") is False,
        f"{path.name}: root must be closed",
        errors,
    )
    properties = value.get("properties", {})
    require(
        isinstance(properties, dict),
        f"{path.name}: properties must be an object",
        errors,
    )
    schema_property = (
        properties.get("schema", {}) if isinstance(properties, dict) else {}
    )
    require(
        schema_property.get("const") == document_schema,
        f"{path.name}: document schema const mismatch",
        errors,
    )


def check_profile(profile_path: Path, errors: list[str]) -> dict[str, Any]:
    profile = load_json(profile_path, errors)
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
    require(
        profile.get("profileId") == "subactor-first",
        "profile: profileId mismatch",
        errors,
    )

    placement = profile.get("placement", {})
    require(
        placement.get("home") == "wellmanifest",
        "profile: HOME must be wellmanifest",
        errors,
    )
    require(
        placement.get("shape") == "domain_pack",
        "profile: SHAPE must be domain_pack",
        errors,
    )
    require(
        placement.get("runtimeOwner") == "subactor",
        "profile: runtimeOwner must be subactor",
        errors,
    )

    transport = profile.get("transport", {})
    require(
        transport.get("preferred") == "mcp", "profile: MCP must be preferred", errors
    )
    require(
        transport.get("fallbacks") == ["https", "cli", "file"],
        "profile: fallback order mismatch",
        errors,
    )

    workflow = profile.get("workflow", [])
    actual = (
        [step.get("operation") for step in workflow if isinstance(step, dict)]
        if isinstance(workflow, list)
        else []
    )
    require(
        actual == OPERATIONS, f"profile: operation order mismatch: {actual}", errors
    )
    if isinstance(workflow, list) and len(workflow) == len(OPERATIONS):
        for index in (0, 1, 4, 5, 6, 7):
            require(
                workflow[index].get("required") is True,
                f"profile: {OPERATIONS[index]} must be required",
                errors,
            )

    authority = profile.get("authority", {})
    require(
        authority
        == {
            "llm": "advisory",
            "mutation": "external-grant",
            "merge": "trusted-validator",
        },
        "profile: authority boundary mismatch",
        errors,
    )
    security = profile.get("security", {})
    require(
        security.get("credentials") == "out-of-context",
        "profile: credentials must remain out of context",
        errors,
    )
    for key in ("secretsInContext", "secretsInUris", "secretsInLogs"):
        require(security.get(key) is False, f"profile: {key} must be false", errors)
    receipt = profile.get("receipt", {})
    require(
        receipt.get("redacted") is True and receipt.get("immutableRefs") is True,
        "profile: receipts must be redacted and immutable-ref based",
        errors,
    )
    return profile


def check_adapters(profile: dict[str, Any], errors: list[str]) -> None:
    bootstrap = profile.get("bootstrap", {})
    targets = bootstrap.get("adapterTargets", {})
    require(
        set(targets) == set(ADAPTER_FILES),
        "profile: adapter target set mismatch",
        errors,
    )
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
        bool(nonempty) and len(set(nonempty)) == 1,
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
    args = parser.parse_args(argv)
    profile_path = args.profile.resolve()

    errors: list[str] = []
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
