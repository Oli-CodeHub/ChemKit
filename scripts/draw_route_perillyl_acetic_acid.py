#!/usr/bin/env python3
"""Draw the direct esterification of perillyl alcohol with acetic acid."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import rdDepictor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from chemkit_model import MoleculeCandidate
from chemkit_route_renderer import (
    Arrow,
    Label,
    MolPlace,
    chemdraw_compact_style,
    condition_labels_for_arrow,
    render_route_svg,
    screenshot_svg,
    tighten_route_svg,
    write_svg,
)


SMILES = {
    "perillyl_alcohol": "CC(=C)C1CCC(=CC1)CO",
    "acetic_acid": "CC(=O)O",
    "perillyl_acetate": "CC(=C)C1CCC(=CC1)COC(=O)C",
}

OUT_DIR = ROOT / "examples"
SVG = OUT_DIR / "20260820-perillyl-alcohol-acetic-acid-route.svg"
PNG = OUT_DIR / "20260820-perillyl-alcohol-acetic-acid-route.png"
MANIFEST = OUT_DIR / "20260820-perillyl-alcohol-acetic-acid-route.json"


def candidate(key: str, smiles: str) -> MoleculeCandidate:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Could not parse SMILES for {key}: {smiles}")
    rdDepictor.Compute2DCoords(mol)
    return MoleculeCandidate(key, mol, smiles, 1.0, "sanitized", [], 0)


def main() -> None:
    candidates = {key: candidate(key, smiles) for key, smiles in SMILES.items()}
    places = [
        MolPlace("perillyl_alcohol", (180, 220), (0, 0), "perillyl alcohol", 365),
        MolPlace("acetic_acid", (500, 220), (0, 0), "acetic acid", 365),
        MolPlace("perillyl_acetate", (1080, 220), (0, 0), "perillyl acetate", 365),
    ]
    arrows = [Arrow(670, 220, 900, 220)]
    style = chemdraw_compact_style()
    labels = [
        Label(340, 235, "+", "cond", 34),
        *condition_labels_for_arrow(
            arrows[0],
            above="DCC, DMAP",
            below="CH₂Cl₂, r.t.",
            style=style,
        ),
    ]

    svg = render_route_svg(candidates, places, arrows, labels, 1500, 520, style)
    svg, crop = tighten_route_svg(svg, padding=44.0)
    write_svg(SVG, svg)
    screenshot_svg(SVG, PNG, crop[2], crop[3])
    MANIFEST.write_text(
        json.dumps(
            {
                "mode": "explicit-smiles-route",
                "source_image_embedded": False,
                "structures": {
                    "perillyl_alcohol": {
                        "name_zh": "紫苏醇",
                        "smiles": SMILES["perillyl_alcohol"],
                    },
                    "acetic_acid": {
                        "name_zh": "乙酸",
                        "smiles": SMILES["acetic_acid"],
                    },
                    "perillyl_acetate": {
                        "name_zh": "乙酸紫苏酯",
                        "smiles": SMILES["perillyl_acetate"],
                    },
                },
                "reaction": {
                    "from": ["perillyl_alcohol", "acetic_acid"],
                    "to": "perillyl_acetate",
                    "conditions": ["DCC, DMAP", "CH₂Cl₂, r.t."],
                    "assumption": "Direct esterification conditions reused from the existing perillyl ester example; replace if a different protocol is intended.",
                },
                "tight_crop": {
                    "x": crop[0],
                    "y": crop[1],
                    "width": crop[2],
                    "height": crop[3],
                },
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
    print(MANIFEST)


if __name__ == "__main__":
    main()
