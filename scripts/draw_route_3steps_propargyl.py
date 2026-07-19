#!/usr/bin/env python3
"""Three-step route: propargyl alcohol → 2-bromoallyl alcohol (S1) → 2-substituted allyl alcohol (S2) → 2-substituted allyl tosylate (S3).

Reuses the bbox-driven layout from draw_reaction3_heck_rdkit.py and extends
it to an N-step sequence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import rdDepictor
from rdkit.Chem.Draw import rdMolDraw2D


OUT = Path("/Users/yl/Desktop/skills/ChemKit/examples/20260625-route-propargyl-alcohol-bromo-kumada-tosylate-v1.svg")
FONT = "/System/Library/Fonts/Supplemental/Arial Black.ttf"

TEMP_W = 1200
TEMP_H = 500
BOND_WIDTH = 1.6
ATOM_FONT = 14
FIXED_BOND = 17

LEFT_PAD = 24
RIGHT_PAD = 60
BOTTOM_PAD = 60  # extra room for S1/S2/S3 labels under each structure
BASELINE_Y = 110

GAP_STRUCTURE_ARROW = 40
GAP_ARROW_STRUCTURE = 48
MIN_ARROW_LEN = 110
ARROW_TEXT_OVERHANG = 50
COND_CHAR_WIDTH = 6.1
LABEL_FONT = 14


@dataclass
class MolSvg:
    name: str
    smiles: str
    label: str | None  # under-structure label (e.g. "S1") or None for starting material
    body: str
    bbox: tuple[float, float, float, float]

    @property
    def width(self) -> float:
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> float:
        return self.bbox[3] - self.bbox[1]


# Step 1: propargyl alcohol (HC≡C-CH2-OH)
# Step 2: 2-bromoallyl alcohol (Br-C(=CH2)-CH2-OH)
# Step 3: R-substituted allyl alcohol (R-C(=CH2)-CH2-OH) — R drawn via dummy atom with _displayLabel="R"
# Step 4: tosylate (R-C(=CH2)-CH2-OTs)
MOLECULES = [
    ("starting material", "C#CCO", None),
    ("S1", "BrC(=C)CO", "S1"),
    ("S2", "[*]C(=C)CO", "S2"),
    ("S3", "[*]C(=C)COS(=O)(=O)c1ccc(C)cc1", "S3"),
]

# (top_conditions, bottom_conditions) for each reaction arrow (left → right)
# Subscript digits in chemical formulas (e.g. Et₃N) are entered as Unicode so that
# sips / Quick Look / Preview.app render them correctly without <tspan> support.
REACTIONS = [
    (
        ["HBr", "Et\u2084NBr"],
        ["DCM"],
    ),
    (
        ["NiCl\u2082(dppe) (5 mol%)", "RMgX (2.5 equiv.)"],
        ["THF, 0 \u00b0C to RT"],
    ),
    (
        ["TsCl (1.1 equiv.)", "Et\u2083N (2.0 equiv.)"],
        ["DMAP (0.15 equiv.)", "DCM, 0 \u00b0C to RT"],
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

    if not xs or not ys:
        raise ValueError("Could not calculate molecule SVG bbox")

    pad = 4.0
    return min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad


def draw_molecule(name: str, smiles: str, label: str | None) -> MolSvg:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Bad SMILES for {name}: {smiles}")

    # For any dummy atom (R group), render the label as "R".
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
    opts.padding = 0.02
    opts.additionalAtomLabelPadding = 0.02
    opts.scaleBondWidth = False
    opts.singleColourWedgeBonds = True

    rdMolDraw2D.PrepareAndDrawMolecule(drawer, mol)
    drawer.FinishDrawing()
    body = strip_svg_shell(drawer.GetDrawingText())
    return MolSvg(name=name, smiles=smiles, label=label, body=body, bbox=path_bbox(body))


def group_for_molecule(mol: MolSvg, x: float, center_y: float) -> str:
    min_x, min_y, _, _ = mol.bbox
    y = center_y - mol.height / 2
    tx = x - min_x
    ty = y - min_y
    return f'<g transform="translate({tx:.2f},{ty:.2f})">\n{mol.body}\n</g>'


def text_block_centered(cls: str, x: float, y: float, lines: list[str], line_step: int) -> str:
    """Emit one centered <text> per line. Using independent <text> elements instead of
    nested <tspan> keeps the layout readable in sips / Quick Look / Preview.app, which
    handle <tspan dy=...> inconsistently.
    """
    out: list[str] = []
    for idx, line in enumerate(lines):
        yy = y + idx * line_step
        out.append(f'<text class="{cls}" x="{x:.1f}" y="{yy:.1f}" text-anchor="middle">{line}</text>')
    return "\n".join(out)


def estimate_text_width(lines: list[str]) -> float:
    return max(len(line) for line in lines) * COND_CHAR_WIDTH


def layout_route(mols: list[MolSvg]) -> tuple[list[float], list[dict], float]:
    """Compute structure center_x list and arrow segment dicts."""
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
    return structure_centers, arrow_segments, route_right


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    mols = [draw_molecule(name, smiles, label) for name, smiles, label in MOLECULES]
    structure_centers, arrow_segments, route_right = layout_route(mols)

    arrow_y = BASELINE_Y
    max_mol_height = max(m.height for m in mols)
    top_cond_max_lines = max(len(r["top"]) for r in arrow_segments)
    bottom_cond_max_lines = max(len(r["bottom"]) for r in arrow_segments)
    cond_block_height = (top_cond_max_lines + bottom_cond_max_lines) * 14 + 56
    label_block_height = LABEL_FONT + 22
    height = BASELINE_Y + max_mol_height / 2 + cond_block_height + label_block_height + BOTTOM_PAD

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

    # Draw structures and (optional) under-structure labels.
    # S1/S2/S3 labels share a single baseline at the bottom of the tallest structure,
    # so they line up horizontally even when individual structures have different heights.
    max_mol_half_height = max(m.height for m in mols) / 2
    shared_label_y = BASELINE_Y + max_mol_half_height + 22
    for mol, cx in zip(mols, structure_centers):
        x = cx - mol.width / 2
        parts.append(group_for_molecule(mol, x, BASELINE_Y))
        if mol.label is not None:
            parts.append(
                f'<text class="label" x="{cx:.1f}" y="{shared_label_y:.1f}" text-anchor="middle">{mol.label}</text>'
            )

    # Draw arrows and conditions.
    for seg in arrow_segments:
        parts.append(
            f'<line class="arrow" x1="{seg["x1"]:.1f}" y1="{arrow_y:.1f}" x2="{seg["x2"]:.1f}" y2="{arrow_y:.1f}" marker-end="url(#arrowhead)"/>'
        )
        top_y = arrow_y - 36
        parts.append(text_block_centered("cond", seg["cx"], top_y, seg["top"], 14))
        bot_first_y = arrow_y + 22
        parts.append(text_block_centered("cond", seg["cx"], bot_first_y, seg["bottom"], 14))

    parts.append('</svg>')
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(OUT)
    print(f"canvas: {route_right:.0f} x {height:.0f}")
    for seg in arrow_segments:
        cond_w = max(estimate_text_width(seg["top"]), estimate_text_width(seg["bottom"]))
        print(
            f"arrow: x={seg['x1']:.0f}..{seg['x2']:.0f} (len={seg['x2']-seg['x1']:.1f}), cond_width={cond_w:.1f}"
        )
    for mol, cx in zip(mols, structure_centers):
        print(f"{mol.name}: center_x={cx:.1f}, size={mol.width:.1f}x{mol.height:.1f}")


if __name__ == "__main__":
    main()
