#!/usr/bin/env python3
"""Draw perillyl alcohol esterification with cyclobutanecarboxylic acid (Steglich)."""

from __future__ import annotations

from pathlib import Path
import sys

from rdkit import Chem
from rdkit.Chem import rdDepictor

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from chemkit_model import MoleculeCandidate
from chemkit_route_renderer import Arrow, Label, MolPlace, chemdraw_compact_style, render_route_svg, screenshot_svg, write_svg


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "examples"
SVG = OUT_DIR / "20260626-perillyl-alcohol-cyclobutanecarboxylic-acid-esterification.svg"
PNG = OUT_DIR / "20260626-perillyl-alcohol-cyclobutanecarboxylic-acid-esterification.png"

WIDTH = 1200
HEIGHT = 245


def candidate(key: str, smiles: str) -> MoleculeCandidate:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Could not parse SMILES for {key}: {smiles}")
    rdDepictor.Compute2DCoords(mol)
    return MoleculeCandidate(
        key=key,
        mol=mol,
        source_smiles=smiles,
        confidence=None,
        rdkit_status="sanitized",
    )


def main() -> None:
    candidates = {
        "perillyl_alcohol": candidate("perillyl_alcohol", "CC(=C)C1CCC(=CC1)CO"),
        "cyclobutanecarboxylic_acid": candidate(
            "cyclobutanecarboxylic_acid", "O=C(O)C1CCC1"
        ),
        "perillyl_cyclobutanecarboxylate": candidate(
            "perillyl_cyclobutanecarboxylate",
            "CC(=C)C1CCC(=CC1)COC(=O)C1CCC1",
        ),
    }

    places = [
        MolPlace("perillyl_alcohol", (130, 105), (220, 165), "perillyl alcohol", 205),
        MolPlace(
            "cyclobutanecarboxylic_acid",
            (460, 105),
            (160, 140),
            "cyclobutanecarboxylic acid",
            205,
        ),
        MolPlace(
            "perillyl_cyclobutanecarboxylate",
            (950, 105),
            (350, 175),
            "perillyl cyclobutanecarboxylate",
            205,
        ),
    ]
    arrows = [Arrow(580, 105, 770, 105)]
    labels = [
        Label(312, 111, "+", "cond", 22),
        Label(675, 81, "DCC, DMAP", "cond", 14),
        Label(675, 128, "DCM, rt, 2 h", "cond", 14),
    ]
    style = chemdraw_compact_style()

    svg = render_route_svg(candidates, places, arrows, labels, WIDTH, HEIGHT, style)
    write_svg(SVG, svg)
    screenshot_svg(SVG, PNG, WIDTH, HEIGHT)
    print(SVG)
    print(PNG)


if __name__ == "__main__":
    main()
