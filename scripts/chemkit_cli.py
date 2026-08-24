#!/usr/bin/env python3
"""Small, deterministic command-line boundary for Agent ChemKit workflows."""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def resolve_repo_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def command_check() -> int:
    print(f"ChemKit {VERSION}")
    print(f"Python {platform.python_version()} ({sys.executable})")
    try:
        import PIL  # noqa: F401
        from rdkit import Chem

        print(f"RDKit {Chem.rdBase.rdkitVersion}")
        print("Pillow: available")
    except ImportError as exc:
        print(f"Dependency missing: {exc}", file=sys.stderr)
        print("Install with: python -m pip install -r requirements.txt", file=sys.stderr)
        return 2
    return 0


def command_run(script: str, script_args: list[str]) -> int:
    path = resolve_repo_path(script)
    if not path.is_file() or path.suffix != ".py":
        print(f"Route script not found: {path}", file=sys.stderr)
        return 2
    completed = subprocess.run([sys.executable, str(path), *script_args], cwd=ROOT)
    return completed.returncode


def open_with_default_app(path: Path) -> bool:
    uri = path.resolve().as_uri()
    if path.suffix.lower() == ".svg":
        return bool(webbrowser.open(uri, new=2))
    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
        return True
    command = "open" if sys.platform == "darwin" else "xdg-open"
    try:
        subprocess.Popen([command, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return bool(webbrowser.open(uri, new=2))
    return True


def command_preview(value: str) -> int:
    path = resolve_repo_path(value)
    if not path.is_file():
        print(f"Preview file not found: {path}", file=sys.stderr)
        return 2
    if not open_with_default_app(path):
        print(f"Could not open a default browser/viewer for {path}", file=sys.stderr)
        return 1
    print(f"Opened preview: {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="chemkit", description="Agent-facing ChemKit commands")
    parser.add_argument("--version", action="version", version=f"ChemKit {VERSION}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check", help="check Python, RDKit, and Pillow")
    run_parser = subparsers.add_parser("run", help="run a repository-relative route script")
    run_parser.add_argument("script", help="path to a Python route script")
    run_parser.add_argument("script_args", nargs=argparse.REMAINDER)
    preview_parser = subparsers.add_parser("preview", help="open an SVG/PDF/PNG with the default app")
    preview_parser.add_argument("path", help="repository-relative output path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "check":
        return command_check()
    if args.command == "run":
        return command_run(args.script, args.script_args)
    if args.command == "preview":
        return command_preview(args.path)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
