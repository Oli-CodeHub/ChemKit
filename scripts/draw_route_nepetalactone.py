#!/usr/bin/env python3
"""Draw nepetalactone total synthesis route from citronellal (5 steps, 2 rows)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys

from rdkit import Chem
from rdkit.Chem import rdDepictor

# Use CoordGen (not RDKit's default 2D algorithm) so that explicit
# rotations like `rotate_180` produce predictable, identical layouts
# every run. Without this, ChemKit scripts silently fall back to the
# legacy RDKit 2D engine and atom orderings drift.
rdDepictor.SetPreferCoordGen(True)

SCRIPT_DIR = Path(__file__).resolve().parent
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
    write_svg,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "examples"
SVG = OUT_DIR / "nepetalactone_total_synthesis.svg"
PNG = OUT_DIR / "nepetalactone_total_synthesis.png"

WIDTH = 2200
HEIGHT = 600


def candidate(key: str, smiles: str, rotate_180: bool = False) -> MoleculeCandidate:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Could not parse SMILES for {key}: {smiles}")
    rdDepictor.Compute2DCoords(mol)
    if rotate_180:
        from rdkit.Geometry import Point3D
        conf = mol.GetConformer()
        for i in range(mol.GetNumAtoms()):
            pos = conf.GetAtomPosition(i)
            # 180° rotation around z: invert x and y. Preserves wedge
            # orientation because rotation is orientation-preserving.
            conf.SetAtomPosition(i, Point3D(-pos.x, -pos.y, pos.z))
    return MoleculeCandidate(
        key=key,
        mol=mol,
        source_smiles=smiles,
        confidence=None,
        rdkit_status="sanitized",
    )


def add_step(
    candidates, places, arrows, labels, style,
    left_key, right_key, y, above, below, length=110.0,
):
    """Add an arrow + conditions between two placed molecules."""
    left_bbox = placed_molecule_bbox(candidates[places[left_key].key], places[left_key], style)
    right_bbox = placed_molecule_bbox(candidates[places[right_key].key], places[right_key], style)
    arrow = centered_arrow_in_gap(left_bbox, right_bbox, y, length, minimum_clearance=14.0)
    arrows.append(arrow)
    labels.extend(condition_labels_for_arrow(arrow, above=above, below=below, style=style))


def add_plus(labels, x, y, size=22):
    labels.append(Label(x, y, "+", "cond", size))


def main() -> None:
    style = replace(
        chemdraw_compact_style(),
        route_font_family='"Arial Bold", "PingFang SC", Arial, Helvetica, sans-serif',
    )
    # rotate_180: 180° in-plane rotation to match the original figure's
    # handedness. CoordGen default doesn't always place isopropenyl /
    # N where the source figure does.
    candidates = {
        "citronellal": candidate("citronellal", "O=C[C@@H](C)CCC=C(C)C",     rotate_180=True),
        "ii_2":        candidate("ii_2",        "O=C[C@@H](C)CCC=C(C)CO",     rotate_180=True),
        "ii_3":        candidate("ii_3",        "O=C[C@@H](C)CCC=C(C)C=O",    rotate_180=True),
        "II_4":        candidate("II_4",        "[H][C@@]12CC[C@@H](C)[C@]1(C(C)=C)CN(C)C2",  rotate_180=True),
        "II_A":        candidate("II_A",        "[H][C@]12CC[C@H](C)[C@]1(C(C)=C)C[C@@H](O)O2", rotate_180=True),
        "II_B":        candidate("II_B",        "[H][C@]12CC[C@H](C)[C@]1(C(C)=C)CC(=O)O2",   rotate_180=True),
    }

    row1_y = 145
    row1_label = 245
    row2_y = 425
    row2_label = 535

    # ====== Row 1: citronellal → ii-2 → ii-3 (paired) → ii-3 → II-4 ======
    # In the original figure, the SeO2 oxidation gives a mixture of ii-2 and
    # ii-3 (the dialdehyde), and the DMP step then oxidizes ii-2 → ii-3.
    places: dict[str, MolPlace] = {
        "citronellal": MolPlace("citronellal", (110,  row1_y), (240, 130), "citronellal", row1_label),
        "ii_2":        MolPlace("ii_2",        (550,  row1_y), (220, 130), "ii-2",         row1_label),
        "ii_3_pair":   MolPlace("ii_3",        (810,  row1_y), (220, 130), "ii-3",         row1_label),
        "ii_3_only":   MolPlace("ii_3",        (1330, row1_y), (220, 130), "ii-3",         row1_label),
        "II_4":        MolPlace("II_4",        (2050, row1_y), (260, 200), "II-4",         row1_label),
        # Row 2
        "II_4_b": MolPlace("II_4", (110,  row2_y), (260, 200), "II-4",  row2_label),
        "II_A":   MolPlace("II_A", (1080, row2_y), (260, 200), "II-A",  row2_label),
        "II_B":   MolPlace("II_B", (1970, row2_y), (260, 200), "II-B",  row2_label),
    }

    arrows: list[Arrow] = []
    labels: list[Label] = []

    # Row 1 — three arrows
    # 1) citronellal → ii-2+ii-3 pair (use ii_3_pair as right side of arrow)
    add_step(
        candidates, places, arrows, labels, style,
        "citronellal", "ii_2", row1_y,
        above=(
            "SeO\u2082 (3 mol %)\n"
            "t-BuOOH\n"
            "salicylic acid\n"
            "CH\u2082Cl\u2082, rt"
        ),
        below="40-50%",
    )
    # 2) ii-2+ii-3 pair → ii-3 (DMP oxidation)
    add_step(
        candidates, places, arrows, labels, style,
        "ii_3_pair", "ii_3_only", row1_y,
        above=(
            "DMP\n"
            "CH\u2082Cl\u2082, rt"
        ),
        below="85%",
    )
    # 3) ii-3 → II-4
    add_step(
        candidates, places, arrows, labels, style,
        "ii_3_only", "II_4", row1_y,
        above=(
            "MeNH\u2082\n"
            "4 \u00c5 MS\n"
            "Et\u2082O, Ar, rt"
        ),
        below="80%",
    )

    # + sign between ii-2 and ii-3 in the first product box
    ii2_bbox = placed_molecule_bbox(candidates["ii_2"], places["ii_2"], style)
    ii3pair_bbox = placed_molecule_bbox(candidates["ii_3"], places["ii_3_pair"], style)
    plus_x = (ii2_bbox[2] + ii3pair_bbox[0]) / 2
    add_plus(labels, plus_x, row1_y)

    # Row 2 — two arrows
    add_step(
        candidates, places, arrows, labels, style,
        "II_4_b", "II_A", row2_y,
        above=(
            "TsOH\u00b7H\u2082O\n"
            "THF:H\u2082O (9:1), rt"
        ),
        below="80%",
    )
    add_step(
        candidates, places, arrows, labels, style,
        "II_A", "II_B", row2_y,
        above=(
            "TPAP (5 mol %)\n"
            "NMO\n"
            "4 \u00c5 MS\n"
            "CH\u2082Cl\u2082, Ar, rt"
        ),
        below="85%",
    )

    # molecule-class labels under the second-row structures
    labels.append(Label(places["II_A"].center[0], row2_label + 22, "nepetalactol",  "cond", 14))
    labels.append(Label(places["II_B"].center[0], row2_label + 22, "nepetalactone", "cond", 14))

    svg = render_route_svg(
        candidates=candidates,
        places=list(places.values()),
        arrows=arrows,
        labels=labels,
        width=WIDTH,
        height=HEIGHT,
        style=style,
    )
    write_svg(SVG, svg)
    if screenshot_svg(SVG, PNG, WIDTH, HEIGHT):
        print(PNG)
    else:
        print("PNG export skipped; open the SVG with ./bin/chemkit preview.")
    print(SVG)


if __name__ == "__main__":
    main()
