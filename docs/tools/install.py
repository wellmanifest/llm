#!/usr/bin/env python3
"""Install a Subactor-first profile and host adapter without overwriting files."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

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
START = "<!-- SUBACTOR-FIRST:START wellmanifest/llm v1 -->"
END = "<!-- SUBACTOR-FIRST:END wellmanifest/llm v1 -->"
HOSTS = {
    "codex": ("AGENTS.md", "AGENTS.md"),
    "claude": ("CLAUDE.md", "CLAUDE.md"),
    "gemini": ("GEMINI.md", "GEMINI.md"),
    "cursor": ("subactor-first.mdc", ".cursor/rules/subactor-first.mdc"),
    "copilot": ("copilot-instructions.md", ".github/copilot-instructions.md"),
    "generic": ("SUBACTOR.md", "SUBACTOR.md"),
}


def inside_target(target: Path, destination: Path) -> bool:
    try:
        destination.resolve(strict=False).relative_to(target)
        return True
    except ValueError:
        return False


def atomic_write(path: Path, content: str, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_temp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp = Path(raw_temp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        if mode is not None:
            os.chmod(temp, mode)
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def marked_block(text: str) -> str | None:
    if START not in text and END not in text:
        return None
    if text.count(START) != 1 or text.count(END) != 1:
        raise ValueError("malformed SUBACTOR-FIRST marker pair")
    return text.split(START, 1)[1].split(END, 1)[0].strip()


def plan_adapter(target: Path, host: str, apply: bool) -> str:
    source_name, target_name = HOSTS[host]
    source = (ADAPTER_ROOT / source_name).read_text(encoding="utf-8")
    destination = target / target_name
    if not inside_target(target, destination):
        raise ValueError(f"{host}: target escapes repository")
    if destination.is_symlink():
        raise ValueError(f"{host}: refusing symlink target {destination}")
    source_block = marked_block(source)
    if source_block is None:
        raise ValueError(f"{host}: source adapter has no marker")

    if destination.exists():
        existing = destination.read_text(encoding="utf-8")
        existing_block = marked_block(existing)
        if existing_block == source_block:
            return f"UNCHANGED {host} {destination}"
        if existing_block is not None:
            raise ValueError(f"{host}: existing marked block differs in {destination}")
        content = (
            existing.rstrip() + "\n\n" + source[source.index(START) :].strip() + "\n"
        )
        action = "APPEND"
        mode = destination.stat().st_mode
    else:
        content = source if source.endswith("\n") else source + "\n"
        action = "CREATE"
        mode = None
    if apply:
        atomic_write(destination, content, mode)
    return f"{action if apply else 'WOULD-' + action} {host} {destination}"


def plan_document(target: Path, name: str, apply: bool, replace: bool) -> str:
    source_path, target_path = DOCUMENTS[name]
    source = source_path.read_text(encoding="utf-8")
    destination = target / target_path
    if not inside_target(target, destination):
        raise ValueError(f"{name} target escapes repository")
    if destination.is_symlink():
        raise ValueError(f"refusing symlink target {destination}")
    if destination.exists():
        existing = destination.read_text(encoding="utf-8")
        if existing == source:
            return f"UNCHANGED {name} {destination}"
        if not replace:
            raise ValueError(
                f"{name} differs at {destination}; review and pass --replace-profile"
            )
        action = "REPLACE"
        mode = destination.stat().st_mode
    else:
        action = "CREATE"
        mode = None
    if apply:
        atomic_write(destination, source, mode)
    return f"{action if apply else 'WOULD-' + action} {name} {destination}"


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
    target = args.target.resolve()
    if not target.is_dir():
        parser.error(f"target is not a directory: {target}")
    hosts = list(HOSTS) if args.host == "all" else [args.host]
    try:
        for name in DOCUMENTS:
            print(plan_document(target, name, args.apply, args.replace_profile))
        for host in hosts:
            print(plan_adapter(target, host, args.apply))
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"REFUSED {exc}", file=sys.stderr)
        return 1
    print("APPLIED" if args.apply else "DRY-RUN; pass --apply to write")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
