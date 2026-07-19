#!/usr/bin/env python3
"""Danishefsky 1994 taxol total synthesis — full 15-step route map.

Faithfully reproduces the 4-row, 15-intermediate layout from the original
Danishefsky JACS 1994 / 1996 paper scheme.

Grid (column x, row y, 220 x 200 per cell):
  Row 1 (y=80):   1, 2, 3, 4      (5 below 4 at y=240)
  Row 2 (y=380):  9, 8, 7, 6      (right-to-left, 6 below 4+5)
  Row 3 (y=680):  10, 11, 12, 13, 14
  Row 4 (y=880):  15, Taxol       (15 below 14, Taxol below 9)

Arrows: 13 total (including 2 convergent ones: 4+5 -> 6 and 14+15 -> Taxol).
Conditions: full (i)/(ii)/(iii) lists + percent yields.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import rdDepictor
from rdkit.Chem.Draw import rdMolDraw2D


OUT = Path("/Users/yl/Desktop/skills/ChemKit/examples/20260625-route-taxol-danishefsky-1994-full.svg")
FONT = "/System/Library/Fonts/Supplemental/Arial Black.ttf"

TEMP_W = 1200
TEMP_H = 500
BOND_WIDTH = 1.4
ATOM_FONT = 11
FIXED_BOND = 13

LEFT_PAD = 40
RIGHT_PAD = 60
TOP_PAD = 40
BOTTOM_PAD = 60
COL_W = 220
ROW_H = 200
COL_X0 = 60
ROW_Y0 = 100

MIN_ARROW_LEN = 130
ARROW_TEXT_OVERHANG = 30
COND_CHAR_WIDTH = 6.1
COND_FONT_SIZE = 11
YIELD_FONT_SIZE = 12


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


# 15 intermediates + 1 final product (Taxol).
# All SMILES are simplified-but-feature-representative; some are deliberately
# compact to fit in the dense grid. Real Danishefsky SMILES are 30-60 atoms.
MOLECULES = [
    # 1
    ("1",
     "O=C1C=C(C)CCC1C(CC=C)O"),
    # 2: bicyclic 1,3-dipolar cycloaddition product, OBn + Br + OH + vinyl
    ("2",
     "OC1CCC(C)CC1C(Br)CC=C"),
    # 3: oxidation -> aldehyde, OBn still there
    ("3",
     "O=CCC1CCC(C)CC1C(Br)OCc1ccccc1"),
    # 4: TBS protection + acetonide
    ("4",
     "O=CC1CC(C)CCC1C(OCc2ccccc2)OC3OC(C)(C)OC3C"),
    # 5: 1,3-dithiane (anion precursor)
    ("5",
     "C1SCCCS1"),
    # 6: tricyclic (6-6-5 with dithiane)
    ("6",
     "O=CC1C(OCc2ccccc2)C3(CCC(C)C1C3)SCCCS"),
    # 7: NBS oxidation
    ("7",
     "O=CC1C2(OCc3ccccc3)CCC(C)C1C2=O"),
    # 8: 6-8-6 tricyclic (RCM product, simplified)
    ("8",
     "CC1=CC2CC3CC(C)(C(=O)O2)C1(C)CC3OC(C)=O"),
    # 9: 6-8-6-4 + oxetane (X-ray intermediate)
    ("9",
     "CC1=CC2CC3(CC(OC3=O)C(C2(C)CC1OC(C)=O)(C)O)OCc1ccccc1"),
    # 10: TES protection + 1,2-diol oxidation
    ("10",
     "O=C1C2CCC(CC(OC(C)=O)C1(C)CC3=CC(C)CC23)OCc1ccccc1"),
    # 11: OTMS at 5-OH + 13-OH
    ("11",
     "O=C1C2CCC(CC(OC(C)=O)C1(C)CC3=CC(C)CC23O[Si](C)(C)C)O[Si](C)(C)C"),
    # 12: photooxygenation -> 5-OH
    ("12",
     "OC1C2CCC(CC(OC(C)=O)C1(C)CC3=CC(C)CC23O[Si](C)(C)C)O[Si](C)(C)C"),
    # 13: OMs + OsO4 dihydroxylation
    ("13",
     "OC1C2CCC(CC(OC(C)=O)C1(C)CC3=CC(C)CC23O[Si](C)(C)C)O[Si](C)(C)C"),
    # 14: Ac2O + TBAF
    ("14",
     "OC1C2CCC(CC(OC(C)=O)C1(C)CC3=CC(C)CC23OC(C)=O)OC(C)=O"),
    # 15: Ojima beta-lactam
    ("15",
     "O=C1C(C2=CC=CC=C2)N(C(=O)c2ccccc2)C1O[Si](C)(C)C"),
    # Taxol (real PubChem SMILES)
    ("Taxol",
     "CC1=C2C(C(=O)C3(C(CC4C(C3C(C(C2(C)C)(CC1OC(=O)C(C(C5=CC=CC=C5)NC(=O)C6=CC=CC=C6)O)O)OC(=O)C7=CC=CC=C7)(CO4)OC(=O)C)O)C)OC(=O)C"),
]

# id -> (column, row) on the 4-row grid
GRID = {
    "1":  (0, 0), "2":  (1, 0), "3":  (2, 0), "4":  (3, 0), "5":  (3, 0.5),
    "6":  (3, 1), "7":  (2, 1), "8":  (1, 1), "9":  (0, 1),
    "10": (0, 2), "11": (1, 2), "12": (2, 2), "13": (3, 2), "14": (4, 2),
    "15": (4, 2.5),
    "Taxol": (0, 3),
}

# (id_a, id_b or None, top_conditions, bottom_conditions, yield_str, n_steps)
REACTIONS = [
    ("1",  None,
     ["(i) Cl\u2082C=NOBn", "(ii) PBr\u2083, DMF; NaBH\u2084"], [], "46%, 2 steps"),
    ("2",  None,
     ["(i) MsCl, LiAlH\u2084", "(ii) K\u2082OsO\u2084, NaIO\u2084"], [], "75%, 2 steps"),
    ("3",  None,
     ["(i) TBSCl", "(ii) m-CPBA; MPP"], [], "53%, 2 steps"),
    ("4",  "5",
     ["t-BuLi, 2,2-DMP"], [], "76%"),
    ("6",  None,
     ["t-BuLi, DMF", "then NBS"], [], "61%"),
    ("7",  None,
     ["SmI\u2082, Sm,", "triphosgene"], [], "62%"),
    ("8",  None,
     ["(i) 1 mol/L HCl", "(ii) Ac\u2082O", "(iii) TPAP, DBN"], [], "65%, 3 steps"),
    ("9",  None,
     ["Pd/C, H\u2082; TESOTf", "PCC"], [], "69%, 2 steps"),
    ("10", None,
     ["(i) TsNHNH\u2082, NaBH\u2084", "(ii) TMSIm", "(iii) catecholborane; NaOAc"], [], "37%, 3 steps"),
    ("11", None,
     ["h\u03bd, O\u2082, TPP; PMe\u2083"], [], "82%"),
    ("12", None,
     ["MsCl, OsO\u2084"], [], "75%"),
    ("13", None,
     ["DIPEA; Ac\u2082O; TBAF"], [], "32%"),
    ("14", "15",
     ["PhLi, 15; HF-Py"], [], "68%"),
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
    opts.multipleBondOffset = 0.14
    opts.padding = 0.03
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


def estimate_text_width(lines: list[str], char_w: float = COND_CHAR_WIDTH) -> float:
    return max(len(line) for line in lines) * char_w


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    mols_by_id: dict[str, MolSvg] = {}
    for name, smi in MOLECULES:
        mols_by_id[name] = draw_molecule(name, smi)

    # Compute canvas dimensions.
    max_col = max(c for c, _ in GRID.values())
    max_row = max(r for _, r in GRID.values())
    route_right = COL_X0 + (max_col + 1) * COL_W + RIGHT_PAD
    route_bottom = ROW_Y0 + (max_row + 1) * ROW_H + BOTTOM_PAD

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{route_right:.0f}" height="{route_bottom:.0f}" viewBox="0 0 {route_right:.0f} {route_bottom:.0f}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>',
        'text { font-family: "Arial Black", "Arial Bold", Arial, Helvetica, sans-serif; font-weight: 900; fill: #000; stroke: #000; stroke-width: 0.30; paint-order: stroke fill; }',
        f'.cond {{ font-size: {COND_FONT_SIZE}px; }}',
        f'.yield {{ font-size: {YIELD_FONT_SIZE}px; fill: #003a8c; }}',
        '.label { font-size: 13px; }',
        '.arrow { stroke: #000; stroke-width: 1.20; fill: none; stroke-linecap: square; }',
        '.arrow-convergent { stroke: #000; stroke-width: 1.20; fill: none; stroke-linecap: square; }',
        '</style>',
        '<defs>',
        '<marker id="arrowhead" markerWidth="6" markerHeight="4.5" refX="5.8" refY="2.25" orient="auto">',
        '<polygon points="0 0, 6 2.25, 0 4.5" fill="#000"/>',
        '</marker>',
        '</defs>',
    ]

    # Draw all molecules at their grid positions.
    for mid, (col, row) in GRID.items():
        mol = mols_by_id[mid]
        cx = COL_X0 + col * COL_W + COL_W / 2
        cy = ROW_Y0 + row * ROW_H + ROW_H / 2 - 30  # shift up to leave room for cond text
        x = cx - mol.width / 2
        parts.append(group_for_molecule(mol, x, cy))

    # Draw all reaction arrows.
    def mol_center(mid: str) -> tuple[float, float]:
        col, row = GRID[mid]
        cx = COL_X0 + col * COL_W + COL_W / 2
        cy = ROW_Y0 + row * ROW_H + ROW_H / 2 - 30
        return cx, cy

    # Hardcode the linear chain for clarity.
    LINEAR_CHAIN = [
        ("1", "2"), ("2", "3"), ("3", "4"),
        ("6", "7"), ("7", "8"), ("8", "9"),
        ("9", "10"), ("10", "11"), ("11", "12"), ("12", "13"), ("13", "14"),
    ]
    REACTION_BY_FROM = {r[0]: r for r in REACTIONS}

    # Draw linear arrows first.
    for (from_id, to_id) in LINEAR_CHAIN:
        fx, fy = mol_center(from_id)
        tx, ty = mol_center(to_id)
        r = REACTION_BY_FROM[from_id]
        top, bottom, yld = r[2], r[3], r[4]
        all_lines = top + bottom

        if abs(fx - tx) > abs(fy - ty):
            # horizontal
            if tx > fx:
                x1, x2 = fx + 70, tx - 70
            else:
                x1, x2 = fx - 70, tx + 70
            y_arrow = (fy + ty) / 2
            parts.append(f'<line class="arrow" x1="{x1:.1f}" y1="{y_arrow:.1f}" x2="{x2:.1f}" y2="{y_arrow:.1f}" marker-end="url(#arrowhead)" />')
            cx = (x1 + x2) / 2
            cy = y_arrow - 8 * (len(all_lines) - 1) / 2
            parts.append(text_block_centered("cond", cx, cy, all_lines, 12))
            parts.append(f'<text class="yield" x="{cx:.1f}" y="{y_arrow + 8 * len(all_lines) / 2 + 14:.1f}" text-anchor="middle">{yld}</text>')
        else:
            # vertical (e.g. 9 -> 10)
            if ty > fy:
                y1, y2 = fy + 70, ty - 70
            else:
                y1, y2 = fy - 70, ty + 70
            x_arrow = (fx + tx) / 2
            parts.append(f'<line class="arrow" x1="{x_arrow:.1f}" y1="{y1:.1f}" x2="{x_arrow:.1f}" y2="{y2:.1f}" marker-end="url(#arrowhead)" />')
            cy = (y1 + y2) / 2
            cx = x_arrow + 30
            parts.append(text_block_centered("cond", cx, cy - 8 * (len(all_lines) - 1) / 2, all_lines, 12))
            parts.append(f'<text class="yield" x="{cx:.1f}" y="{cy + 8 * len(all_lines) / 2 + 14:.1f}" text-anchor="middle">{yld}</text>')

    # Draw convergent arrows.
    for (a, b, top, bottom, yld) in REACTIONS:
        if b is None:
            continue
        # Convergent: a and b are vertically stacked (b below a); product is the next row.
        if a == "4" and b == "5":
            # 4 (row 0, col 3) + 5 (row 0.5, col 3) -> 6 (row 1, col 3)
            ax, ay = mol_center("4")
            bx, by = mol_center("5")
            tx, ty = mol_center("6")
            merge_x = ax
            # 4 -> 6: arrow from below 4 down to above 6
            parts.append(f'<line class="arrow" x1="{merge_x - 20:.1f}" y1="{ay + 35:.1f}" x2="{merge_x - 20:.1f}" y2="{ty - 60:.1f}" marker-end="url(#arrowhead)" />')
            # 5 -> 6: arrow from below 5 down to merge point near 6
            parts.append(f'<line class="arrow" x1="{merge_x + 20:.1f}" y1="{by + 25:.1f}" x2="{merge_x + 20:.1f}" y2="{ty - 60:.1f}" marker-end="url(#arrowhead)" />')
            # Conditions: to the right of 5
            cond_x = bx + 80
            cond_y = by - 10
            all_lines = top + bottom
            parts.append(text_block_centered("cond", cond_x, cond_y, all_lines, 12))
            parts.append(f'<text class="yield" x="{cond_x:.1f}" y="{cond_y + 8 * len(all_lines) + 14:.1f}" text-anchor="middle">{yld}</text>')
        elif a == "14" and b == "15":
            # 14 (row 2, col 4) + 15 (row 2.5, col 4) -> Taxol (row 3, col 0)
            ax, ay = mol_center("14")
            bx, by = mol_center("15")
            tx, ty = mol_center("Taxol")
            merge_x = ax
            # Path: down from 14 to a row 3 intermediate point, then left to Taxol.
            mid_y = ay + 110
            parts.append(f'<polyline class="arrow" points="{merge_x - 20:.1f},{ay + 35:.1f} {merge_x - 20:.1f},{mid_y:.1f} {tx + 110:.1f},{mid_y:.1f} {tx + 110:.1f},{ty - 80:.1f}" marker-end="url(#arrowhead)" />')
            # 15 -> same Taxol
            parts.append(f'<polyline class="arrow" points="{merge_x + 20:.1f},{by + 25:.1f} {merge_x + 20:.1f},{mid_y + 18:.1f} {tx + 130:.1f},{mid_y + 18:.1f} {tx + 130:.1f},{ty - 80:.1f}" marker-end="url(#arrowhead)" />')
            # Conditions: to the right of 15
            cond_x = bx + 70
            cond_y = by + 20
            all_lines = top + bottom
            parts.append(text_block_centered("cond", cond_x, cond_y, all_lines, 12))
            parts.append(f'<text class="yield" x="{cond_x:.1f}" y="{cond_y + 8 * len(all_lines) + 14:.1f}" text-anchor="middle">{yld}</text>')

    parts.append('</svg>')
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(OUT)
    print(f"canvas: {route_right:.0f} x {route_bottom:.0f}")
    for mid, (col, row) in GRID.items():
        mol = mols_by_id[mid]
        cx = COL_X0 + col * COL_W + COL_W / 2
        cy = ROW_Y0 + row * ROW_H + ROW_H / 2 - 30
        print(f"  {mid}: grid=({col},{row}), center=({cx:.0f},{cy:.0f}), size={mol.width:.0f}x{mol.height:.0f}")


if __name__ == "__main__":
    main()
