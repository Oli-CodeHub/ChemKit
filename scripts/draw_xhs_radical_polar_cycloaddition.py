#!/usr/bin/env python3
"""Generate a 4:3 vertical (1080x1440) image for Xiaohongshu (小红书).

Layout (top-to-bottom):
    - Top band:        journal name (Angewandte Chemie), "Supporting Information" tag
    - Title block:     paper title + author list
    - Reaction scheme: 4 compounds (1, 2, 3, 4) with 3 reagent arrows
                       in a 2x2 zigzag (1→2 / 2↓3 / 3→4)
    - Bottom band:     caption, "#chemkit" branding

All four molecules are drawn with chemkit 1.1 chemdraw_compact_style
(Arial Bold 26pt, 2.05 bond width, fixed bond 25.5, drawn on a 1600x1000
canvas then cropped to bbox), matching the chemkit 1.1 SKILL.md standard.
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

ROOT = Path("/Users/yl/Desktop/skills/ChemKit")
sys.path.insert(0, str(ROOT / "scripts"))
from rdkit import Chem  # noqa: E402
from chemkit_route_renderer import (  # noqa: E402
    chemdraw_compact_style,
    draw_mol_svg_at_fixed_scale,
)


# === 4-step reaction sequence ===
# Step 1: methyl 4-X-cyclohexane-1-carboxylate (starting material)
# Step 2: alpha-methallyl quaternary (LDA deprotonation + alkylation)
# Step 3: primary alcohol (LiAlH4 reduction of ester)
# Step 4: primary OTs (TsCl/DMAP tosylation)
COMPOUNDS = [
    {"id": 1, "smiles": "COC(=O)C1CCC(*)CC1"},
    {"id": 2, "smiles": "COC(=O)C1(CC(=C)C)CCC(*)CC1"},
    {"id": 3, "smiles": "OCC1(CC(=C)C)CCC(*)CC1"},
    {"id": 4, "smiles": "Cc1ccc(S(=O)(=O)OCC2(CC(=C)C)CCC(*)CC2)cc1"},
]
REAGENTS = [
    {  # 1 -> 2
        "top": ["methallyl bromide (1.5 equiv.)"],
        "bottom": ["LDA (1.2 equiv.)", "THF (0.5 M), −78 °C → RT"],
    },
    {  # 2 -> 3 (vertical arrow, top->bottom, conditions on the right)
        "top": ["LiAlH\u2084 (1 equiv.)"],
        "bottom": ["Et\u2082O (0.25 M), RT"],
    },
    {  # 3 -> 4
        "top": ["TsCl (1.1 equiv.)", "Et\u2083N (2.0 equiv.)"],
        "bottom": ["DMAP (0.15 equiv.)", "DCM, 0 °C → RT"],
    },
]


def render_molecule(smiles: str) -> str:
    """Render SMILES with the *-dummy atom labeled 'X' (the substituent placeholder)."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"bad SMILES: {smiles}")
    Chem.SanitizeMol(mol)
    for atom in mol.GetAtoms():
        if atom.GetAtomicNum() == 0 and atom.GetSymbol() == "*":
            atom.SetProp("_displayLabel", "X")
    style = chemdraw_compact_style()
    body, bbox, _ = draw_mol_svg_at_fixed_scale(mol, style)
    min_x, min_y, max_x, max_y = bbox
    w = max_x - min_x
    h = max_y - min_y
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{w:.0f}" height="{h:.0f}" '
        f'viewBox="{min_x:.2f} {min_y:.2f} {w:.2f} {h:.2f}">'
        f"{body}</svg>"
    )


# === Layout constants ===
W, H = 1080, 1440

# 4 compounds arranged 2x2:
#   [1] (top-left)  →  [2] (top-right)
#                          ↓
#   [3] (bottom-left) → [4] (bottom-right)
# Each cell holds a structure image ~280x220, plus a bold numeral below.
CELL_W, CELL_H = 300, 230
NUM_H = 30
ROW_Y = [490, 970]            # top row, bottom row
COL_X = [80, 700]              # left col, right col

# Arrow positions between cells (we draw them with simple divs)
# 1->2: horizontal arrow in the gap, centered vertically on row 0
H_ARROW_Y = ROW_Y[0] + CELL_H // 2
H_ARROW_X1 = COL_X[0] + CELL_W + 10
H_ARROW_X2 = COL_X[1] - 10

