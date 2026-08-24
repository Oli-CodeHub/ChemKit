#!/usr/bin/env python3
"""Reproduce the supplied four-compound route with a carbon ring atom."""

from __future__ import annotations

import math
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
    MolPlace,
    arrow_length_for_conditions,
    centered_arrow_in_gap,
    chemdraw_compact_style,
    condition_labels_for_arrow,
    estimate_condition_text_width,
    placed_molecule_bbox,
    render_route_svg,
    screenshot_svg,
    shared_structure_label_baseline,
    tighten_route_svg,
    write_svg,
)


OUT_DIR = ROOT / "examples"
SVG = OUT_DIR / "20260823-route-cyclohexane-allylation-auto-v2.svg"
PNG = OUT_DIR / "20260823-route-cyclohexane-allylation-auto-v2.png"


def _atom(rw: Chem.RWMol, symbol: str) -> int:
    return rw.AddAtom(Chem.Atom(symbol))


def _label_atom(rw: Chem.RWMol, text: str) -> int:
    atom = Chem.Atom(0)
    atom.SetProp("_displayLabel", text)
    return rw.AddAtom(atom)


def _bond(rw: Chem.RWMol, begin: int, end: int, bond_type: Chem.BondType = Chem.BondType.SINGLE) -> None:
    rw.AddBond(begin, end, bond_type)


def _with_coords(rw: Chem.RWMol, coords: list[tuple[float, float]]) -> Chem.Mol:
    mol = rw.GetMol()
    Chem.SanitizeMol(mol)
    if len(coords) != mol.GetNumAtoms():
        raise ValueError(f"Expected {mol.GetNumAtoms()} coordinates, got {len(coords)}")
    conf = Chem.Conformer(mol.GetNumAtoms())
    for idx, (x, y) in enumerate(coords):
        # RDKit's SVG canvas reverses the y-axis relative to the source crop;
        # invert the authored coordinates so substituents remain above/below
        # the ring exactly as drawn in the reference.
        conf.SetAtomPosition(idx, Point3D(x, -y, 0.0))
    mol.AddConformer(conf, assignId=True)
    return mol


def _ring(rw: Chem.RWMol) -> list[int]:
    ring = [_atom(rw, "C") for _ in range(6)]
    for begin, end in zip(ring, ring[1:] + ring[:1]):
        _bond(rw, begin, end)
    return ring


def _ring_coords() -> list[tuple[float, float]]:
    # Vertical cyclohexane projection matching the source.  The bottom atom is
    # an ordinary carbon; the source's X placeholder is intentionally absent.
    return [
        (0.0, 0.0),
        (0.95, 0.58),
        (0.95, 1.75),
        (0.0, 2.34),
        (-0.95, 1.75),
        (-0.95, 0.58),
    ]


def _mapped_atoms(mol: Chem.Mol) -> dict[int, int]:
    return {
        atom.GetAtomMapNum(): atom.GetIdx()
        for atom in mol.GetAtoms()
        if atom.GetAtomMapNum()
    }


def _orient_cyclohexane(mol: Chem.Mol, central_idx: int, right_idx: int | None = None) -> None:
    """Rigidly orient an RDKit-generated depiction without editing bond angles."""
    conf = mol.GetConformer()
    ring = next(
        ring
        for ring in mol.GetRingInfo().AtomRings()
        if len(ring) == 6 and central_idx in ring
    )
    cx = sum(conf.GetAtomPosition(idx).x for idx in ring) / len(ring)
    cy = sum(conf.GetAtomPosition(idx).y for idx in ring) / len(ring)
    central = conf.GetAtomPosition(central_idx)
    angle = math.pi / 2.0 - math.atan2(central.y - cy, central.x - cx)
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    for idx in range(mol.GetNumAtoms()):
        point = conf.GetAtomPosition(idx)
        dx, dy = point.x - cx, point.y - cy
        conf.SetAtomPosition(
            idx,
            Point3D(cx + dx * cos_a - dy * sin_a, cy + dx * sin_a + dy * cos_a, 0.0),
        )

    if right_idx is not None:
        central_x = conf.GetAtomPosition(central_idx).x
        if conf.GetAtomPosition(right_idx).x < central_x:
            for idx in range(mol.GetNumAtoms()):
                point = conf.GetAtomPosition(idx)
                conf.SetAtomPosition(idx, Point3D(2.0 * central_x - point.x, point.y, 0.0))


