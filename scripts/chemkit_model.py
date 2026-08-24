#!/usr/bin/env python3
"""Small neutral molecule container shared by ChemKit renderers.

The renderer only needs a molecule plus a little provenance/QC state.  Keeping
that container independent of any image-recognition backend lets ChemKit draw
hand-transcribed, SMILES, and programmatically assembled structures without
bringing an optional recognition backend into the core skill.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rdkit import Chem


@dataclass
class MoleculeCandidate:
    """Drawable molecule and provenance used by the route renderer."""

    key: str
    mol: Chem.Mol
    source_smiles: str | None = None
    confidence: float | None = None
    rdkit_status: str = "sanitized"
    unresolved_labels: list[str] = field(default_factory=list)
    skipped_bonds: int = 0

    @property
    def is_sanitized(self) -> bool:
        return self.rdkit_status == "sanitized"

    def report_row(self) -> dict[str, object]:
        """Return a backend-neutral QC record suitable for JSON manifests."""
        return {
            "source_smiles": self.source_smiles,
            "rdkit_status": self.rdkit_status,
            "atoms": self.mol.GetNumAtoms(),
            "bonds": self.mol.GetNumBonds(),
            "unresolved_labels": list(self.unresolved_labels),
            "skipped_bonds": self.skipped_bonds,
        }
