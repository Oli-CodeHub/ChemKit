#!/usr/bin/env python3
"""Draw FAT-1a + FAT-2a -> FAT-3a with fixed scale and dual-fragment orientation."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys

from rdkit import Chem
from rdkit.Chem import rdDepictor


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from chemkit_ocsr import OcsrCandidate
from chemkit_route_renderer import (
    Arrow,
    Label,
    MolPlace,
    centered_arrow_in_gap,
    chemdraw_compact_style,
    condition_labels_for_arrow,
    horizontal_gap_center,
    placed_molecule_bbox,
    render_route_svg,
    screenshot_svg,
    shared_structure_label_baseline,
    write_svg,
)


OUT_DIR = ROOT / "examples"
SVG = OUT_DIR / "20260819-fat-amide-coupling.svg"
PNG = OUT_DIR / "20260819-fat-amide-coupling.png"

WIDTH = 850
HEIGHT = 250
STRUCTURE_Y = 100


def candidate(
    key: str,
    display_smiles: str,
    source_smiles: str,
    collapse_nitrile: bool = False,
) -> OcsrCandidate:
    """Build a sanitized display molecule while retaining the full source SMILES."""
    mol = Chem.MolFromSmiles(display_smiles)
    if mol is None:
        raise ValueError(f"Could not parse display SMILES for {key}: {display_smiles}")
    Chem.SanitizeMol(mol)
    if collapse_nitrile:
        for atom in mol.GetAtoms():
            if atom.GetAtomicNum() == 0:
                atom.SetProp("_displayLabel", "CN")
    rdDepictor.Compute2DCoords(mol)
    return OcsrCandidate(
        key=key,
        mol=mol,
        source_smiles=source_smiles,
        confidence=None,
        rdkit_status="sanitized",
    )


def set_coords(mol: Chem.Mol, coords: dict[int, tuple[float, float]]) -> None:
    """Apply an explicit reaction-template depiction."""
    conf = mol.GetConformer()
    if set(coords) != set(range(mol.GetNumAtoms())):
        raise ValueError("Reaction template must define every atom coordinate")
    for idx, (x, y) in coords.items():
        conf.SetAtomPosition(idx, (x, y, 0.0))


def apply_acid_template(mol: Chem.Mol) -> None:
    """C=O upward, OH down-right, cyclobutane extending down-left."""
    set_coords(
        mol,
        {
            0: (0.000, 1.500),
            1: (0.000, 0.000),
            2: (1.299, -0.750),
            3: (-1.299, -0.750),
            4: (-2.748, -0.362),
            5: (-3.136, -1.811),
            6: (-1.687, -2.199),
        },
    )


def apply_aniline_template(mol: Chem.Mol) -> None:
    """Vertical aryl ring with CN at twelve o'clock and NH2 lower-left."""
    set_coords(
        mol,
        {
            0: (-2.598, -1.500),
            1: (-1.299, -0.750),
            2: (0.000, -1.500),
            3: (1.299, -0.750),
            4: (1.299, 0.750),
            5: (0.000, 1.500),
            6: (0.000, 3.000),
            7: (-1.299, 0.750),
        },
    )


def build_dual_fragment_product(
    acid: Chem.Mol,
    aniline: Chem.Mol,
    product: Chem.Mol,
) -> None:
    """Copy both reactant depictions into the amide product."""
    acid_conf = acid.GetConformer()
    aniline_conf = aniline.GetConformer()
    product_conf = product.GetConformer()

    # O=C-C1CCC1 is copied unchanged from FAT-1a.
    acid_to_product = {0: 0, 1: 1, 3: 10, 4: 11, 5: 12, 6: 13}
    for acid_idx, product_idx in acid_to_product.items():
        point = acid_conf.GetAtomPosition(acid_idx)
        product_conf.SetAtomPosition(product_idx, (point.x, point.y, 0.0))

    # The acid OH position becomes the product amide N. Translate the entire
    # FAT-2a fragment by the same vector, preserving its displayed orientation.
    target_n = acid_conf.GetAtomPosition(2)
    source_n = aniline_conf.GetAtomPosition(0)
    dx = target_n.x - source_n.x
    dy = target_n.y - source_n.y
    aniline_to_product = {0: 2, 1: 3, 2: 4, 3: 5, 4: 6, 5: 7, 6: 8, 7: 9}
    for aniline_idx, product_idx in aniline_to_product.items():
        point = aniline_conf.GetAtomPosition(aniline_idx)
        product_conf.SetAtomPosition(product_idx, (point.x + dx, point.y + dy, 0.0))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fat_1a = candidate("fat_1a", "O=C(O)C1CCC1", "O=C(O)C1CCC1")
    fat_2a = candidate(
        "fat_2a",
        "Nc1cccc(*)c1",
        "Nc1cccc(C#N)c1",
        collapse_nitrile=True,
    )
    fat_3a = candidate(
        "fat_3a",
        "O=C(Nc1cccc(*)c1)C1CCC1",
        "O=C(Nc1cccc(C#N)c1)C1CCC1",
        collapse_nitrile=True,
    )

    # Establish both reactant depictions, then join them without rotating
    # either conserved fragment.
    apply_acid_template(fat_1a.mol)
    apply_aniline_template(fat_2a.mol)
    build_dual_fragment_product(fat_1a.mol, fat_2a.mol, fat_3a.mol)

    candidates = {"fat_1a": fat_1a, "fat_2a": fat_2a, "fat_3a": fat_3a}
    style = chemdraw_compact_style()

    places = [
        MolPlace("fat_1a", (76, STRUCTURE_Y), (140, 120), "FAT-1a", 0),
        MolPlace("fat_2a", (260, STRUCTURE_Y), (145, 135), "FAT-2a", 0),
        MolPlace("fat_3a", (675, STRUCTURE_Y), (225, 155), "FAT-3a", 0),
    ]
    bboxes = {
        place.key: placed_molecule_bbox(candidates[place.key], place, style)
        for place in places
    }
    label_y = shared_structure_label_baseline(list(bboxes.values()), style)
    places = [replace(place, label_y=label_y) for place in places]

    plus_x = horizontal_gap_center(bboxes["fat_1a"], bboxes["fat_2a"])
    plus = Label(plus_x, 106, "+", "cond", style.condition_font_size)
    arrow = centered_arrow_in_gap(
        bboxes["fat_2a"],
        bboxes["fat_3a"],
        STRUCTURE_Y,
        length=200,
        minimum_clearance=15,
    )
    conditions = condition_labels_for_arrow(
        arrow,
        above="HATU (1.5 eq)\nDIPEA (3.0 eq)",
        below="DMF, 40 °C, 16 h",
        style=style,
    )

    svg = render_route_svg(
        candidates=candidates,
        places=places,
        arrows=[arrow],
        labels=[plus, *conditions],
        width=WIDTH,
        height=HEIGHT,
        style=style,
    )
    write_svg(SVG, svg)
    if not screenshot_svg(SVG, PNG, WIDTH, HEIGHT):
        raise RuntimeError("Google Chrome is required to render the PNG preview")
    print(SVG)
    print(PNG)


if __name__ == "__main__":
    main()
