#!/usr/bin/env python3
"""Draw FAT-4a + FAT-5a -> FAT-6a using the current ChemKit profile."""

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
    Arrow,
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
SVG = OUT_DIR / "20260819-fat-benzimidazole-piperidine.svg"
PNG = OUT_DIR / "20260819-fat-benzimidazole-piperidine.png"

WIDTH = 1600
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


def apply_benzimidazole_template(mol: Chem.Mol) -> None:
    """Right-facing benzimidazole: [nH] above, N below, Cl lower-left."""
    set_coords(
        mol,
        {
            0: (3.808, 0.000),   # methyl
            1: (2.308, 0.000),   # C2
            2: (1.427, 1.213),   # imidazole [nH]
            3: (0.000, 0.750),   # fused carbon, upper
            4: (-1.299, 1.500),
            5: (-2.598, 0.750),
            6: (-2.598, -0.750),
            7: (-3.897, -1.500),  # Cl / leaving-group position
            8: (-1.299, -1.500),
            9: (0.000, -0.750),   # fused carbon, lower
            10: (1.427, -1.213),  # imidazole N
        },
    )


def apply_boc_aminopiperidine_template(mol: Chem.Mol) -> None:
    """Boc on ring N at upper-left; 4-NH2 extends lower-right."""
    set_coords(
        mol,
        {
            0: (-5.196, 1.500),   # tert-butyl methyl
            1: (-3.897, 0.750),   # tert-butyl quaternary carbon
            2: (-5.196, 0.000),
            3: (-3.897, 2.250),
            4: (-2.598, 0.000),   # alkoxy O
            5: (-1.299, 0.750),   # carbonyl C
            6: (-1.299, 2.250),   # carbonyl O
            7: (0.000, 0.000),    # piperidine N
            8: (1.299, 0.750),
            9: (2.598, 0.000),
            10: (2.598, -1.500),  # 4-carbon bearing NH2
            11: (3.897, -2.250),  # exocyclic NH2
            12: (1.299, -2.250),
            13: (0.000, -1.500),
        },
    )


def build_product_from_fragments(
    benzimidazole: Chem.Mol,
    aminopiperidine: Chem.Mol,
    product: Chem.Mol,
) -> None:
    """Copy both reactant depictions and replace Cl/NH2 with the new N bond."""
    source_ben = benzimidazole.GetConformer()
    source_pip = aminopiperidine.GetConformer()
    target = product.GetConformer()

    # FAT-4a atom -> FAT-6a atom. Atom 7 (Cl) is replaced by the linker N.
    ben_map = {0: 18, 1: 17, 2: 16, 3: 15, 4: 14, 5: 13, 6: 12, 8: 21, 9: 20, 10: 19}
    for source_idx, target_idx in ben_map.items():
        point = source_ben.GetAtomPosition(source_idx)
        target.SetAtomPosition(target_idx, (point.x, point.y, 0.0))

    # Product linker N occupies the former Cl position, so the piperidine
    # fragment is translated from its displayed NH2 position to that site.
    leaving_group = source_ben.GetAtomPosition(7)
    source_linker = source_pip.GetAtomPosition(11)
    dx = leaving_group.x - source_linker.x
    dy = leaving_group.y - source_linker.y
    pip_map = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9, 10: 10, 11: 11, 12: 22, 13: 23}
    for source_idx, target_idx in pip_map.items():
        point = source_pip.GetAtomPosition(source_idx)
        target.SetAtomPosition(target_idx, (point.x + dx, point.y + dy, 0.0))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fat_4a = candidate("fat_4a", "Cc1[nH]c2ccc(Cl)cc2n1")
    fat_5a = candidate("fat_5a", "CC(C)(C)OC(=O)N1CCC(N)CC1")
    fat_6a = candidate(
        "fat_6a",
        "CC(C)(C)OC(=O)N1CCC(Nc2ccc3[nH]c(C)nc3c2)CC1",
    )

    apply_benzimidazole_template(fat_4a.mol)
    apply_boc_aminopiperidine_template(fat_5a.mol)
    build_product_from_fragments(fat_4a.mol, fat_5a.mol, fat_6a.mol)

    candidates = {"fat_4a": fat_4a, "fat_5a": fat_5a, "fat_6a": fat_6a}
    style = chemdraw_compact_style()
    places = [
        MolPlace("fat_4a", (170, STRUCTURE_Y), (230, 180), "FAT-4a", 0),
        MolPlace("fat_5a", (450, STRUCTURE_Y), (285, 200), "FAT-5a", 0),
        MolPlace("fat_6a", (1280, STRUCTURE_Y), (480, 230), "FAT-6a", 0),
    ]
    bboxes = {
        place.key: placed_molecule_bbox(candidates[place.key], place, style)
        for place in places
    }
    label_y = shared_structure_label_baseline(list(bboxes.values()), style)
    places = [replace(place, label_y=label_y) for place in places]

    plus = Label(
        (bboxes["fat_4a"][2] + bboxes["fat_5a"][0]) / 2,
        STRUCTURE_Y + 6,
        "+",
        "cond",
        style.condition_font_size,
    )
    arrow = centered_arrow_in_gap(
        bboxes["fat_5a"], bboxes["fat_6a"], STRUCTURE_Y, length=430, minimum_clearance=18
    )
    conditions = condition_labels_for_arrow(
        arrow,
        above="Cat. (10 mol%)\nBase (3.0 eq)",
        below="Solvent/NMP (60:40, 37 mL/g)\n80 °C, 16 h",
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
