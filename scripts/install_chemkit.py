#!/usr/bin/env python3
"""Install ChemKit as an isolated Agent skill."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "chemkit"
EXCLUDED_NAMES = {
    ".git",
    ".venv",
    "venv",
    "dist",
    "__pycache__",
    ".pytest_cache",
    "outputs",
    "social",
}
EXCLUDED_RELATIVE_PREFIXES = (Path("plugins") / "sources", Path("plugins") / "outputs")
EXCLUDED_RELATIVE_FILES = {
    Path("references") / "ocsr-pipeline.md",
    Path("references") / "phase-notes.md",
    Path("scripts") / "LEGACY.md",
}
EXCLUDED_SCRIPT_FILES = {
    "chemkit_ocsr.py",
    "check_ocsr_plugins.py",
    "install_ocsr_plugins.sh",
    "ocsr_qc_report.py",
    "draw_individual_ocsr_grid.py",
    "draw_route_ocsr_molvec.py",
    "predict_taxol_molscribe.py",
    "draw_taxol_route_from_molscribe.py",
    "draw_taxol_route_from_molscribe_rdkit.py",
    "draw_taxol_route_from_molscribe_v2.py",
    "draw_taxol_route_from_molscribe_v3_clean.py",
}


def default_skills_dir() -> Path:
    explicit = os.environ.get("CODEX_SKILLS_DIR")
    if explicit:
        return Path(explicit).expanduser()
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "skills"
    return Path.home() / ".codex" / "skills"


def should_ignore(relative: Path) -> bool:
    if any(part in EXCLUDED_NAMES for part in relative.parts):
        return True
    if relative in EXCLUDED_RELATIVE_FILES:
        return True
    if relative.parent == Path("scripts") and relative.name in EXCLUDED_SCRIPT_FILES:
        return True
    return any(relative == prefix or prefix in relative.parents for prefix in EXCLUDED_RELATIVE_PREFIXES)


def copy_skill(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for source in SOURCE_ROOT.rglob("*"):
        relative = source.relative_to(SOURCE_ROOT)
        if should_ignore(relative):
            continue
        target = destination / relative
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def install_dependencies(destination: Path, python: Path) -> None:
    requirements = destination / "requirements.txt"
    subprocess.run([str(python), "-m", "pip", "install", "--upgrade", "pip"], check=True)
    subprocess.run([str(python), "-m", "pip", "install", "-r", str(requirements)], check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install ChemKit as an Agent skill")
    parser.add_argument("--target", type=Path, help="skills directory; the skill is installed as <target>/chemkit")
    parser.add_argument("--skip-deps", action="store_true", help="copy files without creating a virtual environment")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    skills_dir = (args.target or default_skills_dir()).expanduser().resolve()
    destination = skills_dir / SKILL_NAME
    if destination != SOURCE_ROOT:
        copy_skill(destination)
    else:
        destination.mkdir(parents=True, exist_ok=True)

    if args.skip_deps:
        print(f"Installed ChemKit skill files: {destination}")
        return 0

    venv_dir = destination / ".venv"
    python = venv_python(venv_dir)
    if not python.exists():
        print(f"Creating isolated environment: {venv_dir}")
        venv.EnvBuilder(with_pip=True, clear=False, symlinks=False).create(venv_dir)
    try:
        install_dependencies(destination, python)
    except subprocess.CalledProcessError as exc:
        print(
            "ChemKit files were installed, but dependency installation failed. "
            f"Retry with {python} -m pip install -r {destination / 'requirements.txt'}.",
            file=sys.stderr,
        )
        return exc.returncode or 1

    print(f"Installed ChemKit 1.0: {destination}")
    command = "chemkit.cmd" if os.name == "nt" else "chemkit"
    print(f"Run: {destination / 'bin' / command} check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
