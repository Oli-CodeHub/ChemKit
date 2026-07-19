#!/usr/bin/env python3
"""Two-reactant + one-product route: cyclohexylidene malononitrile + 3-methyl-1H-pyrazol-5(4H)-one → spiro pyrazolo-pyran product.

Tests ChemKit's user-confirmed defaults on a denser route:
- single 14 px font tier (atom / condition / label)
- Arial Black glyphs for atom labels
- Unicode subscripts in condition text
- shared horizontal baseline for structure labels
- one independent <text> element per condition line (no <tspan dy>)
- font-weight 900 + 0.35 px stroke for SVG <text> bold
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import rdDepictor
from rdkit.Chem.Draw import rdMolDraw2D


OUT = Path("/Users/yl/Desktop/skills/ChemKit/examples/20260625-route-pyran-spiro-2-reactants-v1.svg")
FONT = "/System/Library/Fonts/Supplemental/Arial Black.ttf"

TEMP_W = 1200
TEMP_H = 500
BOND_WIDTH = 1.6
ATOM_FONT = 14
FIXED_BOND = 17

LEFT_PAD = 24
RIGHT_PAD = 80
BOTTOM_PAD = 80
BASELINE_Y = 120

GAP_STRUCTURE_PLUS = 18
GAP_PLUS_STRUCTURE = 18
GAP_STRUCTURE_ARROW = 60
GAP_ARROW_STRUCTURE = 60
MIN_ARROW_LEN = 130
ARROW_TEXT_OVERHANG = 56
COND_CHAR_WIDTH = 6.1


@dataclass
class MolSvg:
    name: str
    smiles: str
    body: str
    bbox: tuple[float, float, float, float]
    bottom_label: str | None = None  # e.g. "1.1 equiv"

    @property
    def width(self) -> float:
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> float:
        return self.bbox[3] - self.bbox[1]


ITEMS: list[dict] = [
    {"kind": "mol", "name": "reactant 1", "smiles": "N#CC(=C1CCCCC1)C#N"},
    {"kind": "plus"},
    {"kind": "mol", "name": "reactant 2", "smiles": "CC1=NNC(=O)C1", "bottom_label": "1.1 equiv"},
    {
        "kind": "arrow",
        "top": ["50 mol% additive"],
        "bottom": ["solvent (15 mL/g)", "65 \u00b0C, 24 h"],
    },
    {"kind": "mol", "name": "product", "smiles": "CC1=NNC2=C1C3(CCCCC3)C(C#N)=C(N)O2"},
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


def draw_molecule(name: str, smiles: str, bottom_label: str | None) -> MolSvg:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Bad SMILES for {name}: {smiles}")

    for atom in mol.GetAtoms():
        if atom.GetAtomicNum() == 0 and atom.GetSymbol() == "*":
            atom.SetProp("_displayLabel", "R")

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
    opts.padding = 0.05
    opts.additionalAtomLabelPadding = 0.02
    opts.scaleBondWidth = False
    opts.singleColourWedgeBonds = True

    rdMolDraw2D.PrepareAndDrawMolecule(drawer, mol)
    drawer.FinishDrawing()
    body = strip_svg_shell(drawer.GetDrawingText())
    return MolSvg(
        name=name,
        smiles=smiles,
        body=body,
        bbox=path_bbox(body),
        bottom_label=bottom_label,
    )


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

    # Pre-draw all molecules so we can use their widths in layout.
    mols: dict[int, MolSvg] = {}
    for i, item in enumerate(ITEMS):
        if item["kind"] == "mol":
            mols[i] = draw_molecule(item["name"], item["smiles"], item.get("bottom_label"))

    # Compute placements: each item gets an x_left (for molecules) or x_center (for plus) or arrow segment.
    placements: list[dict] = []
    cursor = LEFT_PAD
    for i, item in enumerate(ITEMS):
        if item["kind"] == "mol":
            m = mols[i]
            placements.append({"kind": "mol", "idx": i, "x_left": cursor, "x_center": cursor + m.width / 2})
            cursor += m.width
        elif item["kind"] == "plus":
            placements.append({"kind": "plus", "x_center": cursor + GAP_STRUCTURE_PLUS / 2})
            cursor += GAP_STRUCTURE_PLUS + GAP_PLUS_STRUCTURE
        elif item["kind"] == "arrow":
            cond_width = max(estimate_text_width(item["top"]), estimate_text_width(item["bottom"]))
            arrow_len = max(MIN_ARROW_LEN, cond_width + ARROW_TEXT_OVERHANG)
            arrow_x1 = cursor + GAP_STRUCTURE_ARROW / 2
            arrow_x2 = arrow_x1 + arrow_len
            placements.append(
                {
                    "kind": "arrow",
                    "x1": arrow_x1,
                    "x2": arrow_x2,
                    "cx": (arrow_x1 + arrow_x2) / 2,
                    "top": item["top"],
                    "bottom": item["bottom"],
                }
            )
            cursor = arrow_x2 + GAP_ARROW_STRUCTURE / 2
            # No molecule follows yet — leave cursor for the next mol to start at.
    route_right = cursor + RIGHT_PAD

    # Canvas height: tallest structure + condition text + bottom labels.
    max_mol_half_height = max(m.height for m in mols.values()) / 2
    max_mol_bottom_y = BASELINE_Y + max_mol_half_height
    # Shared baseline for any bottom labels (e.g. "1.1 equiv") or S1/S2/S3 markers.
    label_baseline_y = max_mol_bottom_y + 26
    top_cond_max_lines = max(len(p["top"]) for p in placements if p["kind"] == "arrow")
    bottom_cond_max_lines = max(len(p["bottom"]) for p in placements if p["kind"] == "arrow")
    cond_block_height = (top_cond_max_lines + bottom_cond_max_lines) * 18 + 60
    height = label_baseline_y + 24 + BOTTOM_PAD

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{route_right:.0f}" height="{height:.0f}" viewBox="0 0 {route_right:.0f} {height:.0f}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>',
        'text { font-family: "Arial Black", "Arial Bold", Arial, Helvetica, sans-serif; font-weight: 900; fill: #000; stroke: #000; stroke-width: 0.35; paint-order: stroke fill; }',
        '.cond { font-size: 14px; }',
        '.label { font-size: 14px; }',
        '.plus { font-size: 22px; }',
        '.arrow { stroke: #000; stroke-width: 1.30; fill: none; stroke-linecap: square; }',
        '</style>',
        '<defs>',
        '<marker id="arrowhead" markerWidth="6" markerHeight="4.5" refX="5.8" refY="2.25" orient="auto">',
        '<polygon points="0 0, 6 2.25, 0 4.5" fill="#000"/>',
        '</marker>',
        '</defs>',
    ]

    for p in placements:
        if p["kind"] == "mol":
            m = mols[p["idx"]]
            parts.append(group_for_molecule(m, p["x_left"], BASELINE_Y))
            if m.bottom_label:
                parts.append(
                    f'<text class="label" x="{p["x_center"]:.1f}" y="{label_baseline_y:.1f}" text-anchor="middle">{m.bottom_label}</text>'
                )
        elif p["kind"] == "plus":
            parts.append(
                f'<text class="plus" x="{p["x_center"]:.1f}" y="{BASELINE_Y + 6:.1f}" text-anchor="middle">+</text>'
            )
        elif p["kind"] == "arrow":
            parts.append(
                f'<line class="arrow" x1="{p["x1"]:.1f}" y1="{BASELINE_Y}" x2="{p["x2"]:.1f}" y2="{BASELINE_Y}" marker-end="url(#arrowhead)"/>'
            )
            top_y = BASELINE_Y - 42
            parts.append(text_block_centered("cond", p["cx"], top_y, p["top"], 18))
            bot_first_y = BASELINE_Y + 26
            parts.append(text_block_centered("cond", p["cx"], bot_first_y, p["bottom"], 18))

    parts.append('</svg>')
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(OUT)
    print(f"canvas: {route_right:.0f} x {height:.0f}")
    for p in placements:
        if p["kind"] == "mol":
            m = mols[p["idx"]]
            print(f"  mol {m.name}: center_x={p['x_center']:.1f}, size={m.width:.1f}x{m.height:.1f}, label={m.bottom_label}")
        elif p["kind"] == "plus":
            print(f"  plus at x={p['x_center']:.1f}")
        elif p["kind"] == "arrow":
            print(f"  arrow x={p['x1']:.0f}..{p['x2']:.0f} (len={p['x2']-p['x1']:.1f})")


if __name__ == "__main__":
    main()