def _point_terminal_bond(
    mol: Chem.Mol,
    anchor_idx: int,
    terminal_idx: int,
    direction: tuple[float, float],
) -> None:
    """Rotate a terminal bond to a semantic drawing direction at fixed length."""
    conf = mol.GetConformer()
    anchor = conf.GetAtomPosition(anchor_idx)
    terminal = conf.GetAtomPosition(terminal_idx)
    bond_length = math.hypot(terminal.x - anchor.x, terminal.y - anchor.y)
    dx, dy = direction
    magnitude = math.hypot(dx, dy)
    conf.SetAtomPosition(
        terminal_idx,
        Point3D(
            anchor.x + bond_length * dx / magnitude,
            anchor.y + bond_length * dy / magnitude,
            0.0,
        ),
    )


def _apply_semantic_template(
    mol: Chem.Mol,
    maps: dict[int, int],
    template: str,
) -> None:
    """Apply standard functional-group geometry after automatic depiction.

    Templates use RDKit's generated bond length and only impose conventional
    60/120-degree skeletal directions.  They encode publication drawing
    semantics that connectivity-only SMILES does not contain.
    """
    conf = mol.GetConformer()

    def point(map_number: int) -> Point3D:
        return conf.GetAtomPosition(maps[map_number])

    def set_relative(map_number: int, origin: Point3D, dx: float, dy: float, length: float) -> Point3D:
        target = Point3D(origin.x + dx * length, origin.y + dy * length, 0.0)
        conf.SetAtomPosition(maps[map_number], target)
        return target

    def mapped_bond_length(first: int, second: int) -> float:
        a, b = point(first), point(second)
        return math.hypot(b.x - a.x, b.y - a.y)

    def allyl_from_center(center: Point3D, length: float) -> None:
        # Screen-space convention: CH2 upper-right, substituted alkene carbon
        # lower-right, methyl upper-right, terminal methylene vertically down.
        side_ch2 = set_relative(2, center, 0.8660254, 0.5, length)
        alkene = set_relative(7, side_ch2, 0.8660254, -0.5, length)
        set_relative(9, alkene, 0.8660254, 0.5, length)
        set_relative(8, alkene, 0.0, -1.0, length)

    if template == "ester_right":
        center = point(1)
        length = mapped_bond_length(1, 4)
        carbonyl = set_relative(4, center, 0.0, 1.0, length)
        set_relative(10, carbonyl, -0.8660254, 0.5, length)
        methoxy_oxygen = set_relative(6, carbonyl, 0.8660254, 0.5, length)
        if 3 in maps:
            set_relative(3, methoxy_oxygen, 1.0, 0.0, length)
    elif template == "ester_left_allyl":
        center = point(1)
        length = mapped_bond_length(1, 4)
        carbonyl = set_relative(4, center, -0.8660254, 0.5, length)
        set_relative(10, carbonyl, 0.0, 1.0, length)
        methoxy_oxygen = set_relative(6, carbonyl, -0.8660254, -0.5, length)
        if 3 in maps:
            set_relative(3, methoxy_oxygen, -1.0, 0.0, length)
        allyl_from_center(center, length)
    elif template in {"alcohol_allyl", "tosylate_allyl"}:
        center = point(1)
        length = mapped_bond_length(1, 3)
        alcohol_ch2 = set_relative(3, center, -0.8660254, 0.5, length)
        set_relative(5, alcohol_ch2, -0.8660254, -0.5, length)
        allyl_from_center(center, length)
    elif template == "methallyl_reagent":
        alkene = point(7)
        length = mapped_bond_length(7, 2)
        set_relative(8, alkene, -0.8660254, -0.5, length)
        set_relative(9, alkene, 0.0, 1.0, length)
        bromomethyl = set_relative(2, alkene, 0.8660254, -0.5, length)
        set_relative(11, bromomethyl, 0.8660254, 0.5, length)


