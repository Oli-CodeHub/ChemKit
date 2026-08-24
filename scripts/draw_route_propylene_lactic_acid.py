#!/usr/bin/env python3
"""Draw the propene-to-lactic-acid route from the supplied reference."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import rdDepictor


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from chemkit_model import MoleculeCandidate
from chemkit_route_renderer import (
    Arrow,
    MolPlace,
    centered_arrow_in_gap,
    chemdraw_compact_style,
    condition_labels_for_arrow,
    placed_molecule_bbox,
    render_route_svg,
    screenshot_svg,
    write_svg,
)


OUT_DIR = ROOT / "examples"
SVG = OUT_DIR / "20260820-route-propylene-lactic-acid.svg"
PNG = OUT_DIR / "20260820-route-propylene-lactic-acid.png"

WIDTH = 1500
HEIGHT = 860


def candidate(key: str, smiles: str) -> MoleculeCandidate:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Could not parse {key}: {smiles}")
    Chem.SanitizeMol(mol)
    rdDepictor.Compute2DCoords(mol, canonOrient=True)
    return MoleculeCandidate(
        key=key,
        mol=mol,
        source_smiles=smiles,
        confidence=None,
        rdkit_status="sanitized",
    )


def add_step(
    candidates: dict[str, MoleculeCandidate],
    places: dict[str, MolPlace],
    arrows: list[Arrow],
    labels: list,
    left_key: str,
    right_key: str,
    above: str,
    below: str = "",
    length: float = 190.0,
) -> None:
    style = chemdraw_compact_style()
    left_place = places[left_key]
    right_place = places[right_key]
    left_bbox = placed_molecule_bbox(candidates[left_place.key], left_place, style)
    right_bbox = placed_molecule_bbox(candidates[right_place.key], right_place, style)
    arrow = centered_arrow_in_gap(
        left_bbox,
        right_bbox,
        left_place.center[1],
        length,
        minimum_clearance=22.0,
    )
    arrows.append(arrow)
    labels.extend(condition_labels_for_arrow(arrow, above=above, below=below, style=style))


def main() -> None:
    candidates = {
        "propene": candidate("propene", "C=CC"),
        "dichloride": candidate("1,2-dichloropropane", "CC(Cl)CCl"),
        "glycol": candidate("propylene glycol", "CC(O)CO"),
        "methylglyoxal": candidate("methylglyoxal", "CC(=O)C=O"),
        "pyruvic_acid": candidate("pyruvic acid", "CC(=O)C(=O)O"),
        "lactic_acid": candidate("lactic acid", "CC(O)C(=O)O"),
    }

    # The repeated intermediates are intentionally placed in both rows to
    # match the reference's convergent-looking textbook layout.
    places = {
        "propene": MolPlace("propene", (155, 145), (240, 150), "", 0),
        "dichloride": MolPlace("dichloride", (655, 145), (260, 150), "", 0),
        "glycol": MolPlace("glycol", (1160, 145), (240, 150), "", 0),
        "glycol_mid": MolPlace("glycol_mid", (170, 430), (240, 150), "", 0),
        "methylglyoxal": MolPlace("methylglyoxal", (710, 430), (250, 150), "", 0),
        "pyruvic_acid_mid": MolPlace("pyruvic_acid_mid", (1250, 430), (260, 150), "", 0),
        "pyruvic_acid": MolPlace("pyruvic_acid", (240, 710), (260, 150), "", 0),
        "lactic_acid": MolPlace("lactic_acid", (900, 710), (260, 150), "", 0),
    }

    # Alias repeated placements to the same candidate keys for the renderer.
    render_places = {
        key: MolPlace(place.key, place.center, place.box, "", 0)
        for key, place in places.items()
    }
    render_places["glycol_mid"] = MolPlace("glycol", places["glycol_mid"].center, places["glycol_mid"].box, "", 0)
    render_places["pyruvic_acid_mid"] = MolPlace(
        "pyruvic_acid", places["pyruvic_acid_mid"].center, places["pyruvic_acid_mid"].box, "", 0
    )

    arrows: list[Arrow] = []
    labels = []
    add_step(candidates, render_places, arrows, labels, "propene", "dichloride", "Cl₂")
    add_step(candidates, render_places, arrows, labels, "dichloride", "glycol", "NaOH/H₂O", "Δ")
    add_step(candidates, render_places, arrows, labels, "glycol_mid", "methylglyoxal", "O₂/Cu", "Δ")
    add_step(candidates, render_places, arrows, labels, "methylglyoxal", "pyruvic_acid_mid", "O₂", "催化剂")
    add_step(candidates, render_places, arrows, labels, "pyruvic_acid", "lactic_acid", "H₂/Ni", "Δ")

    # Only the actual placements are rendered; aliases share candidate mols.
    style = replace(
        chemdraw_compact_style(),
        route_font_family='"Arial Bold", "PingFang SC", Arial, Helvetica, sans-serif',
    )
    svg = render_route_svg(
        candidates=candidates,
        places=list(render_places.values()),
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
