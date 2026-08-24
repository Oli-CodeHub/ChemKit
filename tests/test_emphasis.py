from __future__ import annotations

import sys
import re
import unittest

from rdkit import Chem
from rdkit.Chem import rdDepictor

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from chemkit_emphasis import resolve_emphasis
from chemkit_route_renderer import chemdraw_compact_style, draw_mol_svg


class EmphasisTests(unittest.TestCase):
    def test_semantic_amide_selection_resolves_atoms_and_bonds(self) -> None:
        mol = Chem.MolFromSmiles("CC(=O)NCC")
        assert mol is not None
        specs = resolve_emphasis(
            mol,
            {
                "selector": {"type": "functional_group", "value": "amide"},
                "mode": "group",
                "color": "red",
            },
        )
        self.assertEqual(specs[0].atoms, (1, 2, 3))
        self.assertEqual(specs[0].bonds, (1, 2))
        self.assertEqual(specs[0].color, "#C62828")

    def test_ambiguous_selector_requires_explicit_choice(self) -> None:
        mol = Chem.MolFromSmiles("CC(=O)NCC(=O)N")
        assert mol is not None
        with self.assertRaisesRegex(ValueError, "matched 2 locations"):
            resolve_emphasis(
                mol,
                {"selector": {"type": "functional_group", "value": "carbonyl"}},
            )
        self.assertEqual(
            len(
                resolve_emphasis(
                    mol,
                    {
                        "selector": {"type": "functional_group", "value": "carbonyl"},
                        "match": "all",
                    },
                )
            ),
            2,
        )

    def test_svg_contains_emphasis_color(self) -> None:
        mol = Chem.MolFromSmiles("CC(=O)NCC")
        assert mol is not None
        rdDepictor.Compute2DCoords(mol)
        specs = resolve_emphasis(
            mol,
            {
                "selector": {"type": "functional_group", "value": "amide"},
                "mode": "bond",
                "color": "#1565C0",
            },
        )
        svg = draw_mol_svg(mol, 800, 500, chemdraw_compact_style(), specs)
        self.assertIn("#1565C0", svg)
        selected_paths = re.findall(r"<path class='bond-(?:1|2)[^>]*style='([^']*)'", svg)
        self.assertTrue(selected_paths)
        self.assertTrue(all("stroke:#1565C0" in style for style in selected_paths))
        self.assertTrue(all("stroke:#000000" not in style for style in selected_paths))
        self.assertTrue(all("stroke-width:4.00px" in style for style in selected_paths))
        # The selected amide bonds end at O/N glyphs; those visible endpoints
        # must inherit the same colour instead of remaining black.
        for atom_index in (2, 3):
            glyph = re.search(
                rf"<path class='atom-{atom_index}'.*?fill='([^']+)'",
                svg,
                re.S,
            )
            self.assertIsNotNone(glyph)
            self.assertEqual(glyph.group(1), "#1565C0")

    def test_explicit_bond_selection_reports_endpoint_atoms(self) -> None:
        mol = Chem.MolFromSmiles("CO")
        assert mol is not None
        specs = resolve_emphasis(
            mol,
            {
                "bond_indices": [0],
                "mode": "bond",
                "color": "#008C8C",
            },
        )
        self.assertEqual(specs[0].atoms, (0, 1))

    def test_group_emphasis_recolors_atom_glyph_without_overlay(self) -> None:
        mol = Chem.MolFromSmiles("CO")
        assert mol is not None
        rdDepictor.Compute2DCoords(mol)
        specs = resolve_emphasis(
            mol,
            {
                "atom_indices": [1],
                "mode": "group",
                "color": "#008C8C",
            },
        )
        svg = draw_mol_svg(mol, 800, 500, chemdraw_compact_style(), specs)
        oxygen = re.search(r"<path class='atom-1'.*?fill='([^']+)'", svg, re.S)
        self.assertIsNotNone(oxygen)
        self.assertEqual(oxygen.group(1), "#008C8C")
        self.assertNotIn("<ellipse", svg)


if __name__ == "__main__":
    unittest.main()
