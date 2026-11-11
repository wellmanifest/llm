"""Shared regular-file I/O, symlink guards, and strict JSON parsing for wellmanifest/llm."""

from __future__ import annotations

import json
import math
import os
import stat
import tempfile
from pathlib import Path
from typing import Any

MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_JSON_DEPTH = 64
MAX_INT_DIGITS = 309

__all__ = [
    "DuplicateKeyError",
    "MAX_FILE_BYTES",
    "MAX_INT_DIGITS",
    "MAX_JSON_DEPTH",
    "atomic_write",
    "has_control_chars",
    "has_lone_surrogate",
    "has_symlink_ancestor",
    "is_finite_int",
    "load_strict_json",
    "loads_strict_json",
    "read_regular_utf8",
]


class DuplicateKeyError(ValueError):
    """Raised when a JSON object contains duplicate keys."""


def has_lone_surrogate(value: str) -> bool:
    try:
        value.encode("utf-8")
        return False
    except UnicodeEncodeError:
        return True


def has_control_chars(value: str, *, allow_newlines: bool = False) -> bool:
    for ch in value:
        code = ord(ch)
        if code == 0x7F:
            return True
        if code < 0x20:
            if allow_newlines and ch in {"\n", "\t"}:
                continue
            return True
    return False


def is_finite_int(value: int) -> bool:
    try:
        return math.isfinite(float(value))
    except OverflowError:
        return False


def _check_utf8_str(value: str) -> None:
    if has_lone_surrogate(value):
        raise ValueError("lone UTF-16 surrogate in JSON string is forbidden")


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


def _parse_bounded_int(token: str) -> int:
    digits = token[1:] if token.startswith("-") else token
    if len(digits) > MAX_INT_DIGITS:
        raise ValueError("JSON integer magnitude exceeds finite range")
    parsed = int(token)
    if not is_finite_int(parsed):
        raise ValueError("JSON integer magnitude exceeds finite range")
    return parsed


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
            if not is_finite_int(current):
                raise ValueError("JSON integer magnitude exceeds finite range")
        elif isinstance(current, float) and not math.isfinite(current):
            raise ValueError("non-finite float value is forbidden")


def has_symlink_ancestor(path: Path, *, include_self: bool = False) -> bool:
    if include_self and path.is_symlink():
        return True
    parts = path.parts if include_self else path.parts[:-1]
    if not path.is_absolute():
        cur = Path()
        for part in parts:
            cur = cur / part
            if cur.is_symlink():
                return True
        cwd = Path.cwd()
        for anc in (cwd, *cwd.parents):
            if len(anc.parts) <= 2:
                break
            if anc.is_symlink():
                return True
        return False
    if not parts:
        return False
    cur = Path(parts[0])
    for idx, part in enumerate(parts[1:], start=2):
        cur = cur / part
        if idx <= 2 and not (include_self and idx == len(parts)):
            continue
        if cur.is_symlink():
            return True
    return False


def read_regular_utf8(path: Path, max_bytes: int = MAX_FILE_BYTES) -> str:
    if type(max_bytes) is not int or max_bytes < 1:
        raise ValueError("max_bytes must be a positive integer")
    if has_symlink_ancestor(path, include_self=False):
        raise OSError(f"refusing symlink ancestor: {path}")
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
            parse_int=_parse_bounded_int,
        )
    except RecursionError as exc:
        raise ValueError("JSON nesting depth exceeds maximum") from exc
    _validate_json_tree(parsed)
    return parsed


def load_strict_json(path: Path) -> Any:
    return loads_strict_json(read_regular_utf8(path))


def atomic_write(path: Path, content: str, mode: int | None = None) -> None:
    if not isinstance(content, str):
        raise TypeError("atomic_write content must be a string")
    try:
        encoded = content.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("lone UTF-16 surrogate in content is forbidden") from exc
    if len(encoded) > MAX_FILE_BYTES:
        raise ValueError("content exceeds maximum size")
    if has_symlink_ancestor(path, include_self=True):
        raise ValueError(f"refusing symlink path during atomic write: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    if has_symlink_ancestor(path, include_self=True):
        raise ValueError(f"refusing symlink path during atomic write: {path}")
    fd, raw_temp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp = Path(raw_temp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        if mode is not None:
            os.chmod(temp, mode)
        if has_symlink_ancestor(path, include_self=True):
            raise ValueError(f"refusing symlink target during atomic write: {path}")
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()
