"""Strict JSON, regular-file IO, marker, and request/response validators for wellmanifest/llm."""

from __future__ import annotations

import math
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

_TOOLS_DIR = str(Path(__file__).resolve().parent)
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

from llm_io import (  # noqa: E402
    MAX_FILE_BYTES,
    MAX_INT_DIGITS,
    MAX_JSON_DEPTH,
    DuplicateKeyError,
    has_control_chars,
    has_lone_surrogate,
    has_symlink_ancestor,
    is_finite_int,
    load_strict_json,
    loads_strict_json,
    read_regular_utf8,
)

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
REQUEST_ID_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._:-]{7,127}\Z")
GRANT_REF_RE = re.compile(r"\Agrant://[A-Za-z0-9._/-]+\Z")
CONTEXT_REF_RE = re.compile(r"\A(?:knowledge|artifact|observation)://[^\s?#]+\Z")
RESULT_REF_RE = re.compile(
    r"\A(?:knowledge://subactor/[^\s?#]+/v[0-9]+|"
    r"artifact://subactor/[^\s?#]+/r[0-9]+|"
    r"observation://[^\s?#]+)\Z"
)
KNOWLEDGE_REF_RE = re.compile(r"\Aknowledge://subactor/[^\s?#]+/v[0-9]+\Z")
SHA256_RE = re.compile(r"\Asha256:[a-f0-9]{64}\Z")
RFC3339_RE = re.compile(
    r"\A[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,9})?(?:Z|[+-][0-9]{2}:[0-9]{2})\Z"
)
_SUBSEC_TRIM_RE = re.compile(r"\.([0-9]{6})[0-9]+")

__all__ = [
    "CONTEXT_REF_RE",
    "DuplicateKeyError",
    "END",
    "GRANT_REF_RE",
    "KNOWLEDGE_REF_RE",
    "MAX_FILE_BYTES",
    "MAX_INT_DIGITS",
    "MAX_JSON_DEPTH",
    "OPERATIONS",
    "REQUEST_ID_RE",
    "RESULT_REF_RE",
    "RFC3339_RE",
    "SHA256_RE",
    "START",
    "extract_marked_block",
    "extract_marked_span",
    "has_control_chars",
    "has_lone_surrogate",
    "has_symlink_ancestor",
    "is_finite_int",
    "is_strict_int",
    "is_valid_context_ref",
    "is_valid_grant_ref",
    "is_valid_knowledge_ref",
    "is_valid_result_ref",
    "load_strict_json",
    "loads_strict_json",
    "parse_rfc3339",
    "read_regular_utf8",
    "validate_request_document",
    "validate_response_document",
]


def is_strict_int(value: Any) -> bool:
    return type(value) is int


def _has_safe_uri_segments(uri: str) -> bool:
    if any(
        ord(ch) < 0x20 or ord(ch) == 0x7F or ch.isspace() or ch in {"\\", "?", "#"} for ch in uri
    ):
        return False
    _, sep, remainder = uri.partition("://")
    if not sep or not remainder or remainder.startswith("/") or remainder.endswith("/"):
        return False
    for seg in remainder.split("/"):
        if not seg or seg in {".", ".."}:
            return False
        if ":" in seg and any(not sub or sub in {".", ".."} for sub in seg.split(":")):
            return False
    return True


def is_valid_grant_ref(value: Any) -> bool:
    return (
        isinstance(value, str)
        and GRANT_REF_RE.fullmatch(value) is not None
        and _has_safe_uri_segments(value)
    )


def is_valid_context_ref(value: Any) -> bool:
    return (
        isinstance(value, str)
        and CONTEXT_REF_RE.fullmatch(value) is not None
        and _has_safe_uri_segments(value)
    )


def is_valid_result_ref(value: Any) -> bool:
    return (
        isinstance(value, str)
        and RESULT_REF_RE.fullmatch(value) is not None
        and _has_safe_uri_segments(value)
    )


def is_valid_knowledge_ref(value: Any) -> bool:
    return (
        isinstance(value, str)
        and KNOWLEDGE_REF_RE.fullmatch(value) is not None
        and _has_safe_uri_segments(value)
    )


