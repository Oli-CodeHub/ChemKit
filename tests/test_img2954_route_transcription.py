from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from draw_routes_img2954 import bcp_candidates, sugar_17, sugar_18


class Img2954TranscriptionTests(unittest.TestCase):
    def test_bcp_has_three_distinct_one_carbon_bridges(self) -> None:
        mol = bcp_candidates()["1"].mol
        self.assertIsNone(mol.GetBondBetweenAtoms(0, 1))
        for bridge in (2, 3, 4):
            self.assertIsNotNone(mol.GetBondBetweenAtoms(0, bridge))
            self.assertIsNotNone(mol.GetBondBetweenAtoms(1, bridge))

    def test_source_abbreviations_remain_condensed(self) -> None:
        candidates = bcp_candidates()
        labels = {
            atom.GetProp("_displayLabel")
            for candidate in candidates.values()
            for atom in candidate.mol.GetAtoms()
            if atom.HasProp("_displayLabel") and atom.GetProp("_displayLabel")
        }
        self.assertIn("BnO", labels)
        self.assertIn("CCl3", labels)
        self.assertFalse(any(atom.GetAtomicNum() == 17 for atom in candidates["20"].mol.GetAtoms()))

        sugar_labels = {
            atom.GetProp("_displayLabel")
            for candidate in (sugar_17(), sugar_18())
            for atom in candidate.mol.GetAtoms()
            if atom.HasProp("_displayLabel") and atom.GetProp("_displayLabel")
        }
        self.assertTrue({"BnO", "OBn", "DPMO", "OCH3", "CCl3"} <= sugar_labels)

    def test_pyranose_uses_non_regular_chair_projection(self) -> None:
        mol = sugar_17().mol
        conf = mol.GetConformer()
        lengths = []
        for begin, end in ((0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0)):
            a, b = conf.GetAtomPosition(begin), conf.GetAtomPosition(end)
            lengths.append(math.hypot(a.x - b.x, a.y - b.y))
        self.assertGreater(max(lengths) / min(lengths), 1.30)


if __name__ == "__main__":
    unittest.main()
