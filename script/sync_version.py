#!/usr/bin/env python3
"""Synchronize project and integration versions.

Usage:
  python3 script/sync_version.py [version]

If ``version`` is omitted, the script reads the version from
``pyproject.toml`` and propagates it to the integration files.
If ``version`` is provided, the script first updates ``pyproject.toml``
and then syncs the same value to the integration files.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import tomllib

root = Path(__file__).resolve().parent.parent
pyproject_path = root / "pyproject.toml"
const_path = root / "custom_components" / "tapo" / "const.py"
manifest_path = root / "custom_components" / "tapo" / "manifest.json"


def replace_or_fail(path: Path, pattern: str, replacement: str) -> None:
    text = path.read_text()
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise SystemExit(f"Unable to update version in {path}")
    path.write_text(updated)


def read_pyproject_version() -> str:
    with pyproject_path.open("rb") as file:
        return tomllib.load(file)["project"]["version"]


def write_pyproject_version(version: str) -> None:
    replace_or_fail(
        pyproject_path,
        r'^version = "[^"]+"$',
        f'version = "{version}"',
    )


def write_const_version(version: str) -> None:
    replace_or_fail(
        const_path,
        r'^VERSION = "[^"]+"$',
        f'VERSION = "{version}"',
    )


def write_manifest_version(version: str) -> None:
    data = json.loads(manifest_path.read_text())
    data["version"] = version
    manifest_path.write_text(json.dumps(data, indent=2) + "\n")


def main() -> None:
    version = sys.argv[1] if len(sys.argv) > 1 else read_pyproject_version()

    if len(sys.argv) > 1:
        write_pyproject_version(version)

    write_const_version(version)
    write_manifest_version(version)

    print(f"Synced pyproject.toml, const.py and manifest.json -> {version}")


if __name__ == "__main__":
    main()