# 2->3: vertical arrow in the right column gap (going down-left)
V_ARROW_X = COL_X[1] + CELL_W // 2
V_ARROW_Y1 = ROW_Y[0] + CELL_H + 10
V_ARROW_Y2 = ROW_Y[1] - 10

# 3->4: horizontal arrow on bottom row
H2_ARROW_Y = ROW_Y[1] + CELL_H // 2


def main() -> None:
    svgs = [render_molecule(c["smiles"]) for c in COMPOUNDS]

    # Build compound cell HTML (one per ID)
    cell_html_parts: list[str] = []
    for idx, c in enumerate(COMPOUNDS):
        r, col = divmod(idx, 2)
        x, y = COL_X[col], ROW_Y[r]
        b64 = base64.b64encode(svgs[idx].encode("utf-8")).decode("ascii")
        cell_html_parts.append(f"""
        <div class="cell" style="left:{x}px; top:{y}px;">
          <img class="mol" src="data:image/svg+xml;base64,{b64}">
          <div class="num">{c['id']}</div>
        </div>
        """)

    # Horizontal arrow helper (1->2, 3->4) — line with arrowhead
    def h_arrow_svg(x1: float, x2: float, y: float) -> str:
        length = x2 - x1
        return f"""
        <svg class="arrow-svg" viewBox="0 0 {length} 60" width="{length}" height="60" style="left:{x1}px; top:{y - 30}px;">
          <line x1="0" y1="30" x2="{length - 12}" y2="30" stroke="#1a1a1a" stroke-width="2.4"/>
          <polygon points="{length},30 {length - 14},22 {length - 14},38" fill="#1a1a1a"/>
        </svg>
        """

    def v_arrow_svg(x: float, y1: float, y2: float) -> str:
        length = y2 - y1
        return f"""
        <svg class="arrow-svg" viewBox="0 0 60 {length}" width="60" height="{length}" style="left:{x - 30}px; top:{y1}px;">
          <line x1="30" y1="0" x2="30" y2="{length - 12}" stroke="#1a1a1a" stroke-width="2.4"/>
          <polygon points="30,{length} 22,{length - 14} 38,{length - 14}" fill="#1a1a1a"/>
        </svg>
        """

    # Condition text blocks
    def cond_block(x: float, y: float, lines: list[str], align: str = "middle") -> str:
        text = "<br>".join(lines)
        return (
            f'<div class="cond" style="left:{x}px; top:{y}px; text-align:{align};">'
            f"{text}</div>"
        )

    # 1->2: conditions above and below the horizontal arrow
    arrow_12 = h_arrow_svg(H_ARROW_X1, H_ARROW_X2, H_ARROW_Y)
    cond_12_top = cond_block(
        (H_ARROW_X1 + H_ARROW_X2) / 2 - 110,
        H_ARROW_Y - 75,
        REAGENTS[0]["top"],
    )
    cond_12_bot = cond_block(
        (H_ARROW_X1 + H_ARROW_X2) / 2 - 110,
        H_ARROW_Y + 35,
        REAGENTS[0]["bottom"],
    )

    # 2->3: vertical arrow, conditions to the right
    arrow_23 = v_arrow_svg(V_ARROW_X, V_ARROW_Y1, V_ARROW_Y2)
    cond_23_right = cond_block(
        V_ARROW_X + 50,
        (V_ARROW_Y1 + V_ARROW_Y2) / 2 - 30,
        REAGENTS[1]["top"] + REAGENTS[1]["bottom"],
        align="left",
    )

    # 3->4: conditions above and below
    arrow_34 = h_arrow_svg(H_ARROW_X1, H_ARROW_X2, H2_ARROW_Y)
    cond_34_top = cond_block(
        (H_ARROW_X1 + H_ARROW_X2) / 2 - 110,
        H2_ARROW_Y - 75,
        REAGENTS[2]["top"],
    )
    cond_34_bot = cond_block(
        (H_ARROW_X1 + H_ARROW_X2) / 2 - 110,
        H2_ARROW_Y + 35,
        REAGENTS[2]["bottom"],
    )

    cells_html = "".join(cell_html_parts)

    # Full HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 0;
    width: {W}px; height: {H}px;
    background: #fdfcf8;
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    color: #1a1a1a;
    overflow: hidden;
  }}
  .journal-band {{
    position: absolute; top: 0; left: 0; right: 0; height: 130px;
    background: linear-gradient(180deg, #003a78 0%, #1d4e8a 100%);
    color: white;
    text-align: center;
    padding-top: 28px;
  }}
  .journal-name {{
    font-size: 28px; font-weight: 800; letter-spacing: 4px;
    text-transform: uppercase;
  }}
  .journal-sub {{
    font-size: 13px; opacity: 0.9; margin-top: 4px; letter-spacing: 1.5px;
  }}
  .journal-tag {{
    display: inline-block; margin-top: 10px;
    padding: 4px 14px;
    border: 1.5px solid white; border-radius: 12px;
    font-size: 12px; font-weight: 600; letter-spacing: 1px;
  }}
  .title {{
    position: absolute; top: 200px; left: 80px; right: 80px;
    font-size: 34px; font-weight: 700; line-height: 1.2; text-align: center;
    color: #1a1a1a;
  }}
  .authors {{
    position: absolute; top: 360px; left: 0; right: 0; text-align: center;
    font-size: 18px; color: #1a1a1a;
  }}
  .authors em {{
    font-style: normal; color: #6e6e73; margin-left: 8px;
  }}
  .affiliation {{
    position: absolute; top: 400px; left: 0; right: 0; text-align: center;
    font-size: 13px; color: #6e6e73; font-style: italic;
  }}
  .scheme {{
    position: absolute; top: 460px; left: 0; right: 0; height: 800px;
  }}
  .cell {{
    position: absolute; width: {CELL_W}px; height: {CELL_H + NUM_H}px;
  }}
  .cell .mol {{
    width: 100%; height: {CELL_H}px;
    display: block; object-fit: contain;
  }}
  .cell .num {{
    height: {NUM_H}px;
    text-align: center;
    font-size: 22px; font-weight: 700; color: #1a1a1a;
    line-height: {NUM_H}px;
  }}
  .arrow-svg {{
    position: absolute;
  }}
  .cond {{
    position: absolute;
    font-size: 13px; font-weight: 600; color: #1a1a1a;
    width: 220px;
    line-height: 1.3;
  }}
  .footer {{
    position: absolute; bottom: 0; left: 0; right: 0; height: 80px;
    background: #f4f1ea;
    border-top: 1px solid #d2d2d7;
    text-align: center;
    padding-top: 16px;
  }}
  .footer .caption {{
    font-size: 13px; color: #6e6e73;
  }}
  .footer .branding {{
    margin-top: 6px;
    font-size: 11px; letter-spacing: 1.5px; color: #003a78; font-weight: 600;
  }}
</style>
</head>
<body>
  <div class="journal-band">
    <div class="journal-name">ANGEWANDTE CHEMIE</div>
    <div class="journal-sub">International Edition · Supporting Information</div>
    <div class="journal-tag">REACTION SCHEME</div>
  </div>
  <div class="title">Cyclic Amine Synthesis via Catalytic Radical–Polar Crossover Cycloadditions</div>
  <div class="authors">Y. Zhang, S.-S. Chen, K.-D. Li, H.-M. Huang<em>*</em></div>
  <div class="affiliation">— redrawn with chemkit 1.1 —</div>
  <div class="scheme">
    {cells_html}
    {arrow_12}
    {cond_12_top}
    {cond_12_bot}
    {arrow_23}
    {cond_23_right}
    {arrow_34}
    {cond_34_top}
    {cond_34_bot}
  </div>
  <div class="footer">
    <div class="caption">Stepwise α-methallylation → reduction → tosylation of 4-X-cyclohexanecarboxylate</div>
    <div class="branding">DRAWN WITH CHEMKIT 1.1 · chemdraw_compact_style</div>
  </div>
</body>
</html>
"""

    out_html = Path("/tmp/xhs_radical_polar.html")
    out_html.write_text(html, encoding="utf-8")
    print(f"wrote {out_html} ({len(html)/1024:.1f} KB)")

    out_png = ROOT / "outputs" / "xhs_radical_polar_cycloaddition.png"
    out_png.parent.mkdir(parents=True, exist_ok=True)

    # Use Chrome headless to render at exact viewport size
    import subprocess
    subprocess.run(
        [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            f"--window-size={W},{H}",
            f"--screenshot={out_png}",
            f"file://{out_html}",
        ],
        check=True,
    )
    print(f"wrote {out_png}")
    print(f"size: {out_png.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
