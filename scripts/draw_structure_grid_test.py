#!/usr/bin/env python3
"""Draw ChemKit's second validation canvas: a regular structure grid.

The EBF entry is intentionally a labelled attachment-group placeholder because
"EBF" is not a unique chemistry abbreviation without a source definition.
Replace ``EBF_SMILES`` and ``display_label`` once the intended structure is
confirmed.
"""

from __future__ import annotations

import sys
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import rdDepictor


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from chemkit_model import MoleculeCandidate
from chemkit_route_renderer import (
    MolPlace,
    chemdraw_compact_style,
    placed_molecule_bbox,
    render_route_svg,
    screenshot_svg,
    shared_structure_label_baseline,
    write_svg,
)


OUT_DIR = ROOT / "examples"
SVG = OUT_DIR / "20260820-structure-grid-test.svg"
PNG = OUT_DIR / "20260820-structure-grid-test.png"

EBF_SMILES = "CC[*]"

STRUCTURES: list[tuple[str, str, str | None]] = [
    ("benzene", "c1ccccc1", None),
    ("pyridine", "n1ccccc1", None),
    ("imidazole", "c1ncc[nH]1", None),
    ("thiazole", "c1nccs1", None),
    ("indole", "c1ccc2[nH]ccc2c1", None),
    ("spiro ring", "C1CCC2(CC1)CCOCC2", None),
    ("quaternary ammonium salt", "C[N+](C)(C)C.[Cl-]", None),
    ("Boc", "CC(C)(C)OC(=O)NCC", None),
    ("EBF", EBF_SMILES, "EBF"),
]


def candidate(key: str, smiles: str, display_label: str | None = None) -> MoleculeCandidate:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Could not parse {key}: {smiles}")
    Chem.SanitizeMol(mol)
    if display_label:
        dummy_atoms = [atom for atom in mol.GetAtoms() if atom.GetAtomicNum() == 0]
        if not dummy_atoms:
            raise ValueError(f"{key} needs a dummy atom for its display label")
        dummy_atoms[0].SetProp("_displayLabel", display_label)
    rdDepictor.Compute2DCoords(mol, canonOrient=True)
    return MoleculeCandidate(
        key=key,
        mol=mol,
        source_smiles=smiles,
        confidence=None,
        rdkit_status="sanitized",
    )


def build_layout(candidates: dict[str, MoleculeCandidate]) -> tuple[list[MolPlace], int, int]:
    style = chemdraw_compact_style()
    width, height = 960, 900
    columns = (160.0, 480.0, 800.0)
    rows = (145.0, 435.0, 725.0)
    places: list[MolPlace] = []

    for row in range(3):
        row_items = STRUCTURES[row * 3 : row * 3 + 3]
        provisional = [
            MolPlace(name, (columns[col], rows[row]), (260.0, 180.0), "", 0.0)
            for col, (name, _, _) in enumerate(row_items)
        ]
        row_bboxes = [
            placed_molecule_bbox(candidates[name], place, style)
            for place, (name, _, _) in zip(provisional, row_items)
        ]
        label_y = shared_structure_label_baseline(row_bboxes, style)
        for col, (name, _, _) in enumerate(row_items):
            places.append(
                MolPlace(
                    key=name,
                    center=(columns[col], rows[row]),
                    box=(260.0, 180.0),
                    label=str(row * 3 + col + 1),
                    label_y=label_y,
                )
            )
    return places, width, height


def main() -> None:
    candidates = {
        name: candidate(name, smiles, display_label)
        for name, smiles, display_label in STRUCTURES
    }
    places, width, height = build_layout(candidates)
    style = chemdraw_compact_style()
    svg = render_route_svg(
        candidates=candidates,
        places=places,
        arrows=[],
        labels=[],
        width=width,
        height=height,
        style=style,
    )
    write_svg(SVG, svg)
    png_available = screenshot_svg(SVG, PNG, width, height)
    print(SVG)
    if png_available:
        print(PNG)
    else:
        print("PNG export skipped; open the SVG with ./bin/chemkit preview.")


if __name__ == "__main__":
    main()
