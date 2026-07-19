#!/usr/bin/env python3
"""Draw 3-hydroxyoxetane-3-carboxylic acid + 3-aminobenzonitrile -> amide
(HATU / DIPEA / DMF, 40 °C, 16 h).

Layout: reactant + reactant -> amide product. No structure labels (the source
figure's FAT-1a / FAT-2a / FAT-3a numbering has been removed on request).
"""

from __future__ import annotations

from pathlib import Path
import sys

from rdkit import Chem
from rdkit.Chem import rdDepictor

SCRIPT_DIR = Path("/Users/yl/Desktop/skills/ChemKit/scripts")
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from chemkit_ocsr import OcsrCandidate
from chemkit_route_renderer import (
    Arrow,
    Label,
    MolPlace,
    RouteStyle,
    render_route_svg,
    screenshot_svg,
    write_svg,
)


ROOT = Path("/Users/yl/Desktop/skills/ChemKit")
OUT_DIR = ROOT / "examples"
SVG = OUT_DIR / "20260702-oxetane-amide-coupling.svg"
PNG = OUT_DIR / "20260702-oxetane-amide-coupling.png"

WIDTH = 1000
HEIGHT = 280


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
        "cyclobutane_acid": candidate(
            "cyclobutane_acid",
            "OC(=O)C1CCC1",  # cyclobutanecarboxylic acid
        ),
        "aniline": candidate(
            "aniline",
            "Nc1cccc(C#N)c1",  # 3-aminobenzonitrile
        ),
        "amide_product": candidate(
            "amide_product",
            "O=C(Nc1cccc(C#N)c1)C1CCC1",  # N-(3-cyanophenyl)cyclobutanecarboxamide
        ),
    }

    # Visual centers, structure boxes, and a shared baseline-anchored label_y.
    places = [
        MolPlace("cyclobutane_acid", (130, 130), (200, 160), "",  228),
        MolPlace("aniline",          (350, 130), (180, 160), "",  228),
        MolPlace("amide_product",    (830, 130), (240, 170), "",  228),
    ]

    # Plus sign between the two reactants.
    plus = Label(245, 138, "+", "cond", 22)

    # Arrow centered on the reaction baseline.
    arrow = Arrow(500, 130, 690, 130)

    # Conditions: HATU + DIPEA above the arrow, DMF / 40 °C / 16 h below.
    conditions_above = Label(
        595,
        102,
        "HATU (1.5 eq)\nDIPEA (3.0 eq)",
        "cond",
        14,
    )
    conditions_below = Label(595, 158, "DMF, 40 °C, 16 h", "cond", 14)

    style = RouteStyle(
        condition_font_size=14,
        label_font_size=14,
        arrow_width=1.25,
        bond_line_width=1.6,
        atom_font_size=18,
        molecule_padding=0.04,
    )

    svg = render_route_svg(
        candidates,
        places,
        [arrow],
        [plus, conditions_above, conditions_below],
        WIDTH,
        HEIGHT,
        style,
    )
    write_svg(SVG, svg)
    screenshot_svg(SVG, PNG, WIDTH, HEIGHT)
    print(SVG)
    print(PNG)


if __name__ == "__main__":
    main()
