#!/usr/bin/env python3
"""Draw an ibuprofen-related industrial route from a reference screenshot."""

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
SVG = OUT_DIR / "20260719-ibuprofen-industrial-route.svg"
PNG = OUT_DIR / "20260719-ibuprofen-industrial-route.png"

WIDTH = 1240
HEIGHT = 760


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
    isobutylbenzene = mol_from_smiles("isobutylbenzene", "CC(C)Cc1ccccc1")
    acetophenone = mol_from_smiles("p_isobutylacetophenone", "CC(=O)c1ccc(CC(C)C)cc1")
    aldehyde = mol_from_smiles("aldehyde", "CC(C)Cc1ccc(C(C)C=O)cc1")
    oxime = mol_from_smiles("oxime", "CC(C)Cc1ccc(C(C)C=NO)cc1")
    ibuprofen = mol_from_smiles("ibuprofen", "CC(C)Cc1ccc(C(C)C(=O)O)cc1")

    rdDepictor.Compute2DCoords(acetophenone)
    start_delta = align_to_reference(isobutylbenzene, acetophenone)
    aldehyde_delta = align_to_reference(aldehyde, acetophenone)
    oxime_delta = align_to_reference(oxime, aldehyde)
    ibuprofen_delta = align_to_reference(ibuprofen, aldehyde)

    candidates = {
        "isobutylbenzene": candidate_from_mol("isobutylbenzene", isobutylbenzene),
        "acetophenone": candidate_from_mol("acetophenone", acetophenone),
        "aldehyde": candidate_from_mol("aldehyde", aldehyde),
        "oxime": candidate_from_mol("oxime", oxime),
        "ibuprofen": candidate_from_mol("ibuprofen", ibuprofen),
    }

    places = [
        MolPlace("isobutylbenzene", (205, 125), (320, 170), "isobutylbenzene", 232),
        MolPlace("acetophenone", (845, 125), (335, 175), "4-isobutylacetophenone", 232),
        MolPlace("aldehyde", (845, 405), (340, 180), "2-(4-isobutylphenyl)propanal", 525),
        MolPlace("oxime", (250, 395), (360, 180), "aldoxime", 525),
        MolPlace("ibuprofen", (250, 635), (360, 180), "ibuprofen", 730),
    ]
    arrows = [
        Arrow(390, 125, 635, 125),
        Arrow(845, 230, 845, 310),
        Arrow(660, 405, 450, 405),
        Arrow(660, 555, 450, 605),
    ]
    labels = [
        Label(512, 86, "Friedel-Crafts acylation", "cond", 14),
        Label(512, 152, "Ac₂O or AcCl", "cond", 14),
        Label(910, 270, "Darzens condensation", "cond", 14, anchor="start"),
        Label(910, 296, "ClCH₂COOCH(CH₃)₂", "cond", 14, anchor="start"),
        Label(910, 322, "or ClCH₂COOEt", "cond", 14, anchor="start"),
        Label(555, 376, "oximation", "cond", 14),
        Label(555, 431, "NH₂OH·HCl", "cond", 14),
        Label(555, 545, "oxidation", "cond", 14),
        Label(555, 611, "Na₂Cr₂O₇", "cond", 14),
    ]
    style = chemdraw_compact_style()

    svg = render_route_svg(candidates, places, arrows, labels, WIDTH, HEIGHT, style)
    write_svg(SVG, svg)
    screenshot_svg(SVG, PNG, WIDTH, HEIGHT)
    print(SVG)
    print(PNG)
    print(f"start core delta: {start_delta:.6f}")
    print(f"aldehyde core delta: {aldehyde_delta:.6f}")
    print(f"oxime core delta: {oxime_delta:.6f}")
    print(f"ibuprofen core delta: {ibuprofen_delta:.6f}")


if __name__ == "__main__":
    main()
