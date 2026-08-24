#!/usr/bin/env python3
"""Structural transcription helpers for the IMG_2954 route proof.

The original route-drawing script was lost from the newer checkout while its
validated proof assets remained.  These small builders keep the chemically
important graph/projection data available to tests and future render scripts:
the BCP is an explicit five-carbon graph and the sugar intermediates retain a
non-regular chair projection with source abbreviations as display labels.
"""

from __future__ import annotations

from pathlib import Path

from rdkit import Chem
from rdkit.Geometry import Point3D

from chemkit_model import MoleculeCandidate


ROOT = Path(__file__).resolve().parents[1]


def _candidate(key: str, mol: Chem.Mol, smiles: str | None = None) -> MoleculeCandidate:
    return MoleculeCandidate(key, mol, smiles, None, "sanitized")


def _label(mol: Chem.RWMol, atom_index: int, text: str) -> None:
    atom = Chem.Atom(0)
    atom.SetProp("_displayLabel", text)
    label_index = mol.AddAtom(atom)
    mol.AddBond(atom_index, label_index, Chem.BondType.SINGLE)


def _set_coords(mol: Chem.Mol, coords: list[tuple[float, float]]) -> None:
    conf = Chem.Conformer(mol.GetNumAtoms())
    for idx, (x, y) in enumerate(coords):
        conf.SetAtomPosition(idx, Point3D(x, y, 0.0))
    mol.RemoveAllConformers()
    mol.AddConformer(conf, assignId=True)


def bcp_candidates() -> dict[str, MoleculeCandidate]:
    """Return the validated BCP structures used by routes B/C.

    Atom indices 0 and 1 are the bridgeheads; 2, 3, and 4 are the three
    distinct one-carbon bridges.  There is deliberately no 0--1 bond.
    """
    rw = Chem.RWMol()
    for _ in range(5):
        rw.AddAtom(Chem.Atom("C"))
    for bridge in (2, 3, 4):
        rw.AddBond(0, bridge, Chem.BondType.SINGLE)
        rw.AddBond(bridge, 1, Chem.BondType.SINGLE)
    _label(rw, 0, "BnO")
    mol1 = rw.GetMol()
    Chem.SanitizeMol(mol1)
    _set_coords(mol1, [(0.0, 0.0), (2.0, 0.0), (1.0, 1.4), (1.0, -1.4), (1.0, 0.0), (0.0, 0.0)])

    rw20 = Chem.RWMol(mol1)
    # Keep the proof structure condensed: CCl3 is a source label, not three
    # explicit chlorine atoms.
    for atom in rw20.GetAtoms():
        if atom.HasProp("_displayLabel"):
            atom.ClearProp("_displayLabel")
    _label(rw20, 1, "CCl3")
    mol20 = rw20.GetMol()
    Chem.SanitizeMol(mol20)
    _set_coords(mol20, [(0.0, 0.0), (2.0, 0.0), (1.0, 1.4), (1.0, -1.4), (1.0, 0.0), (0.0, 0.0), (2.0, 0.0)])
    return {
        "1": _candidate("1", mol1, "C1(C2CC2)C2CC2"),
        "20": _candidate("20", mol20, "C1(C2CC2)C2CC2"),
    }


def _sugar(key: str, phase: float) -> MoleculeCandidate:
    rw = Chem.RWMol()
    for _ in range(6):
        rw.AddAtom(Chem.Atom("C"))
    for begin, end in zip(range(6), [1, 2, 3, 4, 5, 0]):
        rw.AddBond(begin, end, Chem.BondType.SINGLE)
    # These are deliberately condensed labels from the source figure.
    for idx, text in zip((0, 1, 2, 3, 4), ("BnO", "OBn", "DPMO", "OCH3", "CCl3")):
        _label(rw, idx, text)
    mol = rw.GetMol()
    Chem.SanitizeMol(mol)
    # Unequal chair-like coordinates, rather than a regular hexagon.
    coords = [
        (0.0, 0.0),
        (1.55, 0.15 + phase),
        (2.25, 1.55 + phase),
        (1.05, 2.55),
        (-0.45, 1.65 - phase),
        (-0.85, 0.55),
    ]
    coords.extend([(x + 0.35, y + 0.25) for x, y in coords[:5]])
    _set_coords(mol, coords)
    return _candidate(key, mol, "C1CCCCC1")


def sugar_17() -> MoleculeCandidate:
    return _sugar("17", 0.18)


def sugar_18() -> MoleculeCandidate:
    return _sugar("18", -0.16)


if __name__ == "__main__":
    print("BCP candidates:", ", ".join(sorted(bcp_candidates())))
    print("Sugar labels:", sorted({
        atom.GetProp("_displayLabel")
        for candidate in (sugar_17(), sugar_18())
        for atom in candidate.mol.GetAtoms()
        if atom.HasProp("_displayLabel")
    }))
