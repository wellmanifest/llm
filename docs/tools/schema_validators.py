"""Strict JSON, regular-file IO, marker, and request/response validators for wellmanifest/llm."""

from __future__ import annotations

import json
import math
import os
import re
import stat
from datetime import datetime
from pathlib import Path
from typing import Any

START = "<!-- SUBACTOR-FIRST:START wellmanifest/llm v1 -->"
END = "<!-- SUBACTOR-FIRST:END wellmanifest/llm v1 -->"
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_JSON_DEPTH = 64
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


class DuplicateKeyError(ValueError):
    """Raised when a JSON object contains duplicate keys."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, val in pairs:
        if key in obj:
            raise DuplicateKeyError(f"duplicate JSON key {key!r}")
        obj[key] = val
    return obj


def _reject_json_constant(token: str) -> Any:
    raise ValueError(f"non-finite JSON constant {token!r} is forbidden")


def _parse_finite_float(token: str) -> float:
    parsed = float(token)
    if not math.isfinite(parsed):
        raise ValueError(f"non-finite JSON number {token!r} is forbidden")
    return parsed


def _check_utf8_str(value: str) -> None:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("lone UTF-16 surrogate in JSON string is forbidden") from exc


def _is_finite_int(value: int) -> bool:
    try:
        return math.isfinite(float(value))
    except OverflowError:
        return False


def _validate_json_tree(root: Any, max_depth: int = MAX_JSON_DEPTH) -> None:
    stack: list[tuple[Any, int]] = [(root, 0)]
    while stack:
        current, depth = stack.pop()
        if depth > max_depth:
            raise ValueError(f"JSON nesting depth exceeds maximum ({max_depth})")
        if isinstance(current, dict):
            for key, child in current.items():
                if not isinstance(key, str):
                    raise ValueError("JSON object keys must be strings")
                _check_utf8_str(key)
                stack.append((child, depth + 1))
        elif isinstance(current, list):
            for child in current:
                stack.append((child, depth + 1))
        elif isinstance(current, str):
            _check_utf8_str(current)
        elif type(current) is int:
            if not _is_finite_int(current):
                raise ValueError("JSON integer magnitude exceeds finite range")
        elif isinstance(current, float) and not math.isfinite(current):
            raise ValueError("non-finite float value is forbidden")


def read_regular_utf8(path: Path, max_bytes: int = MAX_FILE_BYTES) -> str:
    if type(max_bytes) is not int or max_bytes < 1:
        raise ValueError("max_bytes must be a positive integer")
    if not path.is_absolute():
        cur = Path()
        for part in path.parts[:-1]:
            cur = cur / part
            if cur.is_symlink():
                raise OSError(f"refusing symlink ancestor: {cur}")
    else:
        for anc in path.parents:
            if len(anc.parts) <= 2:
                break
            if anc.is_symlink():
                raise OSError(f"refusing symlink ancestor: {anc}")
    lst = os.lstat(path)
    if stat.S_ISLNK(lst.st_mode):
        raise OSError(f"refusing symlink file: {path}")
    if not stat.S_ISREG(lst.st_mode):
        raise OSError(f"refusing non-regular file: {path}")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise OSError(f"refusing non-regular file: {path}")
        if (lst.st_dev, lst.st_ino) != (st.st_dev, st.st_ino):
            raise OSError(f"file identity changed during open: {path}")
        if st.st_size > max_bytes:
            raise ValueError(f"file exceeds {max_bytes} bytes: {path}")
        chunks = bytearray()
        while True:
            chunk = os.read(fd, min(65536, max_bytes + 1 - len(chunks)))
            if not chunk:
                break
            chunks.extend(chunk)
            if len(chunks) > max_bytes:
                raise ValueError(f"file exceeds {max_bytes} bytes: {path}")
    finally:
        os.close(fd)
    return bytes(chunks).decode("utf-8")


def loads_strict_json(raw: str) -> Any:
    if not isinstance(raw, str):
        raise TypeError("JSON payload must be a string")
    _check_utf8_str(raw)
    if len(raw.encode("utf-8")) > MAX_FILE_BYTES:
        raise ValueError(f"JSON payload exceeds {MAX_FILE_BYTES} bytes")
    try:
        parsed = json.loads(
            raw,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
            parse_float=_parse_finite_float,
        )
    except RecursionError as exc:
        raise ValueError("JSON nesting depth exceeds maximum") from exc
    _validate_json_tree(parsed)
    return parsed


def load_strict_json(path: Path) -> Any:
    return loads_strict_json(read_regular_utf8(path))


def is_strict_int(value: Any) -> bool:
    return type(value) is int


def _has_safe_uri_segments(uri: str) -> bool:
    if any(
        ord(ch) < 0x20 or ord(ch) == 0x7F or ch.isspace() or ch in {"\\", "?", "#"}
        for ch in uri
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
    if any(not isinstance(key, str) for key in value):
        errors.append(f"{label}: object keys must be strings")
    str_keys = {key for key in value if isinstance(key, str)}
    for missing in sorted(required - str_keys):
        errors.append(f"{label}: missing required '{missing}'")
    for extra in sorted(str_keys - allowed):
        errors.append(f"{label}: unknown field '{extra}'")
    return value


def _has_lone_surrogate(value: str) -> bool:
    try:
        value.encode("utf-8")
        return False
    except UnicodeEncodeError:
        return True


def _is_safe_str(value: Any, lo: int, hi: int) -> bool:
    return isinstance(value, str) and lo <= len(value) <= hi and not _has_lone_surrogate(value)


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
                if _has_lone_surrogate(key):
                    errors.append("request.intent: lone UTF-16 surrogate in key is forbidden")
                    return
                stack.append((child, depth + 1))
        elif isinstance(current, list):
            for child in current:
                stack.append((child, depth + 1))
        elif current is None or isinstance(current, bool):
            continue
        elif isinstance(current, str):
            if _has_lone_surrogate(current):
                errors.append("request.intent: lone UTF-16 surrogate in string is forbidden")
                return
        elif type(current) is int:
            if not _is_finite_int(current):
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
            if not _is_safe_str(query, 1, 1000):
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
            if not _is_safe_str(mt, 3, 200):
                errors.append(f"response.results[{idx}].mediaType: invalid mediaType")
            dg = row.get("digest")
            if not isinstance(dg, str) or SHA256_RE.fullmatch(dg) is None:
                errors.append(f"response.results[{idx}].digest: invalid sha256 digest")
            if "summary" in row and not _is_safe_str(row["summary"], 0, 2000):
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
        if not _is_safe_str(route, 1, 200):
            errors.append("response.receipt.route: must be valid UTF-8 of 1..200 chars")
        model = rcpt.get("model")
        if model is not None and not _is_safe_str(model, 0, 200):
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