def parse_rfc3339(value: Any) -> datetime | None:
    if not isinstance(value, str) or RFC3339_RE.fullmatch(value) is None:
        return None
    normalized = _SUBSEC_TRIM_RE.sub(r".\1", value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def extract_marked_block(text: str) -> tuple[str | None, str | None]:
    """Return (block, error). (None, None) means no markers exist in text."""
    start_count = text.count(START)
    end_count = text.count(END)
    if start_count == 0 and end_count == 0:
        return None, None
    if start_count != 1 or end_count != 1:
        return None, "malformed SUBACTOR-FIRST marker pair"
    start_idx = text.index(START)
    end_idx = text.index(END)
    if end_idx < start_idx:
        return None, "inverted SUBACTOR-FIRST marker pair (END precedes START)"
    inner = text[start_idx + len(START) : end_idx].strip()
    return inner, None


def extract_marked_span(text: str) -> str:
    block, err = extract_marked_block(text)
    if err is not None or block is None:
        raise ValueError(err or "missing SUBACTOR-FIRST marker pair")
    start_idx = text.index(START)
    end_idx = text.index(END) + len(END)
    return text[start_idx:end_idx]


def _closed_dict(
    value: Any, label: str, required: set[str], allowed: set[str], errors: list[str]
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        errors.append(f"{label}: must be an object")
        return None
    if any(not isinstance(key, str) for key in value):
        errors.append(f"{label}: object keys must be strings")
    str_keys = {key for key in value if isinstance(key, str)}
    for missing in sorted(required - str_keys):
        errors.append(f"{label}: missing required '{missing}'")
    for extra in sorted(str_keys - allowed):
        errors.append(f"{label}: unknown field '{extra}'")
    return value


def _is_safe_str(value: Any, lo: int, hi: int, *, allow_newlines: bool = False) -> bool:
    return (
        isinstance(value, str)
        and lo <= len(value) <= hi
        and not has_lone_surrogate(value)
        and not has_control_chars(value, allow_newlines=allow_newlines)
    )


def _validate_intent_subtree(intent: dict[str, Any], errors: list[str]) -> None:
    stack: list[tuple[Any, int]] = [(intent, 1)]
    while stack:
        current, depth = stack.pop()
        if depth > MAX_JSON_DEPTH:
            errors.append("request.intent: nesting depth exceeds maximum")
            return
        if isinstance(current, dict):
            for key, child in current.items():
                if not isinstance(key, str):
                    errors.append("request.intent: object keys must be strings")
                    return
                if has_lone_surrogate(key):
                    errors.append("request.intent: lone UTF-16 surrogate in key is forbidden")
                    return
                if has_control_chars(key, allow_newlines=False):
                    errors.append("request.intent: control character in key is forbidden")
                    return
                stack.append((child, depth + 1))
        elif isinstance(current, list):
            for child in current:
                stack.append((child, depth + 1))
        elif current is None or isinstance(current, bool):
            continue
        elif isinstance(current, str):
            if has_lone_surrogate(current):
                errors.append("request.intent: lone UTF-16 surrogate in string is forbidden")
                return
            if has_control_chars(current, allow_newlines=True):
                errors.append("request.intent: control character in string is forbidden")
                return
        elif type(current) is int:
            if not is_finite_int(current):
                errors.append("request.intent: integer magnitude exceeds finite range")
                return
        elif isinstance(current, float):
            if not math.isfinite(current):
                errors.append("request.intent: non-finite number is forbidden")
                return
        else:
            errors.append("request.intent: unsupported value type")
            return


def validate_request_document(doc: Any) -> list[str]:
    errors: list[str] = []
    req_fields = {"schema", "requestId", "operation", "intent", "limits", "authority"}
    opt_fields = {"grantRef", "contextRefs"}
    req = _closed_dict(doc, "request", req_fields, req_fields | opt_fields, errors)
    if req is None:
        return errors
    if req.get("schema") != "wellmanifest.llm-request/v1":
        errors.append("request.schema: must equal 'wellmanifest.llm-request/v1'")
    req_id = req.get("requestId")
    if not isinstance(req_id, str) or REQUEST_ID_RE.fullmatch(req_id) is None:
        errors.append("request.requestId: invalid identifier")
    op = req.get("operation")
    if not isinstance(op, str) or op not in OPERATIONS:
        errors.append("request.operation: unknown operation")
    intent = req.get("intent")
    if not isinstance(intent, dict) or not 1 <= len(intent) <= 16:
        errors.append("request.intent: must be an object with 1..16 properties")
    else:
        _validate_intent_subtree(intent, errors)
    lim_fields = {"maxItems", "maxBytes", "timeoutSeconds"}
    limits = _closed_dict(req.get("limits"), "request.limits", lim_fields, lim_fields, errors)
    if limits is not None:
        bounds = (("maxItems", 1, 50), ("maxBytes", 256, 1048576), ("timeoutSeconds", 1, 300))
        for key, lo, hi in bounds:
            val = limits.get(key)
            if not is_strict_int(val) or not lo <= val <= hi:
                errors.append(f"request.limits.{key}: must be integer in {lo}..{hi}")
    auth = req.get("authority")
    if not isinstance(auth, str) or auth not in {"read-only", "advisory", "mutation-with-grant"}:
        errors.append("request.authority: invalid authority mode")
    has_grant = "grantRef" in req
    if auth == "mutation-with-grant":
        if not is_valid_grant_ref(req.get("grantRef")):
            errors.append("request.grantRef: mutation-with-grant requires valid grant:// URI")
    elif has_grant:
        errors.append("request.grantRef: forbidden unless authority is mutation-with-grant")
    if "contextRefs" in req:
        ctx = req.get("contextRefs")
        if (
            not isinstance(ctx, list)
            or not all(is_valid_context_ref(x) for x in ctx)
            or len(ctx) != len(set(ctx))
        ):
            errors.append("request.contextRefs: must be unique valid context URIs")
    return errors


def validate_response_document(doc: Any) -> list[str]:
    errors: list[str] = []
    req_fields = {"schema", "requestId", "operation", "status", "results", "receipt"}
    resp = _closed_dict(doc, "response", req_fields, req_fields | {"gap"}, errors)
    if resp is None:
        return errors
    if resp.get("schema") != "wellmanifest.llm-response/v1":
        errors.append("response.schema: must equal 'wellmanifest.llm-response/v1'")
    req_id = resp.get("requestId")
    if not isinstance(req_id, str) or REQUEST_ID_RE.fullmatch(req_id) is None:
        errors.append("response.requestId: invalid identifier")
    op = resp.get("operation")
    if not isinstance(op, str) or op not in OPERATIONS:
        errors.append("response.operation: unknown operation")
    status = resp.get("status")
    if not isinstance(status, str) or status not in {"ok", "gap", "denied", "error"}:
        errors.append("response.status: invalid status")
    if status == "gap" and "gap" not in resp:
        errors.append("response.gap: required when status is 'gap'")
    elif status != "gap" and "gap" in resp:
        errors.append("response.gap: forbidden unless status is 'gap'")
    if "gap" in resp:
        gap_req = {"method", "query", "deduplicateAgainst"}
        gap = _closed_dict(resp.get("gap"), "response.gap", gap_req, gap_req, errors)
        if gap is not None:
            method = gap.get("method")
            if not isinstance(method, str) or method not in {
                "live-observation",
                "internet-research",
            }:
                errors.append("response.gap.method: invalid gap method")
            query = gap.get("query")
            if not _is_safe_str(query, 1, 1000, allow_newlines=True):
                errors.append("response.gap.query: must be valid UTF-8 of 1..1000 chars")
            dedup = gap.get("deduplicateAgainst")
            if (
                not isinstance(dedup, list)
                or not all(is_valid_knowledge_ref(x) for x in dedup)
                or len(dedup) != len(set(dedup))
            ):
                errors.append("response.gap.deduplicateAgainst: invalid knowledge refs")
    results = resp.get("results")
    if not isinstance(results, list) or len(results) > 50:
        errors.append("response.results: must be an array of <= 50 items")
    else:
        for idx, item in enumerate(results):
            r_req = {"ref", "mediaType", "digest"}
            row = _closed_dict(item, f"response.results[{idx}]", r_req, r_req | {"summary"}, errors)
            if row is None:
                continue
            if not is_valid_result_ref(row.get("ref")):
                errors.append(f"response.results[{idx}].ref: invalid reference URI")
            mt = row.get("mediaType")
            if not _is_safe_str(mt, 3, 200, allow_newlines=False):
                errors.append(f"response.results[{idx}].mediaType: invalid mediaType")
            dg = row.get("digest")
            if not isinstance(dg, str) or SHA256_RE.fullmatch(dg) is None:
                errors.append(f"response.results[{idx}].digest: invalid sha256 digest")
            if "summary" in row and not _is_safe_str(row["summary"], 0, 2000, allow_newlines=True):
                errors.append(f"response.results[{idx}].summary: must be valid UTF-8 <= 2000 chars")
    rcpt_req = {"redacted", "transport", "route", "model", "startedAt", "finishedAt"}
    rcpt = _closed_dict(
        resp.get("receipt"), "response.receipt", rcpt_req, rcpt_req | {"grantRef"}, errors
    )
    if rcpt is not None:
        if rcpt.get("redacted") is not True:
            errors.append("response.receipt.redacted: must be true")
        transport = rcpt.get("transport")
        if not isinstance(transport, str) or transport not in {"mcp", "https", "cli", "file"}:
            errors.append("response.receipt.transport: invalid transport")
        route = rcpt.get("route")
        if not _is_safe_str(route, 1, 200, allow_newlines=False):
            errors.append("response.receipt.route: must be valid UTF-8 of 1..200 chars")
        model = rcpt.get("model")
        if model is not None and not _is_safe_str(model, 0, 200, allow_newlines=False):
            errors.append("response.receipt.model: must be null or valid UTF-8 <= 200 chars")
        started = parse_rfc3339(rcpt.get("startedAt"))
        finished = parse_rfc3339(rcpt.get("finishedAt"))
        if started is None or finished is None:
            errors.append("response.receipt: startedAt and finishedAt must be RFC3339")
        elif finished < started:
            errors.append("response.receipt: finishedAt precedes startedAt")
        if "grantRef" in rcpt and not is_valid_grant_ref(rcpt["grantRef"]):
            errors.append("response.receipt.grantRef: invalid grant:// URI")
    return errors
