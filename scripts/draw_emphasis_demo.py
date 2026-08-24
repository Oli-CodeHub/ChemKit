#!/usr/bin/env python3
"""Render a small route demonstrating semantic functional-group emphasis."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import rdDepictor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from chemkit_emphasis import emphasis_report, resolve_route_emphasis
from chemkit_model import MoleculeCandidate
from chemkit_route_renderer import (
    Arrow,
    Label,
    MolPlace,
    chemdraw_compact_style,
    render_route_svg,
    screenshot_svg,
    tighten_route_svg,
    write_svg,
)


SMILES = {
    "3w": "O=C(c1c[nH]c2ccccc12)Sc1nccnc1",
    "2": "CC(C)(C)OC(=O)CCn1c(C(=O)Sc2nccnc2)c2ccccc2c1",
}
SVG = ROOT / "examples/20260820-emphasis-demo.svg"
PNG = ROOT / "examples/20260820-emphasis-demo.png"
JSON_OUT = ROOT / "examples/20260820-emphasis-demo.json"


def candidate(key: str, smiles: str) -> MoleculeCandidate:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid demo SMILES: {key}")
    rdDepictor.Compute2DCoords(mol)
    return MoleculeCandidate(key, mol, smiles, 1.0, "sanitized", [], 0)


def main() -> None:
    candidates = {key: candidate(key, smiles) for key, smiles in SMILES.items()}
    # This is the form an Agent can create from: "highlight the thioester in
    # 3w and 2 in red and make it thicker".
    requests = [
        {
            "molecules": ["3w", "2"],
            "selector": {"type": "functional_group", "value": "thioester"},
            "mode": "bond",
            "color": "red",
            "bond_width_multiplier": 2.0,
            "label": "thioester",
        }
    ]
    emphasis = resolve_route_emphasis(candidates, requests)
    places = [
        MolPlace("3w", (280, 270), (0, 0), "3w", 500),
        MolPlace("2", (980, 270), (0, 0), "2", 500),
    ]
    arrows = [Arrow(500, 270, 760, 270)]
    labels = [Label(630, 240, "highlighted thioester", "cond", 25)]
    svg = render_route_svg(
        candidates,
        places,
        arrows,
        labels,
        1400,
        650,
        chemdraw_compact_style(),
        emphasis=emphasis,
    )
    svg, crop = tighten_route_svg(svg, padding=42.0)
    write_svg(SVG, svg)
    screenshot_svg(SVG, PNG, crop[2], crop[3])
    JSON_OUT.write_text(
        json.dumps(
            {
                "requests": requests,
                "resolved_emphasis": emphasis_report(emphasis),
                "tight_crop": {"x": crop[0], "y": crop[1], "width": crop[2], "height": crop[3]},
                "outputs": {"svg": str(SVG), "png": str(PNG)},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(SVG)
    print(PNG)
    print(JSON_OUT)


if __name__ == "__main__":
    main()
