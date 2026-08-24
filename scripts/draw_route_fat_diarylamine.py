#!/usr/bin/env python3
"""Draw FAT-7a + FAT-8a -> FAT-9a from the supplied route image."""

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

from chemkit_model import MoleculeCandidate
from chemkit_route_renderer import (
    Label,
    MolPlace,
    centered_arrow_in_gap,
    chemdraw_compact_style,
    condition_labels_for_arrow,
    placed_molecule_bbox,
    render_route_svg,
    screenshot_svg,
    shared_structure_label_baseline,
    write_svg,
)


OUT_DIR = ROOT / "examples"
SVG = OUT_DIR / "20260819-fat-diarylamine.svg"
PNG = OUT_DIR / "20260819-fat-diarylamine.png"

WIDTH = 1350
HEIGHT = 330
STRUCTURE_Y = 125


def candidate(key: str, smiles: str) -> MoleculeCandidate:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Could not parse SMILES for {key}: {smiles}")
    Chem.SanitizeMol(mol)
    rdDepictor.Compute2DCoords(mol)
    return MoleculeCandidate(
        key=key,
        mol=mol,
        source_smiles=smiles,
        confidence=None,
        rdkit_status="sanitized",
    )


def set_coords(mol: Chem.Mol, coords: dict[int, tuple[float, float]]) -> None:
    conf = mol.GetConformer()
    if set(coords) != set(range(mol.GetNumAtoms())):
        raise ValueError("Template must define every atom coordinate")
    for idx, (x, y) in coords.items():
        conf.SetAtomPosition(idx, (x, y, 0.0))


def apply_bromofluorobenzene_template(mol: Chem.Mol) -> None:
    """Para ring with Br at upper-right and F at lower-left."""
    set_coords(
        mol,
        {
            0: (-2.598, -1.500),  # F
            1: (-1.299, -0.750),  # carbon bearing F
            2: (0.000, -1.500),
            3: (1.299, -0.750),
            4: (1.299, 0.750),   # carbon bearing Br
            5: (2.598, 1.500),   # Br
            6: (0.000, 1.500),
            7: (-1.299, 0.750),
        },
    )


def apply_aniline_template(mol: Chem.Mol) -> None:
    """Phenyl ring with NH2 at the upper-right vertex."""
    set_coords(
        mol,
        {
            0: (2.598, 1.500),   # NH2
            1: (1.299, 0.750),   # carbon bearing NH2
            2: (1.299, -0.750),
            3: (0.000, -1.500),
            4: (-1.299, -0.750),
            5: (-1.299, 0.750),
            6: (0.000, 1.500),
        },
    )


def build_product_from_fragments(
    aryl_halide: Chem.Mol,
    aniline: Chem.Mol,
    product: Chem.Mol,
) -> None:
    """Join both displayed fragments while matching the supplied product view."""
    halide_conf = aryl_halide.GetConformer()
    aniline_conf = aniline.GetConformer()
    target = product.GetConformer()

    # The product's right ring is the halide ring reflected horizontally so
    # the new N-C bond points left, as in the supplied ChemDraw depiction.
    # 7a atom 4 (C-Br) -> 9a atom 4 (C-N); atom 5 (Br) is removed.
    right_map = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 6: 12, 7: 13}
    for source_idx, target_idx in right_map.items():
        point = halide_conf.GetAtomPosition(source_idx)
        target.SetAtomPosition(target_idx, (-point.x, point.y, 0.0))

    # The linker N occupies the reflected former Br position.
    linker_target = (-halide_conf.GetAtomPosition(5).x, halide_conf.GetAtomPosition(5).y)
    source_n = aniline_conf.GetAtomPosition(0)
    dx = linker_target[0] - source_n.x
    dy = linker_target[1] - source_n.y
    left_map = {0: 5, 1: 6, 2: 7, 3: 8, 4: 9, 5: 10, 6: 11}
    for source_idx, target_idx in left_map.items():
        point = aniline_conf.GetAtomPosition(source_idx)
        target.SetAtomPosition(target_idx, (point.x + dx, point.y + dy, 0.0))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fat_7a = candidate("fat_7a", "Fc1ccc(Br)cc1")
    fat_8a = candidate("fat_8a", "Nc1ccccc1")
    fat_9a = candidate("fat_9a", "Fc1ccc(Nc2ccccc2)cc1")

    apply_bromofluorobenzene_template(fat_7a.mol)
    apply_aniline_template(fat_8a.mol)
    build_product_from_fragments(fat_7a.mol, fat_8a.mol, fat_9a.mol)

    candidates = {"fat_7a": fat_7a, "fat_8a": fat_8a, "fat_9a": fat_9a}
    style = chemdraw_compact_style()
    places = [
        MolPlace("fat_7a", (145, STRUCTURE_Y), (225, 180), "FAT-7a", 0),
        MolPlace("fat_8a", (415, STRUCTURE_Y), (225, 180), "FAT-8a", 0),
        MolPlace("fat_9a", (1080, STRUCTURE_Y), (420, 190), "FAT-9a", 0),
    ]
    bboxes = {
        place.key: placed_molecule_bbox(candidates[place.key], place, style)
        for place in places
    }
    label_y = shared_structure_label_baseline(list(bboxes.values()), style)
    places = [replace(place, label_y=label_y) for place in places]

    plus = Label(
        (bboxes["fat_7a"][2] + bboxes["fat_8a"][0]) / 2,
        STRUCTURE_Y + 6,
        "+",
        "cond",
        style.condition_font_size,
    )
    arrow = centered_arrow_in_gap(
        bboxes["fat_8a"], bboxes["fat_9a"], STRUCTURE_Y, length=430, minimum_clearance=18
    )
    conditions = condition_labels_for_arrow(
        arrow,
        above="Pd₂(dba)₃ (10 mol%)\nXPhos (20 mol%)\nK₃PO₄ (2.5 eq)",
        below="Toluene (300 μL)\n100 °C, 12 h",
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
        print("PNG export skipped; open the SVG with chemkit preview or the system browser.")
    print(SVG)
    print(PNG)


if __name__ == "__main__":
    main()
