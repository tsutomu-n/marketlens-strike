#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

from sis.cli import app


REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md"
COMMAND_BULLET_RE = re.compile(r"^- `([^`]+)`$", re.MULTILINE)


def _registered_command_names() -> set[str]:
    command_names = {command.name for command in app.registered_commands if command.name}
    command_names.update(group.name for group in app.registered_groups if group.name)
    return command_names


def _catalog_command_names() -> set[str]:
    text = CATALOG_PATH.read_text(encoding="utf-8")
    if "## Public CLI Command Catalog" not in text:
        msg = f"{CATALOG_PATH.relative_to(REPO_ROOT)} missing Public CLI Command Catalog heading"
        raise SystemExit(msg)
    return set(COMMAND_BULLET_RE.findall(text))


def check_cli_catalog() -> list[str]:
    registered = _registered_command_names()
    documented = _catalog_command_names()
    errors: list[str] = []

    missing = sorted(registered - documented)
    if missing:
        errors.append("catalog missing registered commands: " + ", ".join(missing))

    stale = sorted(documented - registered)
    if stale:
        errors.append("catalog contains stale commands: " + ", ".join(stale))

    if not documented:
        errors.append("catalog has no command bullets")

    return errors


def main() -> None:
    errors = check_cli_catalog()
    if errors:
        for error in errors:
            print(error)
        raise SystemExit(1)

    print(f"checked {len(_catalog_command_names())} public CLI commands against Typer registration")


if __name__ == "__main__":
    main()
