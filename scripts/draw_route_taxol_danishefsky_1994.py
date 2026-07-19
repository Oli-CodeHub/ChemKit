#!/usr/bin/env python3
"""Danishefsky 1994 taxol total synthesis — 4-node simplified key-skeleton route.

Full 15-step route: Danishefsky, S. J. et al. JACS 1994, 116, 11273.
This is a high-level skeleton, not a per-step route map.

  1. Cyclohexenone 1
     → Diels-Alder 1,3-dipolar cycloaddition + NaBH4 reduction
  2. 6-8-6 tricyclic (compound 8, simplified, no stereo)
     → RCM / acetonide protection
  3. 6-8-6-4 + oxetane (compound 9, simplified)
     → Ojima beta-lactam side-chain attach + global deprotection
  4. Paclitaxel (real SMILES)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import rdDepictor
from rdkit.Chem.Draw import rdMolDraw2D


OUT = Path("/Users/yl/Desktop/skills/ChemKit/examples/20260625-route-taxol-danishefsky-1994-v1.svg")
FONT = "/System/Library/Fonts/Supplemental/Arial Black.ttf"

TEMP_W = 1200
TEMP_H = 500
BOND_WIDTH = 1.6
ATOM_FONT = 12  # smaller to fit denser structures
FIXED_BOND = 14

LEFT_PAD = 60
RIGHT_PAD = 80
BOTTOM_PAD = 80
BASELINE_Y = 130

GAP_STRUCTURE_ARROW = 40
GAP_ARROW_STRUCTURE = 40
MIN_ARROW_LEN = 180
ARROW_TEXT_OVERHANG = 60
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
    ("1 (cyclohexenone)", "O=C1C=C(C)CCC1C(CC=C)O"),
    ("8 (6-8-6 tricyclic)", "C1=CC2CC3CCCCC3(CC1)CC2"),
    ("9 (6-8-6-4 + oxetane)", "CC1=CC2CC3(CC(OC3=O)C(C2(C)CC1OC(C)=O)(C)O)OCc1ccccc1"),
    ("Taxol (paclitaxel)", "CC1=C2C(C(=O)C3(C(CC4C(C3C(C(C2(C)C)(CC1OC(=O)C(C(C5=CC=CC=C5)NC(=O)C6=CC=CC=C6)O)O)OC(=O)C7=CC=CC=C7)(CO4)OC(=O)C)O)C)OC(=O)C"),
]

REACTIONS = [
    (
        ["1,3-dipolar cycloaddition", "+ oxidation / reduction"],
        ["(i) Cl\u2082C=NOH, Bn", "(ii) PBr\u2083, DMF; NaBH\u2084"],
    ),
    (
        ["RCM (6-8-6 closure)", "+ acetonide protection"],
        ["SmI\u2082, triphosgene", "DBU, TBSCl"],
    ),
    (
        ["oxetane formation", "+ Ojima \u03b2-lactam (15) attach", "+ global deprotection"],
        ["(i) 1 M HCl", "(ii) Ac\u2082O; PhLi, 15; HF-Py"],
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
