#!/usr/bin/env python3
"""Citronellal → nepetalactone: 3-step biomimetic route.

  1. Citronellal --intramolecular Prins/ene (TiCl4)--> iridoidal
  2. Iridoidal --Baeyer-Villiger (mCPBA)--> nepetalactol (lactol)
  3. Nepetalactol --oxidation (PCC/Dess-Martin)--> nepetalactone

Real SMILES throughout. Tests ChemKit user-confirmed defaults (single 14 px
tier, Arial Black, Unicode subscripts, shared label baseline) on a
small-molecule natural-product route.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import rdDepictor
from rdkit.Chem.Draw import rdMolDraw2D


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples" / "20260625-route-citronellal-nepetalactone-v1.svg"
FONT = "/System/Library/Fonts/Supplemental/Arial Black.ttf"

TEMP_W = 1200
TEMP_H = 500
BOND_WIDTH = 1.6
ATOM_FONT = 14
FIXED_BOND = 17

LEFT_PAD = 60
RIGHT_PAD = 80
BOTTOM_PAD = 80
BASELINE_Y = 120

GAP_STRUCTURE_ARROW = 50
GAP_ARROW_STRUCTURE = 50
MIN_ARROW_LEN = 150
ARROW_TEXT_OVERHANG = 56
COND_CHAR_WIDTH = 6.1


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


MOLECULES = [
    ("citronellal", "CC(C)=CCCC(C)CC=O"),
    ("iridoidal", "O=CC1CCC(CCO)C1C"),
    ("nepetalactol", "OC1OCC2CC=C(C)C2C1C"),
    ("nepetalactone", "O=C1OCC2CC=C(C)C2C1C"),
]

REACTIONS = [
    (
        ["intramolecular Prins / ene"],
        ["TiCl\u2084, CH\u2082Cl\u2082", "\u201378 \u00b0C \u2192 RT"],
    ),
    (
        ["hemiacetal formation"],
        ["H\u207a (cat.), CH\u2082Cl\u2082", "0 \u00b0C \u2192 RT"],
    ),
    (
        ["oxidation (lactol \u2192 lactone)"],
        ["PCC, CH\u2082Cl\u2082", "0 \u00b0C \u2192 RT"],
    ),
]


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
    opts.padding = 0.04
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
    out: list[str] = []
    for idx, line in enumerate(lines):
        yy = y + idx * line_step
        out.append(f'<text class="{cls}" x="{x:.1f}" y="{yy:.1f}" text-anchor="middle">{line}</text>')
    return "\n".join(out)


def estimate_text_width(lines: list[str]) -> float:
    return max(len(line) for line in lines) * COND_CHAR_WIDTH


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    mols = [draw_molecule(name, smi) for name, smi in MOLECULES]

    structure_x_left: list[float] = []
    arrow_segments: list[dict] = []

    cursor = LEFT_PAD
    for i, mol in enumerate(mols):
        if i > 0:
            top, bottom = REACTIONS[i - 1]
            cond_width = max(estimate_text_width(top), estimate_text_width(bottom))
            arrow_len = max(MIN_ARROW_LEN, cond_width + ARROW_TEXT_OVERHANG)
            arrow_x1 = cursor + GAP_STRUCTURE_ARROW
            arrow_x2 = arrow_x1 + arrow_len
            arrow_segments.append(
                {
                    "x1": arrow_x1,
                    "x2": arrow_x2,
                    "cx": (arrow_x1 + arrow_x2) / 2,
                    "top": top,
                    "bottom": bottom,
                }
            )
            cursor = arrow_x2 + GAP_ARROW_STRUCTURE
        structure_x_left.append(cursor)
        cursor += mol.width

    structure_centers = [x + m.width / 2 for x, m in zip(structure_x_left, mols)]
    route_right = cursor + RIGHT_PAD

    arrow_y = BASELINE_Y
    max_mol_half_height = max(m.height for m in mols) / 2
    top_cond_max_lines = max(len(r["top"]) for r in arrow_segments)
    bottom_cond_max_lines = max(len(r["bottom"]) for r in arrow_segments)
    cond_block_height = (top_cond_max_lines + bottom_cond_max_lines) * 18 + 60
    label_block_height = 14 + 24
    height = BASELINE_Y + max_mol_half_height + cond_block_height + label_block_height + BOTTOM_PAD

    label_y = BASELINE_Y + max_mol_half_height + 26

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{route_right:.0f}" height="{height:.0f}" viewBox="0 0 {route_right:.0f} {height:.0f}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>',
        'text { font-family: "Arial Black", "Arial Bold", Arial, Helvetica, sans-serif; font-weight: 900; fill: #000; stroke: #000; stroke-width: 0.35; paint-order: stroke fill; }',
        '.cond { font-size: 14px; }',
        '.label { font-size: 14px; }',
        '.arrow { stroke: #000; stroke-width: 1.30; fill: none; stroke-linecap: square; }',
        '</style>',
        '<defs>',
        '<marker id="arrowhead" markerWidth="6" markerHeight="4.5" refX="5.8" refY="2.25" orient="auto">',
        '<polygon points="0 0, 6 2.25, 0 4.5" fill="#000"/>',
        '</marker>',
        '</defs>',
    ]

    for mol, cx in zip(mols, structure_centers):
        x = cx - mol.width / 2
        parts.append(group_for_molecule(mol, x, BASELINE_Y))

    for mol, cx in zip(mols, structure_centers):
        parts.append(
            f'<text class="label" x="{cx:.1f}" y="{label_y:.1f}" text-anchor="middle">{mol.name}</text>'
        )

    for seg in arrow_segments:
        parts.append(
            f'<line class="arrow" x1="{seg["x1"]:.1f}" y1="{arrow_y:.1f}" x2="{seg["x2"]:.1f}" y2="{arrow_y:.1f}" marker-end="url(#arrowhead)"/>'
        )
        top_y = arrow_y - 40
        parts.append(text_block_centered("cond", seg["cx"], top_y, seg["top"], 18))
        bot_first_y = arrow_y + 24
        parts.append(text_block_centered("cond", seg["cx"], bot_first_y, seg["bottom"], 18))

    parts.append('</svg>')
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(OUT)
    print(f"canvas: {route_right:.0f} x {height:.0f}")
    for seg in arrow_segments:
        cond_w = max(estimate_text_width(seg["top"]), estimate_text_width(seg["bottom"]))
        print(f"  arrow x={seg['x1']:.0f}..{seg['x2']:.0f} (len={seg['x2']-seg['x1']:.1f}, cond_width={cond_w:.1f})")
    for mol, cx in zip(mols, structure_centers):
        print(f"  {mol.name}: center_x={cx:.1f}, size={mol.width:.1f}x{mol.height:.1f}")


if __name__ == "__main__":
    main()
