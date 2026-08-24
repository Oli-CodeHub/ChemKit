#!/usr/bin/env python3
"""Draw individually supplied screenshots from Agent visual interpretation.

This intentionally bypasses generic OCSR for the final drawing.  The Agent
interprets each isolated screenshot, writes an explicit structure description,
and ChemKit/RDKit renders the editable result.  Symbolic repeat units remain
labels instead of being guessed as a fixed chain length.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import rdDepictor

ROOT = Path(__file__).resolve().parents[1]
SVG = ROOT / "examples/20260820-agent-analyzed-structure-grid.svg"
PNG = ROOT / "examples/20260820-agent-analyzed-structure-grid.png"
MANIFEST = ROOT / "examples/20260820-agent-analyzed-structure-grid.json"


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


def with_repeat_label(mol: Chem.Mol, key: str) -> Chem.Mol:
    """Replace one guessed linker carbon with an editable ``(CH2)n`` label."""
    if key == "5":
        mol = Chem.MolFromSmiles("NCCCCNC(=O)OC(C)(C)C")
        assert mol is not None
        mol.GetAtomWithIdx(0).SetProp("_displayLabel", "H2N")
        mol.GetAtomWithIdx(5).SetProp("_displayLabel", "NH")
        repeat = mol.GetAtomWithIdx(2)
    else:
        mol = Chem.MolFromSmiles(SMILES[key])
        assert mol is not None
        nitrogens = [atom for atom in mol.GetAtoms() if atom.GetSymbol() == "N"]
        linker_n = [atom for atom in nitrogens if any(neighbor.GetSymbol() == "C" for neighbor in atom.GetNeighbors())]
        if linker_n:
            linker_n[0].SetProp("_displayLabel", "NH")
        aromatic_n = next((atom for atom in nitrogens if any(neighbor.GetIsAromatic() for neighbor in atom.GetNeighbors())), None)
        if aromatic_n is not None:
            aromatic_n.SetProp("_displayLabel", "NH")
        if not linker_n or aromatic_n is None:
            return mol
        path = list(Chem.rdmolops.GetShortestPath(mol, linker_n[0].GetIdx(), aromatic_n.GetIdx()))
        carbon_path = [idx for idx in path if mol.GetAtomWithIdx(idx).GetSymbol() == "C"]
        repeat = mol.GetAtomWithIdx(carbon_path[len(carbon_path) // 2]) if carbon_path else None
    if repeat is not None:
        repeat.SetAtomicNum(0)
        repeat.SetNoImplicit(True)
        repeat.SetProp("_displayLabel", "(CH2)n")
    return mol


def main() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from chemkit_model import MoleculeCandidate
    from chemkit_route_renderer import Label, MolPlace, chemdraw_compact_style, render_route_svg, screenshot_svg, write_svg

    structures: dict[str, Chem.Mol] = {}
    notes: dict[str, str] = {
        "1": "indole-2-carboxylic acid",
        "3w": "indole-2-carbonyl thio-pyrimidine analogue",
        "2": "N-(tert-butoxycarbonyl-propyl) thio-pyrimidine analogue",
        "3": "acid analogue of 2",
        "4": "fluorinated phthalimide/glutarimide scaffold",
        "5": "H2N-(CH2)n-NH-Boc; repeat unit kept symbolic",
        "6": "Boc linker attached to phthalimide/glutarimide scaffold",
        "7": "acid linker attached to phthalimide/glutarimide scaffold",
        "8": "indole-thio-pyrimidine linker conjugate",
    }
    for key, smiles in SMILES.items():
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            raise ValueError(f"Could not parse Agent structure {key}: {smiles}")
        structures[key] = mol
    structures["5"] = with_repeat_label(structures["5"], "5")
    structures["6"] = with_repeat_label(structures["6"], "6")
    structures["7"] = with_repeat_label(structures["7"], "7")
    for mol in structures.values():
        mol.UpdatePropertyCache(strict=False)
        rdDepictor.Compute2DCoords(mol)

    candidates = {
        key: MoleculeCandidate(key, mol, SMILES.get(key), 1.0, "sanitized", [], 0)
        for key, mol in structures.items()
    }
    columns = [380, 1200, 2020]
    rows = [260, 760, 1260]
    keys = ["1", "3w", "2", "3", "4", "5", "6", "7", "8"]
    places = []
    for idx, key in enumerate(keys):
        row, col = divmod(idx, 3)
        places.append(MolPlace(key, (columns[col], rows[row]), (0, 0), key, rows[row] + 230))
    labels = [Label(1200, 55, "Agent visual analysis → ChemKit redraw", "cond", 25)]
    svg = render_route_svg(candidates, places, [], labels, 2400, 1550, chemdraw_compact_style())
    write_svg(SVG, svg)
    screenshot_svg(SVG, PNG, 2400, 1550)
    MANIFEST.write_text(json.dumps({
        "mode": "agent-visual-analysis-redraw",
        "source_image_embedded": False,
        "structures": notes,
        "repeat_unit_policy": "(CH2)n kept as editable label; no chain length guessed",
        "uncertainty": ["heteroaromatic ring assignment and attachment positions should be checked before publication"],
        "outputs": {"svg": str(SVG), "png": str(PNG)},
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(SVG)
    print(PNG)
    print(MANIFEST)


if __name__ == "__main__":
    main()