def _candidate_from_smiles(
    key: str,
    source_smiles: str,
    drawing_smiles: str | None = None,
    right_map: int | None = None,
    display_labels: dict[int, str] | None = None,
    terminal_directions: list[tuple[int, int, tuple[float, float]]] | None = None,
    semantic_template: str | None = None,
) -> MoleculeCandidate:
    mol = Chem.MolFromSmiles(drawing_smiles or source_smiles)
    if mol is None:
        raise ValueError(f"Could not parse SMILES for {key}")
    rdDepictor.Compute2DCoords(mol, canonOrient=True)
    maps = _mapped_atoms(mol)
    if 1 in maps:
        _orient_cyclohexane(mol, maps[1], maps.get(right_map) if right_map else None)
    if semantic_template:
        _apply_semantic_template(mol, maps, semantic_template)
    for anchor_map, terminal_map, direction in terminal_directions or []:
        _point_terminal_bond(mol, maps[anchor_map], maps[terminal_map], direction)
    for map_number, label in (display_labels or {}).items():
        mol.GetAtomWithIdx(maps[map_number]).SetProp("_displayLabel", label)
    for atom in mol.GetAtoms():
        atom.SetAtomMapNum(0)
    return MoleculeCandidate(key, mol, source_smiles, None, "sanitized")


def ester_candidate() -> MoleculeCandidate:
    return _candidate_from_smiles(
        "1",
        "COC(=O)C1CCCCC1",
        drawing_smiles="[*:6][C:4](=[O:10])[CH:1]1CCCCC1",
        right_map=6,
        display_labels={6: "OMe"},
        semantic_template="ester_right",
    )


def allylated_candidate() -> MoleculeCandidate:
    return _candidate_from_smiles(
        "2",
        "COC(=O)C1(CC(=C)C)CCCCC1",
        drawing_smiles="[*:6][C:4](=[O:10])[C:1]1([CH2:2][C:7](=[CH2:8])[CH3:9])CCCCC1",
        right_map=2,
        display_labels={6: "MeO"},
        semantic_template="ester_left_allyl",
    )


def alcohol_candidate(key: str, tosylate: bool = False) -> MoleculeCandidate:
    if not tosylate:
        return _candidate_from_smiles(
            key,
            "OCC1(CC(=C)C)CCCCC1",
            drawing_smiles="[OH:5][CH2:3][C:1]1([CH2:2][C:7](=[CH2:8])[CH3:9])CCCCC1",
            right_map=2,
            display_labels={5: "HO"},
            semantic_template="alcohol_allyl",
        )
    full_smiles = "Cc1ccc(S(=O)(=O)OC[C:1]2([CH2:2]C(=C)C)CCCCC2)cc1"
    return _candidate_from_smiles(
        key,
        full_smiles,
        drawing_smiles="[*:5][CH2:3][C:1]1([CH2:2][C:7](=[CH2:8])[CH3:9])CCCCC1",
        right_map=2,
        display_labels={5: "TsO"},
        semantic_template="tosylate_allyl",
    )


def methallyl_bromide() -> MoleculeCandidate:
    # The reagent is shown above the first arrow but is not numbered.
    return _candidate_from_smiles(
        "methallyl",
        "C=C(C)CBr",
        drawing_smiles="[CH2:8]=[C:7]([CH3:9])[CH2:2][Br:11]",
        semantic_template="methallyl_reagent",
    )


