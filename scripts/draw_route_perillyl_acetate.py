#!/usr/bin/env python3
"""Draw perillyl alcohol esterification with acetic acid."""

from __future__ import annotations

from pathlib import Path
import sys

from rdkit import Chem
from rdkit.Chem import rdDepictor

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from chemkit_ocsr import OcsrCandidate
from chemkit_route_renderer import Arrow, Label, MolPlace, chemdraw_compact_style, render_route_svg, screenshot_svg, write_svg


ROOT = Path("/Users/yl/Desktop/skills/ChemKit")
OUT_DIR = ROOT / "examples"
SVG = OUT_DIR / "20260626-perillyl-alcohol-acetic-acid-esterification.svg"
PNG = OUT_DIR / "20260626-perillyl-alcohol-acetic-acid-esterification.png"

WIDTH = 900
HEIGHT = 245


def candidate(key: str, smiles: str) -> OcsrCandidate:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Could not parse SMILES for {key}: {smiles}")
    rdDepictor.Compute2DCoords(mol)
    return OcsrCandidate(
        key=key,
        mol=mol,
        source_smiles=smiles,
        confidence=None,
        rdkit_status="sanitized",
    )


def main() -> None:
    candidates = {
        "perillyl_alcohol": candidate("perillyl_alcohol", "CC(=C)C1CCC(=CC1)CO"),
        "acetic_acid": candidate("acetic_acid", "CC(=O)O"),
        "perillyl_acetate": candidate("perillyl_acetate", "CC(=C)C1CCC(=CC1)COC(=O)C"),
    }

    places = [
        MolPlace("perillyl_alcohol", (140, 105), (225, 165), "perillyl alcohol", 205),
        MolPlace("acetic_acid", (350, 105), (135, 125), "AcOH", 205),
        MolPlace("perillyl_acetate", (745, 105), (265, 170), "perillyl acetate", 205),
    ]
    arrows = [Arrow(455, 105, 625, 105)]
    labels = [
        Label(260, 111, "+", "cond", 22),
        Label(540, 81, "DCC, DMAP", "cond", 14),
        Label(540, 128, "CH₂Cl₂, 0 °C", "cond", 14),
    ]
    style = chemdraw_compact_style()

    svg = render_route_svg(candidates, places, arrows, labels, WIDTH, HEIGHT, style)
    write_svg(SVG, svg)
    screenshot_svg(SVG, PNG, WIDTH, HEIGHT)
    print(SVG)
    print(PNG)


if __name__ == "__main__":
    main()
