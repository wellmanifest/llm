"""Strict JSON, marker-pair, and request/response validators for wellmanifest/llm v1."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

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
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$")
GRANT_REF_RE = re.compile(r"^grant://[A-Za-z0-9._/-]+$")
CONTEXT_REF_RE = re.compile(r"^(?:knowledge|artifact|observation)://[^\s?#]+$")
RESULT_REF_RE = re.compile(
    r"^(?:knowledge://subactor/[^\s?#]+/v[0-9]+|"
    r"artifact://subactor/[^\s?#]+/r[0-9]+|"
    r"observation://[^\s?#]+)$"
)
KNOWLEDGE_REF_RE = re.compile(r"^knowledge://subactor/[^\s?#]+/v[0-9]+$")
SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
RFC3339_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,9})?(?:Z|[+-][0-9]{2}:[0-9]{2})$"
)


class DuplicateKeyError(ValueError):
    """Raised when a JSON object contains duplicate keys."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, val in pairs:
        if key in obj:
            raise DuplicateKeyError(f"duplicate JSON key {key!r}")
        obj[key] = val
    return obj


def loads_strict_json(raw: str) -> Any:
    return json.loads(raw, object_pairs_hook=_reject_duplicate_keys)


def load_strict_json(path: Path) -> Any:
    return loads_strict_json(path.read_text(encoding="utf-8"))


def is_strict_int(value: Any) -> bool:
    return type(value) is int


def parse_rfc3339(value: Any) -> datetime | None:
    if not isinstance(value, str) or RFC3339_RE.fullmatch(value) is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
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
    for missing in sorted(required - set(value)):
        errors.append(f"{label}: missing required '{missing}'")
    for extra in sorted(set(value) - allowed):
        errors.append(f"{label}: unknown field '{extra}'")
    return value


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
    if req.get("operation") not in OPERATIONS:
        errors.append("request.operation: unknown operation")
    intent = req.get("intent")
    if not isinstance(intent, dict) or not 1 <= len(intent) <= 16:
        errors.append("request.intent: must be an object with 1..16 properties")
    lim_fields = {"maxItems", "maxBytes", "timeoutSeconds"}
    limits = _closed_dict(req.get("limits"), "request.limits", lim_fields, lim_fields, errors)
    if limits is not None:
        bounds = (("maxItems", 1, 50), ("maxBytes", 256, 1048576), ("timeoutSeconds", 1, 300))
        for key, lo, hi in bounds:
            val = limits.get(key)
            if not is_strict_int(val) or not lo <= val <= hi:
                errors.append(f"request.limits.{key}: must be integer in {lo}..{hi}")
    auth = req.get("authority")
    if auth not in {"read-only", "advisory", "mutation-with-grant"}:
        errors.append("request.authority: invalid authority mode")
    has_grant = "grantRef" in req
    if auth == "mutation-with-grant":
        grant_ref = req.get("grantRef")
        if not isinstance(grant_ref, str) or GRANT_REF_RE.fullmatch(grant_ref) is None:
            errors.append("request.grantRef: mutation-with-grant requires valid grant:// URI")
    elif has_grant:
        errors.append("request.grantRef: forbidden unless authority is mutation-with-grant")
    if "contextRefs" in req:
        ctx = req.get("contextRefs")
        if (
            not isinstance(ctx, list)
            or not all(isinstance(x, str) and CONTEXT_REF_RE.fullmatch(x) for x in ctx)
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
    if resp.get("operation") not in OPERATIONS:
        errors.append("response.operation: unknown operation")
    status = resp.get("status")
    if status not in {"ok", "gap", "denied", "error"}:
        errors.append("response.status: invalid status")
    if status == "gap" and "gap" not in resp:
        errors.append("response.gap: required when status is 'gap'")
    elif status != "gap" and "gap" in resp:
        errors.append("response.gap: forbidden unless status is 'gap'")
    if "gap" in resp:
        gap_req = {"method", "query", "deduplicateAgainst"}
        gap = _closed_dict(resp.get("gap"), "response.gap", gap_req, gap_req, errors)
        if gap is not None:
            if gap.get("method") not in {"live-observation", "internet-research"}:
                errors.append("response.gap.method: invalid gap method")
            query = gap.get("query")
            if not isinstance(query, str) or not 1 <= len(query) <= 1000:
                errors.append("response.gap.query: must be 1..1000 chars")
            dedup = gap.get("deduplicateAgainst")
            if (
                not isinstance(dedup, list)
                or not all(isinstance(x, str) and KNOWLEDGE_REF_RE.fullmatch(x) for x in dedup)
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
            if not isinstance(row.get("ref"), str) or RESULT_REF_RE.fullmatch(row["ref"]) is None:
                errors.append(f"response.results[{idx}].ref: invalid reference URI")
            mt = row.get("mediaType")
            if not isinstance(mt, str) or len(mt) < 3:
                errors.append(f"response.results[{idx}].mediaType: invalid mediaType")
            dg = row.get("digest")
            if not isinstance(dg, str) or SHA256_RE.fullmatch(dg) is None:
                errors.append(f"response.results[{idx}].digest: invalid sha256 digest")
            if "summary" in row and (
                not isinstance(row["summary"], str) or len(row["summary"]) > 2000
            ):
                errors.append(f"response.results[{idx}].summary: must be string <= 2000 chars")
    rcpt_req = {"redacted", "transport", "route", "model", "startedAt", "finishedAt"}
    rcpt = _closed_dict(
        resp.get("receipt"), "response.receipt", rcpt_req, rcpt_req | {"grantRef"}, errors
    )
    if rcpt is not None:
        if rcpt.get("redacted") is not True:
            errors.append("response.receipt.redacted: must be true")
        if rcpt.get("transport") not in {"mcp", "https", "cli", "file"}:
            errors.append("response.receipt.transport: invalid transport")
        route = rcpt.get("route")
        if not isinstance(route, str) or not 1 <= len(route) <= 200:
            errors.append("response.receipt.route: must be 1..200 chars")
        model = rcpt.get("model")
        if model is not None and (not isinstance(model, str) or len(model) > 200):
            errors.append("response.receipt.model: must be null or string <= 200 chars")
        started = parse_rfc3339(rcpt.get("startedAt"))
        finished = parse_rfc3339(rcpt.get("finishedAt"))
        if started is None or finished is None:
            errors.append("response.receipt: startedAt and finishedAt must be RFC3339")
        elif finished < started:
            errors.append("response.receipt: finishedAt precedes startedAt")
        if "grantRef" in rcpt and (
            not isinstance(rcpt["grantRef"], str)
            or GRANT_REF_RE.fullmatch(rcpt["grantRef"]) is None
        ):
            errors.append("response.receipt.grantRef: invalid grant:// URI")
    return errors