def main() -> None:
    candidates = {
        "1": ester_candidate(),
        "2": allylated_candidate(),
        "3": alcohol_candidate("3"),
        "4": alcohol_candidate("4", tosylate=True),
        "methallyl": methallyl_bromide(),
    }
    style = chemdraw_compact_style()

    first_above = "1.5 equiv."
    first_below = "LDA (1.2 equiv.)\nTHF (0.5 M), -78 °C to RT"
    second_above = "LiAlH₄ (1 equiv.)"
    second_below = "Et₂O (0.25 M), RT"
    third_above = "TsCl (1.1 equiv.)\nEt₃N (2.0 equiv.)"
    third_below = "DMAP (0.15 equiv.)\nDCM, 0 °C to RT"
    clearance = 24.0

    # Top-row compounds 1 and 2 are laid out from measured molecule widths and
    # the first condition block.  The second edge intentionally wraps: its
    # continuation arrow remains on the top row, while compound 3 starts the
    # lower row as in the supplied figure.
    first_length = arrow_length_for_conditions(first_above, first_below, style)
    probe1 = MolPlace("1", (0.0, 160.0), (0.0, 0.0), "1", 0.0)
    probe2 = MolPlace("2", (0.0, 160.0), (0.0, 0.0), "2", 0.0)
    bbox1_probe = placed_molecule_bbox(candidates["1"], probe1, style)
    bbox2_probe = placed_molecule_bbox(candidates["2"], probe2, style)
    width1 = bbox1_probe[2] - bbox1_probe[0]
    width2 = bbox2_probe[2] - bbox2_probe[0]
    center1 = 130.0
    center2 = center1 + width1 / 2.0 + first_length + 2.0 * clearance + width2 / 2.0 + 2.0
    places = {
        "1": MolPlace("1", (center1, 160.0), (width1, 150.0), "1", 0.0),
        "2": MolPlace("2", (center2, 160.0), (width2, 150.0), "2", 0.0),
        "3": MolPlace("3", (155.0, 430.0), (250.0, 170.0), "3", 0.0),
        "4": MolPlace("4", (870.0, 430.0), (250.0, 170.0), "4", 0.0),
    }
    bboxes = {key: placed_molecule_bbox(candidates[key], place, style) for key, place in places.items()}
    top_baseline = shared_structure_label_baseline([bboxes["1"], bboxes["2"]], style)
    bottom_baseline = shared_structure_label_baseline([bboxes["3"], bboxes["4"]], style)
    places["1"] = MolPlace("1", places["1"].center, places["1"].box, "1", top_baseline)
    places["2"] = MolPlace("2", places["2"].center, places["2"].box, "2", top_baseline)
    places["3"] = MolPlace("3", places["3"].center, places["3"].box, "3", bottom_baseline)
    places["4"] = MolPlace("4", places["4"].center, places["4"].box, "4", bottom_baseline)
    bboxes = {key: placed_molecule_bbox(candidates[key], places[key], style) for key in places}

    arrow1 = centered_arrow_in_gap(bboxes["1"], bboxes["2"], 160.0, first_length, clearance)
    second_length = arrow_length_for_conditions(second_above, second_below, style)
    second_x1 = bboxes["2"][2] + 70.0
    arrow2 = Arrow(second_x1, 160.0, second_x1 + second_length, 160.0)
    third_length = arrow_length_for_conditions(third_above, third_below, style)
    arrow3 = centered_arrow_in_gap(bboxes["3"], bboxes["4"], 430.0, third_length, clearance)
    arrows = [arrow1, arrow2, arrow3]
    labels = []
    labels.extend(condition_labels_for_arrow(arrow1, "", first_below, style))
    labels.extend(condition_labels_for_arrow(arrow2, second_above, second_below, style))
    labels.extend(condition_labels_for_arrow(arrow3, third_above, third_below, style))
    # Treat the reagent structure and its equivalent text as one measured
    # visual block, then center that block on the arrow.  Fixed offsets center
    # the molecule alone and leave the combined condition shifted to the right.
    equiv_text = "(1.5 equiv.)"
    reagent_probe = MolPlace("methallyl", (0.0, 73.0), (0.0, 0.0), "", 0.0)
    reagent_bbox = placed_molecule_bbox(candidates["methallyl"], reagent_probe, style)
    reagent_width = reagent_bbox[2] - reagent_bbox[0]
    equiv_width = estimate_condition_text_width(
        equiv_text,
        "",
        style,
        glyph_width_factor=0.43,
    )
    reagent_text_gap = 2.0
    composite_width = reagent_width + reagent_text_gap + equiv_width
    composite_left = (arrow1.x1 + arrow1.x2) / 2.0 - composite_width / 2.0
    reagent_x = composite_left + reagent_width / 2.0
    equiv_x = composite_left + reagent_width + reagent_text_gap + equiv_width / 2.0
    reagent = MolPlace("methallyl", (reagent_x, 73.0), (reagent_width, 80.0), "", 0.0)
    places_with_reagent = list(places.values()) + [reagent]
    labels.append(Label(equiv_x, 79.0, equiv_text, "cond", style.condition_font_size))

    raw_svg = render_route_svg(
        candidates,
        places_with_reagent,
        arrows,
        labels,
        width=2400,
        height=1200,
        style=style,
    )
    svg, (_, _, width, height) = tighten_route_svg(raw_svg, padding=30.0)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_svg(SVG, svg)
    screenshot_svg(SVG, PNG, width, height)
    print(SVG)
    print(PNG)


if __name__ == "__main__":
    main()
