#!/usr/bin/env python3
"""Draw (S)-citronellal terminal methyl oxidation."""

from __future__ import annotations

from pathlib import Path
import sys

from rdkit import Chem
from rdkit.Chem import rdDepictor, rdFMCS

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from chemkit_ocsr import OcsrCandidate
from chemkit_route_renderer import Arrow, Label, MolPlace, chemdraw_compact_style, render_route_svg, screenshot_svg, write_svg


ROOT = Path("/Users/yl/Desktop/skills/ChemKit")
OUT_DIR = ROOT / "examples"
SVG = OUT_DIR / "20260719-s-citronellal-terminal-methyl-oxidation.svg"
PNG = OUT_DIR / "20260719-s-citronellal-terminal-methyl-oxidation.png"

WIDTH = 1180
HEIGHT = 235


def mol_from_smiles(key: str, smiles: str) -> Chem.Mol:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Could not parse SMILES for {key}: {smiles}")
    return mol


def align_to_reference(mol: Chem.Mol, reference: Chem.Mol) -> float:
    mcs = rdFMCS.FindMCS(
        [reference, mol],
        matchValences=False,
        ringMatchesRingOnly=False,
        completeRingsOnly=False,
        timeout=5,
    )
    if not mcs.smartsString:
        rdDepictor.Compute2DCoords(mol)
        return float("inf")

    patt = Chem.MolFromSmarts(mcs.smartsString)
    ref_match = reference.GetSubstructMatch(patt)
    mol_match = mol.GetSubstructMatch(patt)
    if not ref_match or not mol_match:
        rdDepictor.Compute2DCoords(mol)
        return float("inf")

    rdDepictor.GenerateDepictionMatching2DStructure(mol, reference, refPatt=patt)
    ref_conf = reference.GetConformer()
    mol_conf = mol.GetConformer()
    return max(
        (
            (ref_conf.GetAtomPosition(ref_idx).x - mol_conf.GetAtomPosition(mol_idx).x) ** 2
            + (ref_conf.GetAtomPosition(ref_idx).y - mol_conf.GetAtomPosition(mol_idx).y) ** 2
        )
        ** 0.5
        for ref_idx, mol_idx in zip(ref_match, mol_match)
    )


def candidate_from_mol(key: str, mol: Chem.Mol) -> OcsrCandidate:
    return OcsrCandidate(
        key=key,
        mol=mol,
        source_smiles=Chem.MolToSmiles(mol, isomericSmiles=True),
        confidence=None,
        rdkit_status="sanitized",
    )


def main() -> None:
    s_citronellal = mol_from_smiles("s_citronellal", "CC(C)=CCC[C@H](C)CC=O")
    hydroxy_product = mol_from_smiles("hydroxy_product", "OCC(C)=CCC[C@H](C)CC=O")
    aldehyde_product = mol_from_smiles("aldehyde_product", "O=CC(C)=CCC[C@H](C)CC=O")

    rdDepictor.Compute2DCoords(s_citronellal)
    hydroxy_delta = align_to_reference(hydroxy_product, s_citronellal)
    aldehyde_delta = align_to_reference(aldehyde_product, s_citronellal)

    candidates = {
        "s_citronellal": candidate_from_mol("s_citronellal", s_citronellal),
        "hydroxy_product": candidate_from_mol("hydroxy_product", hydroxy_product),
        "aldehyde_product": candidate_from_mol("aldehyde_product", aldehyde_product),
    }

    places = [
        MolPlace("s_citronellal", (170, 106), (295, 150), "(S)-citronellal", 202),
        MolPlace("hydroxy_product", (695, 106), (300, 150), "8-hydroxycitronellal", 202),
        MolPlace("aldehyde_product", (1010, 106), (300, 150), "8-oxocitronellal", 202),
    ]
    arrows = [Arrow(345, 106, 555, 106)]
    labels = [
        Label(450, 82, "TBHP, salicylic acid", "cond", 14),
        Label(450, 129, "DCM, 48 h", "cond", 14),
        Label(850, 112, "+", "cond", 22),
    ]
    style = chemdraw_compact_style()

    svg = render_route_svg(candidates, places, arrows, labels, WIDTH, HEIGHT, style)
    write_svg(SVG, svg)
    screenshot_svg(SVG, PNG, WIDTH, HEIGHT)
    print(SVG)
    print(PNG)
    print(f"hydroxy core delta: {hydroxy_delta:.6f}")
    print(f"aldehyde core delta: {aldehyde_delta:.6f}")


if __name__ == "__main__":
    main()
