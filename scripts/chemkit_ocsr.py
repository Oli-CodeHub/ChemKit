#!/usr/bin/env python3
"""Reusable OCSR-to-RDKit helpers for ChemKit."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rdkit import Chem
from rdkit.Chem import rdDepictor


ABBREVIATION_LABELS: dict[str, str] = {
    "Ac": "Ac",
    "AcA": "Ac",
    "AcO": "AcO",
    "AlSO": "TMSO",
    "Bn": "Bn",
    "Bz": "Bz",
    "CHO": "CHO",
    "IO": "HO",
    "Me": "Me",
    "OB": "OBn",
    "OBn": "OBn",
    "OBz": "OBz",
    "OAc": "OAc",
    "OHC": "CHO",
    "OMe": "OMe",
    "OMs": "OMs",
    "ON": "OMs",
    "O-": "O",
    "OTES": "OTES",
    "OTBS": "OTBS",
    "OTESO": "OTES",
    "Ph": "Ph",
    "TESO": "TESO",
    "TBSO": "TBSO",
    "TMSO": "TMSO",
}

ELEMENTS = {"B", "C", "N", "O", "P", "S", "F", "Cl", "Br", "I", "Si", "H"}
CARBON_ALIASES = {"", "C", "CH", "CHH", "T", "(T)"}


@dataclass
class OcsrCandidate:
    key: str
    mol: Chem.Mol
    source_smiles: str | None
    confidence: float | None
    rdkit_status: str
    unresolved_labels: list[str] = field(default_factory=list)
    skipped_bonds: int = 0

    @property
    def is_sanitized(self) -> bool:
        return self.rdkit_status == "sanitized"

    def report_row(self) -> dict[str, Any]:
        return {
            "molscribe_confidence": self.confidence,
            "molscribe_smiles": self.source_smiles,
            "rdkit_status": self.rdkit_status,
            "atoms": self.mol.GetNumAtoms(),
            "bonds": self.mol.GetNumBonds(),
            "unresolved_labels": self.unresolved_labels,
            "skipped_bonds": self.skipped_bonds,
        }


def load_predictions(path: str | Path) -> dict[str, dict[str, Any]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def normalize_ocsr_label(symbol: str) -> str:
    raw = symbol.strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    raw = raw.replace("@", "")
    raw = re.sub(r"^\d+", "", raw)
    if raw.startswith("C"):
        raw = raw.replace("H", "")
    return raw


def atom_from_ocsr(symbol: str, unresolved: list[str]) -> Chem.Atom:
    raw = normalize_ocsr_label(symbol)
    if raw in CARBON_ALIASES:
        return Chem.Atom("C")
    if raw in ELEMENTS:
        return Chem.Atom(raw)
    if raw in ABBREVIATION_LABELS:
        label = ABBREVIATION_LABELS[raw]
        if label == "O":
            return Chem.Atom("O")
        atom = Chem.Atom(0)
        atom.SetProp("_displayLabel", label)
        return atom

    unresolved.append(raw or symbol)
    atom = Chem.Atom(0)
    atom.SetProp("_displayLabel", raw if raw and len(raw) <= 5 else "R")
    return atom


def mol_from_ocsr_prediction(key: str, prediction: dict[str, Any]) -> OcsrCandidate:
    unresolved: list[str] = []
    rw = Chem.RWMol()
    for atom_data in prediction.get("atoms", []):
        rw.AddAtom(atom_from_ocsr(atom_data.get("atom_symbol", "C"), unresolved))

    bond_types = {
        "single": Chem.BondType.SINGLE,
        "double": Chem.BondType.DOUBLE,
        "triple": Chem.BondType.TRIPLE,
        "solid wedge": Chem.BondType.SINGLE,
        "dashed wedge": Chem.BondType.SINGLE,
    }
    bond_dirs = {
        "solid wedge": Chem.BondDir.BEGINWEDGE,
        "dashed wedge": Chem.BondDir.BEGINDASH,
    }
    skipped_bonds = 0
    for bond_data in prediction.get("bonds", []):
        i, j = bond_data.get("endpoint_atoms", [None, None])
        if i is None or j is None or i >= rw.GetNumAtoms() or j >= rw.GetNumAtoms():
            skipped_bonds += 1
            continue
        try:
            rw.AddBond(int(i), int(j), bond_types.get(bond_data.get("bond_type"), Chem.BondType.SINGLE))
            bond = rw.GetBondBetweenAtoms(int(i), int(j))
            if bond_data.get("bond_type") in bond_dirs:
                bond.SetBondDir(bond_dirs[bond_data["bond_type"]])
        except RuntimeError:
            skipped_bonds += 1

    mol = rw.GetMol()
    mol.UpdatePropertyCache(strict=False)
    status = "sanitized"
    try:
        Chem.SanitizeMol(mol)
    except Exception as exc:
        status = f"unsanitized: {type(exc).__name__}: {str(exc).splitlines()[0]}"
        mol.UpdatePropertyCache(strict=False)
    rdDepictor.Compute2DCoords(mol)

    return OcsrCandidate(
        key=key,
        mol=mol,
        source_smiles=prediction.get("smiles"),
        confidence=prediction.get("confidence"),
        rdkit_status=status,
        unresolved_labels=sorted(set(filter(None, unresolved))),
        skipped_bonds=skipped_bonds,
    )


def candidates_from_predictions(predictions: dict[str, dict[str, Any]]) -> dict[str, OcsrCandidate]:
    return {key: mol_from_ocsr_prediction(key, pred) for key, pred in predictions.items()}


def summarize_candidates(candidates: dict[str, OcsrCandidate], low_confidence_cutoff: float = 0.5) -> dict[str, Any]:
    rows = {key: candidate.report_row() for key, candidate in candidates.items()}
    unsanitized = [key for key, candidate in candidates.items() if not candidate.is_sanitized]
    low_confidence = [
        key
        for key, candidate in candidates.items()
        if candidate.confidence is not None and candidate.confidence < low_confidence_cutoff
    ]
    invalid_smiles = [
        key
        for key, candidate in candidates.items()
        if not candidate.source_smiles or candidate.source_smiles == "<invalid>"
    ]
    unresolved = {
        key: candidate.unresolved_labels
        for key, candidate in candidates.items()
        if candidate.unresolved_labels
    }
    return {
        "summary": {
            "total_structures": len(candidates),
            "valid_smiles_or_mol_count": len(candidates) - len(invalid_smiles),
            "invalid_smiles_count": len(invalid_smiles),
            "sanitized_molecule_count": len(candidates) - len(unsanitized),
            "unsanitized_molecule_count": len(unsanitized),
            "low_confidence_count": len(low_confidence),
            "unresolved_label_count": sum(len(v) for v in unresolved.values()),
        },
        "invalid_smiles": invalid_smiles,
        "unsanitized_structures": unsanitized,
        "low_confidence_structures": low_confidence,
        "unresolved_labels": unresolved,
        "molecules": rows,
    }


def write_qc_report(path: str | Path, candidates: dict[str, OcsrCandidate]) -> dict[str, Any]:
    report = summarize_candidates(candidates)
    Path(path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
