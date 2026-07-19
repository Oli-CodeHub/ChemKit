#!/usr/bin/env python3
"""Check the local ChemKit OCSR plugin registry."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path("/Users/yl/Desktop/skills/ChemKit")
MANIFEST = ROOT / "plugins" / "manifest.json"
VENV_PYTHON = ROOT / "plugins" / ".venv-ocsr" / "bin" / "python"


def main() -> int:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    plugin_root = ROOT / "plugins"
    ok = True

    print(f"ChemKit OCSR plugins: {plugin_root}")
    for plugin in data["plugins"]:
        path = plugin_root / plugin["local_path"]
        present = path.exists() and any(path.iterdir())
        marker = "OK" if present else "MISSING"
        print(f"- {marker}: {plugin['name']} ({plugin['role']})")
        print(f"  path: {path}")
        print(f"  repo: {plugin['repo']}")
        if not present:
            ok = False

    venv = plugin_root / ".venv-ocsr"
    if venv.exists():
        print(f"- OK: Python venv present: {venv}")
        check_python_packages()
    else:
        print(f"- INFO: Python venv not present. Run install_ocsr_plugins.sh --install-python when ready.")

    return 0 if ok else 1


def check_python_packages() -> None:
    packages = [
        "decimer",
        "MolScribe",
        "RxnScribe",
        "torch",
        "rdkit",
        "tensorflow",
        "transformers",
        "easyocr",
    ]
    code = """
import importlib.metadata as md
packages = {packages!r}
for package in packages:
    try:
        print(f"  python-package OK: {{package}} {{md.version(package)}}")
    except Exception:
        print(f"  python-package MISSING: {{package}}")
""".format(packages=packages)
    try:
        proc = subprocess.run(
            [str(VENV_PYTHON), "-c", code],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        print(f"- INFO: venv Python missing: {VENV_PYTHON}")
        return
    sys.stdout.write(proc.stdout)
    if proc.stderr.strip():
        print("  python-package WARN: stderr emitted during metadata check")


if __name__ == "__main__":
    raise SystemExit(main())
