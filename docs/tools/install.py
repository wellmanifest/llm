#!/usr/bin/env python3
"""Install a Subactor-first profile and host adapter without overwriting files."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

_TOOLS_DIR = str(Path(__file__).resolve().parent)
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

from schema_validators import (  # noqa: E402
    END,
    START,
    extract_marked_block,
    extract_marked_span,
    read_regular_utf8,
)

ROOT = Path(__file__).resolve().parents[2]
ADAPTER_ROOT = ROOT / "docs" / "adapters"
DOCUMENTS = {
    "profile": (
        ROOT / "models" / "subactor-first.v1.json",
        Path(".wellmanifest/llm.json"),
    ),
    "profile-schema": (
        ROOT / "models" / "llm-profile.schema.json",
        Path(".wellmanifest/llm-profile.schema.json"),
    ),
    "request-schema": (
        ROOT / "models" / "request.schema.json",
        Path(".wellmanifest/request.schema.json"),
    ),
    "response-schema": (
        ROOT / "models" / "response.schema.json",
        Path(".wellmanifest/response.schema.json"),
    ),
}
HOSTS = {
    "codex": ("AGENTS.md", "AGENTS.md"),
    "claude": ("CLAUDE.md", "CLAUDE.md"),
    "gemini": ("GEMINI.md", "GEMINI.md"),
    "cursor": ("subactor-first.mdc", ".cursor/rules/subactor-first.mdc"),
    "copilot": ("copilot-instructions.md", ".github/copilot-instructions.md"),
    "generic": ("SUBACTOR.md", "SUBACTOR.md"),
}

__all__ = [
    "DOCUMENTS",
    "END",
    "HOSTS",
    "PlannedWrite",
    "START",
    "atomic_write",
    "inside_target",
    "main",
    "marked_block",
    "plan_adapter",
    "plan_document",
]


@dataclass(frozen=True)
class PlannedWrite:
    action: str
    subject: str
    destination: Path
    content: str | None = None
    mode: int | None = None

    def render(self, apply: bool) -> str:
        if self.action == "UNCHANGED":
            return f"UNCHANGED {self.subject} {self.destination}"
        prefix = self.action if apply else f"WOULD-{self.action}"
        return f"{prefix} {self.subject} {self.destination}"


def inside_target(target: Path, destination: Path) -> bool:
    try:
        rel = destination.relative_to(target)
    except ValueError:
        return False
    current = target
    for part in rel.parts[:-1]:
        current = current / part
        if current.is_symlink():
            return False
    try:
        destination.resolve(strict=False).relative_to(target)
        return True
    except ValueError:
        return False


def _validate_destination(target: Path, destination: Path, label: str) -> None:
    if not inside_target(target, destination):
        raise ValueError(f"{label}: target escapes repository or traverses symlink")
    if destination.is_symlink():
        raise ValueError(f"{label}: refusing symlink target {destination}")
    if destination.exists() and not destination.is_file():
        raise ValueError(f"{label}: refusing non-regular target {destination}")


def atomic_write(path: Path, content: str, mode: int | None = None) -> None:
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError(f"refusing symlink path during atomic write: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_temp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp = Path(raw_temp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        if mode is not None:
            os.chmod(temp, mode)
        if path.is_symlink():
            raise ValueError(f"refusing symlink target during atomic write: {path}")
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def marked_block(text: str) -> str | None:
    block, err = extract_marked_block(text)
    if err is not None:
        raise ValueError(err)
    return block


def build_adapter_plan(target: Path, host: str) -> PlannedWrite:
    source_name, target_name = HOSTS[host]
    source = read_regular_utf8(ADAPTER_ROOT / source_name)
    destination = target / target_name
    _validate_destination(target, destination, host)
    source_block = marked_block(source)
    if source_block is None:
        raise ValueError(f"{host}: source adapter has no marker")
    marker_span = extract_marked_span(source)

    if destination.exists():
        existing = read_regular_utf8(destination)
        existing_block = marked_block(existing)
        if existing_block == source_block:
            return PlannedWrite("UNCHANGED", host, destination)
        if existing_block is not None:
            raise ValueError(f"{host}: existing marked block differs in {destination}")
        stripped = existing.rstrip()
        content = (f"{stripped}\n\n{marker_span}\n") if stripped else f"{marker_span}\n"
        return PlannedWrite("APPEND", host, destination, content, destination.stat().st_mode)

    content = source if source.endswith("\n") else source + "\n"
    return PlannedWrite("CREATE", host, destination, content, None)


def build_document_plan(target: Path, name: str, replace: bool) -> PlannedWrite:
    source_path, target_path = DOCUMENTS[name]
    source = read_regular_utf8(source_path)
    destination = target / target_path
    _validate_destination(target, destination, name)
    if destination.exists():
        existing = read_regular_utf8(destination)
        if existing == source:
            return PlannedWrite("UNCHANGED", name, destination)
        if not replace:
            raise ValueError(
                f"{name} differs at {destination}; review and pass --replace-profile"
            )
        return PlannedWrite("REPLACE", name, destination, source, destination.stat().st_mode)
    return PlannedWrite("CREATE", name, destination, source, None)


def plan_adapter(target: Path, host: str, apply: bool) -> str:
    planned = build_adapter_plan(target, host)
    if apply and planned.content is not None:
        atomic_write(planned.destination, planned.content, planned.mode)
    return planned.render(apply)


def plan_document(target: Path, name: str, apply: bool, replace: bool) -> str:
    planned = build_document_plan(target, name, replace)
    if apply and planned.content is not None:
        atomic_write(planned.destination, planned.content, planned.mode)
    return planned.render(apply)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, choices=[*HOSTS, "all"])
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument(
        "--apply", action="store_true", help="perform writes; default is dry-run"
    )
    parser.add_argument(
        "--replace-profile",
        action="store_true",
        help="replace a reviewed differing profile; requires --apply",
    )
    args = parser.parse_args(argv)
    if args.replace_profile and not args.apply:
        parser.error("--replace-profile requires --apply")
    if args.target.is_symlink():
        print(f"REFUSED target must not be a symlink: {args.target}", file=sys.stderr)
        return 1
    target = args.target.resolve()
    if not target.is_dir():
        parser.error(f"target is not a directory: {target}")
    hosts = list(HOSTS) if args.host == "all" else [args.host]
    try:
        plans: list[PlannedWrite] = [
            build_document_plan(target, name, args.replace_profile) for name in DOCUMENTS
        ]
        plans.extend(build_adapter_plan(target, host) for host in hosts)
        for item in plans:
            if args.apply and item.content is not None:
                atomic_write(item.destination, item.content, item.mode)
            print(item.render(args.apply))
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"REFUSED {exc}", file=sys.stderr)
        return 1
    print("APPLIED" if args.apply else "DRY-RUN; pass --apply to write")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
