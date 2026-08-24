#!/usr/bin/env python3
"""Resolve semantic emphasis requests into RDKit atom/bond selections.

The Agent can keep user-facing requests semantic (for example ``indole`` or
``thioester``). This module resolves them to explicit atom and bond indices so
the final SVG is deterministic and auditable.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from rdkit import Chem


FUNCTIONAL_GROUP_SMARTS: dict[str, str] = {
    "carbonyl": "[C](=O)",
    "amide": "[C](=O)[N]",
    "ester": "[C](=O)[O]",
    "thioester": "[C](=O)[S]",
    "carboxylic_acid": "[C](=O)[O;H1]",
    "nitrile": "[C]#[N]",
    "indole": "c1ccc2[nH]ccc2c1",
    "pyridine": "n1ccccc1",
    "imidazole": "c1ncc[nH]1",
    "pyrimidine": "n1ccnc1",
}

COLOR_MAP = {
    "red": "#C62828",
    "blue": "#1565C0",
    "green": "#2E7D32",
    "orange": "#EF6C00",
    "purple": "#6A1B9A",
    "black": "#000000",
}


@dataclass(frozen=True)
class EmphasisSpec:
    """Resolved drawable emphasis for one molecule."""

    atoms: tuple[int, ...] = ()
    bonds: tuple[int, ...] = ()
    color: str = "#C62828"
    mode: str = "bond"  # bond, atom, or group
    bond_width_multiplier: float = 2.0
    label: str = ""


def normalize_color(value: str | None) -> str:
    raw = (value or "#C62828").strip()
    if raw.lower() in COLOR_MAP:
        return COLOR_MAP[raw.lower()]
    if re.fullmatch(r"#[0-9a-fA-F]{6}", raw):
        return raw.upper()
    raise ValueError(f"Unsupported emphasis color: {value!r}; use a named color or #RRGGBB")


def hex_to_rgb(value: str) -> tuple[float, float, float]:
    color = normalize_color(value)
    return tuple(int(color[idx : idx + 2], 16) / 255.0 for idx in (1, 3, 5))


def _selector_smarts(selector: dict[str, Any]) -> str:
    selector_type = str(selector.get("type", "")).lower()
    value = selector.get("value")
    if selector_type in {"smarts", "pattern"}:
        if not value:
            raise ValueError("A SMARTS emphasis selector requires a value")
        return str(value)
    if selector_type in {"functional_group", "group", "name"}:
        key = str(value).strip().lower().replace(" ", "_")
        if key not in FUNCTIONAL_GROUP_SMARTS:
            known = ", ".join(sorted(FUNCTIONAL_GROUP_SMARTS))
            raise ValueError(f"Unknown functional group {value!r}; available: {known}")
        return FUNCTIONAL_GROUP_SMARTS[key]
    raise ValueError(f"Unsupported emphasis selector type: {selector_type!r}")


def _bonds_for_atoms(mol: Chem.Mol, atom_indices: set[int]) -> tuple[int, ...]:
    return tuple(
        bond.GetIdx()
        for bond in mol.GetBonds()
        if bond.GetBeginAtomIdx() in atom_indices and bond.GetEndAtomIdx() in atom_indices
    )


def resolve_emphasis(mol: Chem.Mol, request: dict[str, Any]) -> list[EmphasisSpec]:
    """Resolve one user/Agent request into one or more deterministic specs.

    ``request`` accepts either explicit ``atom_indices``/``bond_indices`` or a
    semantic ``selector`` with ``type`` ``functional_group`` or ``smarts``.
    Set ``match`` to an integer to choose one match, or ``all`` to highlight
    every match. Ambiguous matches default to an error so the Agent can ask
    the user instead of silently choosing a location.
    """
    style = request.get("style", request)
    color = normalize_color(style.get("color"))
    mode = str(style.get("mode", "bond")).lower()
    if mode not in {"bond", "atom", "group"}:
        raise ValueError("Emphasis mode must be bond, atom, or group")
    try:
        width = float(style.get("bond_width_multiplier", style.get("width_multiplier", 2.0)))
    except (TypeError, ValueError) as exc:
        raise ValueError("bond_width_multiplier must be numeric") from exc
    if width < 1.0 or width > 6.0:
        raise ValueError("bond_width_multiplier must be between 1.0 and 6.0")

    explicit_atoms = tuple(int(index) for index in request.get("atom_indices", ()))
    explicit_bonds = tuple(int(index) for index in request.get("bond_indices", ()))
    matches: list[tuple[int, ...]]
    if explicit_atoms or explicit_bonds:
        matches = [explicit_atoms]
    else:
        selector = request.get("selector", request)
        if not isinstance(selector, dict):
            raise ValueError("An emphasis request requires selector or atom/bond indices")
        query = Chem.MolFromSmarts(_selector_smarts(selector))
        if query is None:
            raise ValueError("Invalid SMARTS emphasis selector")
        matches = list(mol.GetSubstructMatches(query, uniquify=True))
        if not matches:
            raise ValueError("Emphasis selector matched no atoms in the molecule")
        choice = request.get("match", "error")
        if choice != "all" and len(matches) > 1:
            if isinstance(choice, int) and 0 <= choice < len(matches):
                matches = [matches[choice]]
            else:
                raise ValueError(f"Emphasis selector matched {len(matches)} locations; specify match or use match=all")

    label = str(request.get("label", request.get("selector", {}).get("value", "")))
    specs: list[EmphasisSpec] = []
    for match in matches:
        atoms = tuple(sorted(set(explicit_atoms or match)))
        bonds = tuple(sorted(set(explicit_bonds or _bonds_for_atoms(mol, set(atoms)))))
        if mode == "bond":
            # Bond emphasis also colors the visible atom glyphs at both ends.
            # Resolve those endpoints now so the SVG layer can update the
            # original RDKit glyph paths rather than adding an overlay.
            endpoint_atoms = {
                endpoint
                for bond_index in bonds
                for endpoint in (
                    mol.GetBondWithIdx(bond_index).GetBeginAtomIdx(),
                    mol.GetBondWithIdx(bond_index).GetEndAtomIdx(),
                )
            }
            atoms = tuple(sorted(endpoint_atoms))
        elif mode == "atom":
            bonds = ()
        specs.append(EmphasisSpec(atoms, tuple(sorted(set(bonds))), color, mode, width, label))
    return specs


def resolve_route_emphasis(
    candidates: dict[str, Any], requests: list[dict[str, Any]]
) -> dict[str, list[EmphasisSpec]]:
    """Resolve route requests scoped by ``molecules``/``molecule`` keys."""
    resolved: dict[str, list[EmphasisSpec]] = {}
    for request in requests:
        molecule_keys = request.get("molecules", request.get("molecule"))
        if isinstance(molecule_keys, str):
            molecule_keys = [molecule_keys]
        if not molecule_keys:
            raise ValueError("A route emphasis request needs molecule or molecules")
        for key in molecule_keys:
            if key not in candidates:
                raise ValueError(f"Emphasis target molecule not found: {key}")
            specs = resolve_emphasis(candidates[key].mol, request)
            resolved.setdefault(key, []).extend(specs)
    return resolved


def emphasis_report(resolved: dict[str, list[EmphasisSpec]]) -> dict[str, list[dict[str, Any]]]:
    """Return a JSON-safe audit record for resolved emphasis selections."""
    return {
        key: [
            {
                "label": spec.label,
                "atoms": list(spec.atoms),
                "bonds": list(spec.bonds),
                "color": spec.color,
                "mode": spec.mode,
                "bond_width_multiplier": spec.bond_width_multiplier,
            }
            for spec in specs
        ]
        for key, specs in resolved.items()
    }
