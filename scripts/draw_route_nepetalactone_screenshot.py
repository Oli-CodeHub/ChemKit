#!/usr/bin/env python3
"""Redraw the supplied citronellal/nepetalactone route with ChemKit.

The structures are Agent-transcribed from isolated visual regions of the
provided figure. The source pixels are not embedded in the output.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import rdDepictor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from chemkit_model import MoleculeCandidate
from chemkit_route_renderer import (
    Arrow,
    BracketOperation,
    Label,
    MolPlace,
    chemdraw_compact_style,
    condition_labels_for_arrow,
    condition_labels_for_bracket,
    render_route_svg,
    screenshot_svg,
    tighten_route_svg,
    write_svg,
)


SMILES = {
    # Folded depiction of citronellal; the chain is open, not a ring.
    "II-1": "CC(C)=CCC[C@H](C)CC=O",
    "II-2": "O=CCC[C@H](C)CCC=C(C)CO",
    "II-3": "O=CCC[C@H](C)CCC=C(C)C=O",
    # Fused cyclopentane/pyran skeleton transcribed from II-4, II-A and II-B.
    "II-4": "[C@@H]12[C@@H](C)CC[C@@H]1C(C)=CO[C@@H]2N(C)c3ccccc3",
    "II-A": "[C@@H]12[C@@H](C)CC[C@@H]1C(C)=CO[C@@H]2O",
    "II-B": "[C@@H]12[C@@H](C)CC[C@@H]1C(C)=COC2=O",
}

SVG = ROOT / "examples/20260820-nepetalactone-screenshot-redraw.svg"
PNG = ROOT / "examples/20260820-nepetalactone-screenshot-redraw.png"
MANIFEST = ROOT / "examples/20260820-nepetalactone-screenshot-redraw.json"


# These are semantic source mappings, not renderer-order guesses.  Each pair
# identifies the bond that represents one visible hashed wedge in the source
# crop; II-B uses the bridgehead-to-carbonyl bond for its top-right mark.
SOURCE_STEREO_BONDS = {
    "II-4": {
        "left_methyl": (1, 2),
        "upper_bridgehead": (5, 4),
        "top_right_substituent": (10, 11),
        "lower_bridgehead": (0, 1),
    },
    "II-A": {
        "left_methyl": (1, 2),
        "upper_bridgehead": (5, 4),
        "top_right_substituent": (10, 11),
        "lower_bridgehead": (0, 1),
    },
    "II-B": {
        "left_methyl": (1, 2),
        "upper_bridgehead": (5, 4),
        "top_right_substituent": (0, 10),
        "lower_bridgehead": (0, 1),
    },
}


def candidate(key: str, smiles: str) -> MoleculeCandidate:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid structure {key}: {smiles}")
    rdDepictor.Compute2DCoords(mol)
    if key in {"II-4", "II-A", "II-B"}:
        # Normalize the fused skeleton from its atom graph, rather than using
        # one hard-coded angle for every analogue.  Atoms 0 and 5 are the two
        # bridgeheads in these explicit SMILES.  A vertical shared bond leaves
        # the cyclopentane on the left and the pyran/lactone ring on the right,
        # matching the isolated ChemDraw crops.
        conf = mol.GetConformer()
        p0, p5 = conf.GetAtomPosition(0), conf.GetAtomPosition(5)
        current_angle = math.atan2(p5.y - p0.y, p5.x - p0.x)
        theta = math.radians(90.0) - current_angle
        cos_theta, sin_theta = math.cos(theta), math.sin(theta)
        for index in range(mol.GetNumAtoms()):
            point = conf.GetAtomPosition(index)
            conf.SetAtomPosition(
                index,
                (
                    cos_theta * point.x - sin_theta * point.y,
                    sin_theta * point.x + cos_theta * point.y,
                    point.z,
                ),
            )

        # The source places the key top-right substituent above the bridgehead
        # (N-phenyl in II-4, OH in II-A, carbonyl in II-B).  RDKit's equivalent
        # depiction puts that substituent below after normalization, so mirror
        # all three fused conformers vertically around their centroid.
        if key in {"II-4", "II-A", "II-B"}:
            points = [conf.GetAtomPosition(i) for i in range(mol.GetNumAtoms())]
            y_mid = sum(point.y for point in points) / len(points)
            for index, point in enumerate(points):
                conf.SetAtomPosition(index, (point.x, 2 * y_mid - point.y, point.z))
        # Recompute wedge/dash directions after the final coordinate transform.
        # A post-depiction mirror without this step can make a chemically
        # chiral SMILES look like the opposite diastereomer on the page.
        Chem.WedgeMolBonds(mol, conf)
        # The supplied ChemDraw crop uses hashed wedges for the four visible
        # stereochemical marks on this scaffold (the methyl, both bridgehead
        # H marks, and the top-right substituent).  Keep the chiral tags in the
        # molecule, but normalize the final drawing directions to that source
        # convention after the coordinates are fixed.
        stereo_roles = SOURCE_STEREO_BONDS[key]
        for role, (begin, end) in stereo_roles.items():
            bond = mol.GetBondBetweenAtoms(begin, end)
            if bond is None:
                raise ValueError(f"Missing mapped stereo bond {key}: {begin}-{end}")
            bond.SetBondDir(Chem.BondDir.BEGINDASH)
            # The source shows direct hashed bonds to the two bridgehead H
            # labels.  Do not let RDKit encode those implicit H marks by
            # wedging an adjacent ring bond; the renderer adds the explicit
            # short H hash after the final coordinates are known.
            if role in {"upper_bridgehead", "lower_bridgehead"}:
                bond.SetBondDir(Chem.BondDir.NONE)
        mol.SetProp("_chemkit_stereo_roles", json.dumps(stereo_roles, sort_keys=True))
        mol.SetProp("_chemkit_stereo_h_atoms", json.dumps({"0": [0, -1], "5": [0, 1]}))
    return MoleculeCandidate(key, mol, smiles, 1.0, "sanitized", [], 0)


def main() -> None:
    candidates = {key: candidate(key, smiles) for key, smiles in SMILES.items()}
    places = [
        MolPlace("II-1", (180, 300), (0, 0), "II-1", 500),
        MolPlace("II-2", (700, 300), (0, 0), "II-2", 500),
        MolPlace("II-3", (960, 300), (0, 0), "II-3", 500),
        MolPlace("II-4", (1510, 300), (0, 0), "II-4", 500),
        # The second row is a wrapped continuation of II-4 and starts with a
        # horizontal incoming arrow at the left, as in the source figure.
        MolPlace("II-A", (700, 760), (0, 0), "II-A", 960),
        MolPlace("II-B", (1400, 760), (0, 0), "II-B", 960),
    ]
    arrows = [
        Arrow(335, 300, 540, 300),
        Arrow(1060, 300, 1320, 300),
        # Continuation of II-4 on the wrapped second row.
        Arrow(120, 760, 500, 760),
        Arrow(900, 760, 1120, 760),
    ]
    bracket_operations = [
        # DMP oxidizes the alcohol II-2 to the aldehyde II-3.  The plus sign
        # above remains the mixture marker from the preceding SeO₂ step.
        BracketOperation(570, 960, 100, 155, 220),
    ]
    style = chemdraw_compact_style()
    labels = [
        *condition_labels_for_arrow(
            arrows[0],
            above="SeO₂ (3 mol %)\nt-BuOOH\nsalicylic acid",
            below="CH₂Cl₂, r.t.\n40–50%",
            style=style,
        ),
        *condition_labels_for_arrow(
            arrows[1],
            above="MeNHPh, 4 Å MS",
            below="Et₂O, Ar, r.t.\n80%",
            style=style,
        ),
        *condition_labels_for_arrow(
            arrows[2],
            above="TsOH·H₂O\nTHF:H₂O (9:1), r.t.\n80%",
            style=style,
        ),
        *condition_labels_for_arrow(
            arrows[3],
            above="TPAP (5 mol %), NMO\n4 Å MS, CH₂Cl₂, Ar, r.t.\n85%",
            style=style,
        ),
        *condition_labels_for_bracket(
            bracket_operations[0],
            above="DMP\nCH₂Cl₂, r.t.\n85%",
            style=style,
        ),
        Label(830, 315, "+", "cond", 34),
        Label(180, 535, "citronellal", "cond", 25),
        Label(700, 1000, "nepetalactol", "cond", 25),
        Label(1400, 1000, "nepetalactone", "cond", 25),
    ]
    # Use a generous logical canvas, then crop only after all route primitives
    # have been drawn. This preserves the fixed molecular scale.
    svg = render_route_svg(
        candidates,
        places,
        arrows,
        labels,
        2200,
        1200,
        style,
        bracket_operations=bracket_operations,
    )
    svg, crop = tighten_route_svg(svg, padding=44.0)
    write_svg(SVG, svg)
    screenshot_svg(SVG, PNG, crop[2], crop[3])
    MANIFEST.write_text(
        json.dumps(
            {
                "mode": "agent-visual-transcription",
                "source_image_embedded": False,
                "analysis": "Agent visual interpretation -> explicit SMILES -> RDKit/ChemKit",
                "structures": SMILES,
                "route_manifest": {
                    "rows": [
                        ["II-1", "II-2", "II-3", "II-4"],
                        ["II-A", "II-B"],
                    ],
                    "edges": [
                        {"from": "II-1", "to": ["II-2", "II-3"], "kind": "mixture"},
                        {"from": "II-2", "to": ["II-3"], "condition": "DMP; CH₂Cl₂, r.t.; 85%"},
                        {"from": "II-3", "to": ["II-4"], "condition": "MeNHPh, 4 Å MS; Et₂O, Ar, r.t.; 80%"},
                        {"from": "II-4", "to": ["II-A"], "condition": "TsOH·H₂O; THF:H₂O (9:1), r.t.; 80%", "wrapped": True},
                        {"from": "II-A", "to": ["II-B"], "condition": "TPAP (5 mol %), NMO; 4 Å MS, CH₂Cl₂, Ar, r.t.; 85%"},
                    ],
                },
                "stereo_mapping": "Fused products use explicit chiral SMILES and semantic source bond roles; final coordinates are fixed before RDKit wedge assignment, with direct hashed H marks rendered by stereo_h_overlay.",
                "uncertainties": [
                    "Absolute stereochemical identities should be confirmed against the source structure names before publication.",
                    "Top-chain conformations are connectivity-faithful Agent transcriptions and may need local 2D conformation tuning for exact ChemDraw matching.",
                ],
                "tight_crop": {"x": crop[0], "y": crop[1], "width": crop[2], "height": crop[3]},
                "outputs": {"svg": str(SVG), "png": str(PNG)},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(SVG)
    print(PNG)
    print(MANIFEST)


if __name__ == "__main__":
    main()
