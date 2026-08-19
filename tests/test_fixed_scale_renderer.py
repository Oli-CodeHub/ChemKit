#!/usr/bin/env python3
"""Regression checks for ChemKit fixed-scale and dual-fragment depiction."""

from __future__ import annotations

import math
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from chemkit_route_renderer import (
    MolPlace,
    centered_arrow_in_gap,
    chemdraw_compact_style,
    draw_mol_svg_at_fixed_scale,
    horizontal_gap_center,
    placed_molecule_bbox,
    shared_structure_label_baseline,
)
from draw_route_fat_amide_coupling import (
    apply_acid_template,
    apply_aniline_template,
    build_dual_fragment_product,
    candidate,
)


def prepared_molecules():
    acid = candidate("acid", "O=C(O)C1CCC1", "O=C(O)C1CCC1").mol
    aniline = candidate("aniline", "Nc1cccc(*)c1", "Nc1cccc(C#N)c1", True).mol
    product = candidate(
        "product",
        "O=C(Nc1cccc(*)c1)C1CCC1",
        "O=C(Nc1cccc(C#N)c1)C1CCC1",
        True,
    ).mol
    apply_acid_template(acid)
    apply_aniline_template(aniline)
    build_dual_fragment_product(acid, aniline, product)
    return acid, aniline, product


class FixedScaleRendererTests(unittest.TestCase):
    def test_effective_bond_lengths_match(self) -> None:
        style = chemdraw_compact_style()
        lengths = [draw_mol_svg_at_fixed_scale(mol, style)[2] for mol in prepared_molecules()]
        self.assertLess((max(lengths) - min(lengths)) / max(lengths), 0.02)

    def test_product_copies_both_reactant_fragments(self) -> None:
        acid, aniline, product = prepared_molecules()
        acid_conf = acid.GetConformer()
        aniline_conf = aniline.GetConformer()
        product_conf = product.GetConformer()

        for acid_idx, product_idx in {0: 0, 1: 1, 3: 10, 4: 11, 5: 12, 6: 13}.items():
            self.assertLess(
                acid_conf.GetAtomPosition(acid_idx).Distance(
                    product_conf.GetAtomPosition(product_idx)
                ),
                1e-6,
            )

        target_n = product_conf.GetAtomPosition(2)
        source_n = aniline_conf.GetAtomPosition(0)
        dx = target_n.x - source_n.x
        dy = target_n.y - source_n.y
        for aniline_idx, product_idx in {0: 2, 1: 3, 2: 4, 3: 5, 4: 6, 5: 7, 6: 8, 7: 9}.items():
            source = aniline_conf.GetAtomPosition(aniline_idx)
            copied = product_conf.GetAtomPosition(product_idx)
            self.assertAlmostEqual(source.x + dx, copied.x, places=6)
            self.assertAlmostEqual(source.y + dy, copied.y, places=6)

    def test_cyclobutane_template_is_square(self) -> None:
        acid, _, _ = prepared_molecules()
        conf = acid.GetConformer()
        center = conf.GetAtomPosition(3)
        left = conf.GetAtomPosition(4)
        lower = conf.GetAtomPosition(6)
        first = (left.x - center.x, left.y - center.y)
        second = (lower.x - center.x, lower.y - center.y)
        dot = first[0] * second[0] + first[1] * second[1]
        first_length = math.hypot(*first)
        second_length = math.hypot(*second)
        cosine = dot / (first_length * second_length)
        self.assertAlmostEqual(cosine, 0.0, places=3)
        self.assertAlmostEqual(first_length, second_length, places=3)

    def test_route_operators_use_visible_molecule_gaps(self) -> None:
        acid, aniline, product = prepared_molecules()
        style = chemdraw_compact_style()
        candidates = {
            "acid": candidate("acid", "O=C(O)C1CCC1", "O=C(O)C1CCC1"),
            "aniline": candidate("aniline", "Nc1cccc(*)c1", "Nc1cccc(C#N)c1", True),
            "product": candidate(
                "product",
                "O=C(Nc1cccc(*)c1)C1CCC1",
                "O=C(Nc1cccc(C#N)c1)C1CCC1",
                True,
            ),
        }
        candidates["acid"].mol = acid
        candidates["aniline"].mol = aniline
        candidates["product"].mol = product
        places = {
            "acid": MolPlace("acid", (76, 100), (140, 120), "FAT-1a", 0),
            "aniline": MolPlace("aniline", (260, 100), (145, 135), "FAT-2a", 0),
            "product": MolPlace("product", (675, 100), (225, 155), "FAT-3a", 0),
        }
        bboxes = {
            key: placed_molecule_bbox(candidates[key], places[key], style)
            for key in places
        }

        plus_x = horizontal_gap_center(bboxes["acid"], bboxes["aniline"])
        self.assertAlmostEqual(
            plus_x - bboxes["acid"][2],
            bboxes["aniline"][0] - plus_x,
            places=6,
        )

        arrow = centered_arrow_in_gap(
            bboxes["aniline"], bboxes["product"], 100, 200, minimum_clearance=15
        )
        self.assertAlmostEqual(
            arrow.x1 - bboxes["aniline"][2],
            bboxes["product"][0] - arrow.x2,
            places=6,
        )
        baseline = shared_structure_label_baseline(list(bboxes.values()), style)
        self.assertAlmostEqual(
            baseline - max(bbox[3] for bbox in bboxes.values()),
            style.structure_label_baseline_padding,
            places=6,
        )


if __name__ == "__main__":
    unittest.main()
