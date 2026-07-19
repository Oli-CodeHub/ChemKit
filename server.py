#!/usr/bin/env python3
"""ChemKit local web backend."""

from __future__ import annotations

import base64
import sys
import traceback
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from rdkit import Chem
from rdkit.Chem import rdDepictor
from werkzeug.exceptions import HTTPException


ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"
WEB = ROOT / "web"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from chemkit_agent_parser import parse_reaction_text, parser_status
from chemkit_ocsr import OcsrCandidate
from chemkit_route_renderer import Arrow, Label, MolPlace, chemdraw_compact_style, render_route_svg


app = Flask(__name__, static_folder=str(WEB), static_url_path="")


def candidate_from_structure(structure: dict) -> OcsrCandidate:
    mol = Chem.MolFromSmiles(structure["smiles"])
    if mol is None:
        raise ValueError(f"Could not parse SMILES for {structure['name']}: {structure['smiles']}")
    rdDepictor.Compute2DCoords(mol)
    return OcsrCandidate(
        key=structure["id"],
        mol=mol,
        source_smiles=structure["smiles"],
        confidence=None,
        rdkit_status="sanitized",
    )


def layout_single_step(spec: dict) -> tuple[list[MolPlace], list[Arrow], list[Label], int, int]:
    reactants = spec["reactants"]
    products = spec["products"]
    width = 900
    height = 245
    baseline_y = 105
    label_y = 205

    places: list[MolPlace] = []
    if len(reactants) == 1:
        places.append(MolPlace(reactants[0]["id"], (180, baseline_y), (245, 170), reactants[0]["name"], label_y))
        arrow_start = 390
        plus_labels: list[Label] = []
    else:
        places.append(MolPlace(reactants[0]["id"], (140, baseline_y), (225, 165), reactants[0]["name"], label_y))
        places.append(MolPlace(reactants[1]["id"], (350, baseline_y), (135, 125), display_label(reactants[1]), label_y))
        arrow_start = 455
        plus_labels = [Label(260, baseline_y + 6, "+", "cond", 22)]

    places.append(MolPlace(products[0]["id"], (745, baseline_y), (265, 170), products[0]["name"], label_y))

    above = spec.get("conditions", {}).get("above", [])
    below = spec.get("conditions", {}).get("below", [])
    yield_text = spec.get("conditions", {}).get("yield", "")
    longest = max([len(line) for line in [*above, *below, yield_text] if line] or [8])
    arrow_len = max(170, min(245, longest * 10 + 70))
    arrow_center = 540
    arrow = Arrow(arrow_center - arrow_len / 2, baseline_y, arrow_center + arrow_len / 2, baseline_y)

    labels = plus_labels
    for idx, line in enumerate(above):
        labels.append(Label(arrow_center, baseline_y - 24 + idx * 14, line, "cond", 14))
    for idx, line in enumerate(below):
        labels.append(Label(arrow_center, baseline_y + 23 + idx * 14, line, "cond", 14))
    if yield_text:
        labels.append(Label(arrow_center, baseline_y + 43 + len(below) * 14, yield_text, "yield", 13))
    return places, [arrow], labels, width, height


def display_label(structure: dict) -> str:
    if structure["name"] == "acetic acid":
        return "AcOH"
    return structure["name"]


def render_spec(spec: dict) -> str:
    structures = [*spec["reactants"], *spec["products"]]
    candidates = {item["id"]: candidate_from_structure(item) for item in structures}
    places, arrows, labels, width, height = layout_single_step(spec)
    return render_route_svg(
        candidates=candidates,
        places=places,
        arrows=arrows,
        labels=labels,
        width=width,
        height=height,
        style=chemdraw_compact_style(),
    )


@app.get("/")
def index():
    return send_from_directory(WEB, "index.html")


@app.get("/examples/<path:filename>")
def examples(filename: str):
    return send_from_directory(ROOT / "examples", filename)


@app.get("/api/status")
def status():
    return jsonify({"ok": True, "parser": parser_status(), "rdkit": Chem.rdBase.rdkitVersion})


@app.post("/api/draft")
def draft():
    payload = request.get_json(force=True)
    text = payload.get("text", "")
    parsed = parse_reaction_text(text)
    if not parsed["ok"]:
        return jsonify(parsed)

    spec = parsed["spec"]
    svg = render_spec(spec)
    return jsonify(
        {
            "ok": True,
            "spec": spec,
            "svg": svg,
            "svg_data_url": "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii"),
            "questions": parsed["questions"],
            "warnings": parsed["warnings"],
            "parser_mode": parsed.get("parser_mode", "unknown"),
            "qc": [
                {"level": "good", "title": item["name"], "message": f"{item['source']} · SMILES verified"}
                for item in [*spec["reactants"], *spec["products"]]
            ],
        }
    )


@app.post("/api/render")
def render():
    try:
        spec = request.get_json(force=True)["spec"]
        svg = render_spec(spec)
        return jsonify({"ok": True, "svg": svg})
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.errorhandler(Exception)
def handle_error(exc: Exception):
    if isinstance(exc, HTTPException):
        return exc
    traceback.print_exc()
    return jsonify({"ok": False, "error": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8765, debug=False)
