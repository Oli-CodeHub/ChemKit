#!/usr/bin/env python3
"""Render the screenshot's three-step allylic alcohol route with ACS styling."""

from __future__ import annotations

import sys
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import rdDepictor
from rdkit.Geometry import Point3D

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from chemkit_model import MoleculeCandidate
from chemkit_route_renderer import (
    Arrow,
    Label,
    arrow_length_for_conditions,
    MolPlace,
    centered_arrow_in_gap,
    chemdraw_compact_style,
    condition_labels_for_arrow,
    placed_molecule_bbox,
    render_route_svg,
    screenshot_svg,
    shared_structure_label_baseline,
    tighten_route_svg,
    write_svg,
)


OUT_DIR = ROOT / "examples"
SVG = OUT_DIR / "20260822-route-3-butyn-1-ol-bromo-kumada-tosylate-acs.svg"
PNG = OUT_DIR / "20260822-route-3-butyn-1-ol-bromo-kumada-tosylate-acs.png"


def candidate(
    key: str,
    smiles: str,
    labels: dict[int, str] | None = None,
    rotate_180: bool = False,
) -> MoleculeCandidate:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Could not parse {key}: {smiles}")
    for atom_index, label in (labels or {}).items():
        mol.GetAtomWithIdx(atom_index).SetProp("_displayLabel", label)
    rdDepictor.Compute2DCoords(mol)
    if rotate_180:
        conf = mol.GetConformer()
        for atom_index in range(mol.GetNumAtoms()):
            point = conf.GetAtomPosition(atom_index)
            conf.SetAtomPosition(atom_index, Point3D(-point.x, -point.y, point.z))
    return MoleculeCandidate(key, mol, smiles, None, "sanitized")


def main() -> None:
    # The source draws 3-butyn-1-ol, then a 2-bromoallylic intermediate. R and
    # OTs remain condensed source labels rather than expanded fragments.
    candidates = {
        "start": candidate("start", "C#CCCO", rotate_180=True),
        "s1": candidate("s1", "C=C(Br)CCO", rotate_180=True),
        "s2": candidate("s2", "*C(=C)CCO", {0: "R"}),
        "s3": candidate("s3", "*C(=C)CCO", {0: "R", 5: "OTs"}),
    }
    style = chemdraw_compact_style()
    arrow_specs = (
        ("start", "s1", "HBr\nEt₄NBr", "DCM"),
        ("s1", "s2", "NiCl₂(dppe) (5 mol%)\nRMgX (2.5 equiv.)", "THF, 0 °C to RT"),
        ("s2", "s3", "TsCl (1.1 equiv.)\nEt₃N (2.0 equiv.)", "DMAP (0.15 equiv.)\nDCM, 0 °C to RT"),
    )
    clearance = 22.0
    # Measure each molecule once at the common fixed scale, then allocate the
    # inter-molecule gaps from the actual condition text widths.
    widths = {}
    for key in candidates:
        probe = MolPlace(key, (0.0, 160.0), (0.0, 0.0), "", 0.0)
        bbox = placed_molecule_bbox(candidates[key], probe, style)
        widths[key] = bbox[2] - bbox[0]
    lengths = {
        (left, right): arrow_length_for_conditions(above, below, style)
        for left, right, above, below in arrow_specs
    }
    centers = {"start": 100.0 + widths["start"] / 2.0}
    for left, right, _, _ in arrow_specs:
        centers[right] = (
            centers[left]
            + widths[left] / 2.0
            + lengths[(left, right)]
            + 2.0 * clearance
            + widths[right] / 2.0
        )
    labels_by_key = {"start": "", "s1": "S1", "s2": "S2", "s3": "S3"}
    places = {
        key: MolPlace(key, (x, 160.0), (widths[key], 150.0), labels_by_key[key], 0.0)
        for key, x in centers.items()
    }
    bboxes = {key: placed_molecule_bbox(candidates[key], places[key], style) for key in places}
    baseline = shared_structure_label_baseline(list(bboxes.values()), style)
    places = {
        key: MolPlace(place.key, place.center, place.box, place.label, baseline)
        for key, place in places.items()
    }

    arrows: list[Arrow] = []
    labels: list[Label] = []
    for left, right, above, below in arrow_specs:
        arrow = centered_arrow_in_gap(
            bboxes[left], bboxes[right], 160.0, lengths[(left, right)], minimum_clearance=clearance
        )
        arrows.append(arrow)
        labels.extend(condition_labels_for_arrow(arrow, above, below, style))

    raw_svg = render_route_svg(
        candidates,
        list(places.values()),
        arrows,
        labels,
        width=int(centers["s3"] + widths["s3"] / 2.0 + 260.0),
        height=1200,
        style=style,
    )
    svg, (_, _, cropped_width, cropped_height) = tighten_route_svg(raw_svg, padding=28.0)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_svg(SVG, svg)
    screenshot_svg(SVG, PNG, cropped_width, cropped_height)
    print(SVG)
    print(PNG)


if __name__ == "__main__":
    main()
