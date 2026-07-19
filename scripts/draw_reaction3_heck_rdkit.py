#!/usr/bin/env python3
"""Draw Reaction 3 Routine Heck Reaction with RDKit and bbox-driven layout."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import rdDepictor
from rdkit.Chem.Draw import rdMolDraw2D


OUT = Path("/Users/yl/Desktop/skills/ChemKit/examples/20260625-reaction-3-routine-heck-rdkit-v3.svg")
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

TEMP_W = 1200
TEMP_H = 500
BOND_WIDTH = 1.55
ATOM_FONT = 11
FIXED_BOND = 17

TOP_PAD = 22
LEFT_PAD = 24
RIGHT_PAD = 140
BOTTOM_PAD = 24
BASELINE_Y = 96
GAP_STRUCTURE_PLUS = 24
GAP_PLUS_STRUCTURE = 24
GAP_STRUCTURE_ARROW = 40
GAP_ARROW_PRODUCT = 48
MIN_ARROW_LEN = 105
ARROW_TEXT_OVERHANG = 46
COND_CHAR_WIDTH = 6.1


MOLECULES = [
    ("aryl chloride", "CC(C)(C)OC(=O)Nc1ccc(Cl)nn1"),
    ("butyl acrylate", "C=CC(=O)OCCCC"),
    ("heck product", "CC(C)(C)OC(=O)Nc1ccc(/C=C/C(=O)OCCCC)nn1"),
]


@dataclass
class MolSvg:
    name: str
    smiles: str
    body: str
    bbox: tuple[float, float, float, float]

    @property
    def width(self) -> float:
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> float:
        return self.bbox[3] - self.bbox[1]


def strip_svg_shell(svg: str) -> str:
    svg = re.sub(r"^.*?<svg[^>]*>", "", svg, flags=re.S)
    svg = re.sub(r"</svg>\s*$", "", svg, flags=re.S)
    svg = re.sub(r"<rect[^>]+fill=['\"]#FFFFFF['\"][^>]*/>\s*", "", svg)
    return svg


def path_bbox(svg_body: str) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []

    for d in re.findall(r"\sd=['\"]([^'\"]+)['\"]", svg_body):
        nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", d)]
        for i in range(0, len(nums) - 1, 2):
            xs.append(nums[i])
            ys.append(nums[i + 1])

    for tag in re.findall(r"<(?:circle|ellipse|rect)\b[^>]*>", svg_body):
        attrs = dict(re.findall(r"([a-zA-Z]+)=['\"]([^'\"]+)['\"]", tag))
        if "cx" in attrs and "cy" in attrs:
            cx = float(attrs["cx"])
            cy = float(attrs["cy"])
            r = float(attrs.get("r") or attrs.get("rx") or 0)
            xs.extend([cx - r, cx + r])
            ys.extend([cy - r, cy + r])
        elif "x" in attrs and "y" in attrs and "width" in attrs and "height" in attrs:
            x = float(attrs["x"])
            y = float(attrs["y"])
            w = float(attrs["width"])
            h = float(attrs["height"])
            xs.extend([x, x + w])
            ys.extend([y, y + h])

    if not xs or not ys:
        raise ValueError("Could not calculate molecule SVG bbox")

    pad = 4.0
    return min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad


def draw_molecule(name: str, smiles: str) -> MolSvg:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Bad SMILES for {name}: {smiles}")

    rdDepictor.Compute2DCoords(mol)
    drawer = rdMolDraw2D.MolDraw2DSVG(TEMP_W, TEMP_H)
    opts = drawer.drawOptions()
    opts.clearBackground = False
    opts.useBWAtomPalette()
    opts.fontFile = FONT
    opts.fixedFontSize = ATOM_FONT
    opts.minFontSize = ATOM_FONT
    opts.maxFontSize = ATOM_FONT
    opts.bondLineWidth = BOND_WIDTH
    opts.fixedBondLength = FIXED_BOND
    opts.multipleBondOffset = 0.16
    opts.padding = 0.02
    opts.additionalAtomLabelPadding = 0.02
    opts.scaleBondWidth = False
    opts.singleColourWedgeBonds = True

    rdMolDraw2D.PrepareAndDrawMolecule(drawer, mol)
    drawer.FinishDrawing()
    body = strip_svg_shell(drawer.GetDrawingText())
    return MolSvg(name=name, smiles=smiles, body=body, bbox=path_bbox(body))


def group_for_molecule(mol: MolSvg, x: float, center_y: float) -> str:
    min_x, min_y, _, _ = mol.bbox
    y = center_y - mol.height / 2
    tx = x - min_x
    ty = y - min_y
    return f'<g transform="translate({tx:.2f},{ty:.2f})">\n{mol.body}\n</g>'


def text_block_centered(cls: str, x: float, y: float, lines: list[str], line_step: int) -> str:
    tspans = []
    for idx, line in enumerate(lines):
        dy = "0" if idx == 0 else str(line_step)
        tspans.append(f'<tspan x="{x:.1f}" dy="{dy}">{line}</tspan>')
    return f'<text class="{cls}" x="{x:.1f}" y="{y:.1f}" text-anchor="middle">{"".join(tspans)}</text>'


def estimate_text_width(lines: list[str]) -> float:
    return max(len(line) for line in lines) * COND_CHAR_WIDTH


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    mols = [draw_molecule(name, smiles) for name, smiles in MOLECULES]
    reactant1, reactant2, product = mols
    top_conditions = ["Cat (10%)", "Base (3 equiv)"]
    bottom_conditions = ["Solvent (16 mL/g)", "80 °C, 24 h"]
    condition_width = max(estimate_text_width(top_conditions), estimate_text_width(bottom_conditions))
    arrow_len = max(MIN_ARROW_LEN, condition_width + ARROW_TEXT_OVERHANG)

    x1 = LEFT_PAD
    plus1_x = x1 + reactant1.width + GAP_STRUCTURE_PLUS
    x2 = plus1_x + GAP_PLUS_STRUCTURE
    arrow_x1 = x2 + reactant2.width + GAP_STRUCTURE_ARROW
    arrow_x2 = arrow_x1 + arrow_len
    product_x = arrow_x2 + GAP_ARROW_PRODUCT
    route_right = product_x + product.width

    arrow_y = BASELINE_Y
    arrow_center_x = (arrow_x1 + arrow_x2) / 2
    note_x = (x1 + x2 + reactant2.width) / 2
    note_y = BASELINE_Y + max(reactant1.height, reactant2.height) / 2 + 42

    width = route_right + RIGHT_PAD
    height = max(note_y + 28, BASELINE_Y + product.height / 2 + BOTTOM_PAD)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>',
        'text { font-family: Arial, Helvetica, sans-serif; font-weight: 700; fill: #000; }',
        '.cond { font-size: 11px; }',
        '.note { font-size: 12px; }',
        '.plus { font-size: 18px; }',
        '.arrow { stroke: #000; stroke-width: 1.30; fill: none; stroke-linecap: square; }',
        '</style>',
        '<defs>',
        '<marker id="arrowhead" markerWidth="6" markerHeight="4.5" refX="5.8" refY="2.25" orient="auto">',
        '<polygon points="0 0, 6 2.25, 0 4.5" fill="#000"/>',
        '</marker>',
        '</defs>',
        group_for_molecule(reactant1, x1, BASELINE_Y),
        f'<text class="plus" x="{plus1_x:.1f}" y="{BASELINE_Y + 6:.1f}" text-anchor="middle">+</text>',
        group_for_molecule(reactant2, x2, BASELINE_Y),
        f'<line class="arrow" x1="{arrow_x1:.1f}" y1="{arrow_y:.1f}" x2="{arrow_x2:.1f}" y2="{arrow_y:.1f}" marker-end="url(#arrowhead)"/>',
        text_block_centered("cond", arrow_center_x, arrow_y - 31, top_conditions, 14),
        text_block_centered("cond", arrow_center_x, arrow_y + 23, bottom_conditions, 14),
        group_for_molecule(product, product_x, BASELINE_Y),
        f'<text class="note" x="{note_x:.1f}" y="{note_y:.1f}" text-anchor="middle">Both are commercially available</text>',
        '</svg>',
    ]

    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(OUT)
    print(f"canvas: {width:.0f} x {height:.0f}")
    print(f"condition_width={condition_width:.1f}, arrow_len={arrow_len:.1f}")
    for mol in mols:
        print(f"{mol.name}: bbox={mol.bbox}, size={mol.width:.1f}x{mol.height:.1f}")


if __name__ == "__main__":
    main()
