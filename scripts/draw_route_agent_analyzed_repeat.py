#!/usr/bin/env python3
"""Draw the complex route from Agent-interpreted structures.

The route uses explicit structure descriptions rather than an image-recognition
engine. Variable methylene linkers are represented by real short zigzags; the
crop-selected repeat carbon receives ChemKit parentheses and an upright
external ``n`` marker.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import rdDepictor

ROOT = Path(__file__).resolve().parents[1]
SVG = ROOT / "examples/20260820-route-agent-repeat.svg"
PNG = ROOT / "examples/20260820-route-agent-repeat.png"
MANIFEST = ROOT / "examples/20260820-route-agent-repeat.json"

SMILES = {
    "1": "O=C(O)c1cc2ccccc2[nH]1",
    "3w": "O=C(c1c[nH]c2ccccc12)Sc1nccnc1",
    "2": "CC(C)(C)OC(=O)CCn1c(C(=O)Sc2nccnc2)c2ccccc2c1",
    "3": "O=C(O)CCn1c(C(=O)Sc2nccnc2)c2ccccc2c1",
    "4": "O=C1CCC(N2C(=O)c3cccc(F)c3C2=O)C(=O)N1",
    "5": "NCCCCNC(=O)OC(C)(C)C",
    "6": "CC(C)(C)OC(=O)NCCCCNc1cccc2c1C(=O)N(C1CCC(=O)NC1=O)C2=O",
    "7": "O=C(O)NCCCCNc1cccc2c1C(=O)N(C1CCC(=O)NC1=O)C2=O",
    "8": "n1(CC(=O)NCCCCNc2cccc3c2C(=O)N(C2CCC(=O)NC2=O)C3=O)c(C(=O)Sc2nccnc2)c2ccccc2c1",
}


def find_repeat_path(mol: Chem.Mol) -> list[int]:
    nitrogens = [atom for atom in mol.GetAtoms() if atom.GetSymbol() == "N"]
    def has_carbonyl_neighbor(atom: Chem.Atom) -> bool:
        for bond in atom.GetBonds():
            other = bond.GetOtherAtom(atom)
            if other.GetSymbol() != "C":
                continue
            if any(
                neighbor.GetSymbol() == "O"
                and mol.GetBondBetweenAtoms(other.GetIdx(), neighbor.GetIdx()).GetBondType() == Chem.BondType.DOUBLE
                for neighbor in other.GetNeighbors()
            ):
                return True
        return False

    candidates: list[tuple[int, int, list[int]]] = []
    for left in nitrogens:
        for right in nitrogens:
            if right == left or right.GetIsAromatic():
                continue
            right_aromatic = any(neighbor.GetIsAromatic() for neighbor in right.GetNeighbors())
            # The standalone diamine has no aromatic partner, so allow the
            # second non-aromatic N only when no aromatic N exists.
            aromatic_required = any(any(neighbor.GetIsAromatic() for neighbor in n.GetNeighbors()) for n in nitrogens)
            if aromatic_required and not right_aromatic:
                continue
            if not has_carbonyl_neighbor(left):
                continue
            path = list(Chem.rdmolops.GetShortestPath(mol, left.GetIdx(), right.GetIdx()))
            carbons = [idx for idx in path if mol.GetAtomWithIdx(idx).GetSymbol() == "C"]
            if 2 <= len(carbons) <= 6:
                candidates.append((len(carbons), left.GetIdx(), path))
    if not candidates:
        raise ValueError("Could not identify the variable linker nitrogens")
    # The screenshot convention uses a short four-carbon exemplar. Prefer
    # that path when available; shorter/longer alternatives can pass through
    # the imide or glutarimide ring rather than the linker.
    exact = [candidate for candidate in candidates if candidate[0] == 4]
    _, left_idx, path = (exact[0] if exact else min(candidates, key=lambda item: abs(item[0] - 4)))
    return [idx for idx in path if mol.GetAtomWithIdx(idx).GetSymbol() == "C"]


def prepare_molecule(key: str) -> Chem.Mol:
    mol = Chem.MolFromSmiles(SMILES[key])
    if mol is None:
        raise ValueError(f"Invalid structure {key}")
    if key in {"5", "6", "7", "8"}:
        repeat_atoms = find_repeat_path(mol)
        mol.SetProp("_chemkit_repeat_atom_indices", json.dumps(repeat_atoms))
        # The screenshot convention is -CH2-(CH2)n-CH2-.  The selected
        # carbon is explicit so the overlay does not incorrectly surround the
        # whole linker.  For this route the second linker carbon is the one
        # enclosed by parentheses in each crop.
        mol.SetProp("_chemkit_repeat_atom", str(repeat_atoms[1]))
        # Label the two linker nitrogens, while keeping the actual chain atoms
        # for the ChemKit repeat-unit overlay.
        for atom in mol.GetAtoms():
            if atom.GetIdx() in repeat_atoms:
                continue
            if atom.GetSymbol() == "N" and any(neighbor.GetIdx() in repeat_atoms for neighbor in atom.GetNeighbors()):
                atom.SetProp("_displayLabel", "H2N" if key == "5" and atom.GetIdx() == min(repeat_atoms) - 1 else "NH")
    rdDepictor.Compute2DCoords(mol)
    # Match the supplied crop for the standalone diamine: the free amine is
    # on the left and the Boc-protected amine is on the right.
    if key == "5":
        conf = mol.GetConformer()
        xs = [conf.GetAtomPosition(index).x for index in range(mol.GetNumAtoms())]
        center = (min(xs) + max(xs)) / 2
        for index in range(mol.GetNumAtoms()):
            point = conf.GetAtomPosition(index)
            conf.SetAtomPosition(index, (2 * center - point.x, point.y, point.z))
    return mol


def main() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from chemkit_model import MoleculeCandidate
    from chemkit_route_renderer import Arrow, Label, MolPlace, chemdraw_compact_style, render_route_svg, screenshot_svg, tighten_route_svg, write_svg

    molecules = {key: prepare_molecule(key) for key in SMILES}
    candidates = {key: MoleculeCandidate(key, mol, SMILES[key], 1.0, "sanitized", [], 0) for key, mol in molecules.items()}
    places = [
        MolPlace("1", (180, 260), (0, 0), "1", 500),
        MolPlace("3w", (700, 260), (0, 0), "3w", 500),
        MolPlace("2", (1260, 260), (0, 0), "2", 500),
        MolPlace("3", (1810, 260), (0, 0), "3", 500),
        MolPlace("4", (210, 720), (0, 0), "4", 980),
        MolPlace("5", (820, 720), (0, 0), "5a–5d", 980),
        MolPlace("6", (1700, 720), (0, 0), "6a–6d", 980),
        MolPlace("7", (720, 1200), (0, 0), "7", 1500),
        MolPlace("8", (1650, 1200), (0, 0), "A1–A4  n=1, 2, 6, 10", 1500),
    ]
    arrows = [Arrow(400, 275, 535, 275), Arrow(900, 275, 1050, 275), Arrow(1500, 275, 1600, 275), Arrow(1130, 735, 1320, 735), Arrow(1080, 1215, 1280, 1215)]
    labels = [
        Label(468, 245, "a", "cond", 25), Label(975, 245, "b", "cond", 25), Label(1550, 245, "c", "cond", 25),
        Label(1225, 705, "d", "cond", 25), Label(1180, 1185, "e", "cond", 25), Label(500, 755, "+", "cond", 36),
    ]
    # Logical canvas is intentionally generous; the final SVG is tightened
    # after all structures, arrows, labels, and repeat markers are present.
    svg = render_route_svg(candidates, places, arrows, labels, 2600, 1700, chemdraw_compact_style())
    svg, crop = tighten_route_svg(svg, padding=42.0)
    write_svg(SVG, svg)
    screenshot_svg(SVG, PNG, crop[2], crop[3])
    MANIFEST.write_text(json.dumps({
        "mode": "agent-analyzed-route-with-repeat-unit",
        "source_image_embedded": False,
        "analysis": "Agent visual interpretation -> explicit SMILES -> RDKit/ChemKit",
        "repeat_unit": "real short carbon zigzag with parentheses and external n",
        "structures": SMILES,
        "repeat_annotations": {
            key: {
                "linker_carbon_atom_indices": json.loads(molecules[key].GetProp("_chemkit_repeat_atom_indices")),
                "repeated_carbon_atom_index": int(molecules[key].GetProp("_chemkit_repeat_atom")),
                "notation": "-CH2-(CH2)n-CH2-",
            }
            for key in ("5", "6", "7", "8")
        },
        "outputs": {"svg": str(SVG), "png": str(PNG)},
        "tight_crop": {"x": crop[0], "y": crop[1], "width": crop[2], "height": crop[3], "scale_changed": False},
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(SVG)
    print(PNG)
    print(MANIFEST)


if __name__ == "__main__":
    main()
