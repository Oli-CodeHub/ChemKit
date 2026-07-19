#!/usr/bin/env python3
"""ChemKit layout replica draft for the supplied Taxol route image."""

from __future__ import annotations

from pathlib import Path


OUT = Path("/Users/yl/Desktop/skills/ChemKit/examples/20260625-taxol-route-layout-replica.svg")


def text(x: float, y: float, body: str, size: int = 10, anchor: str = "middle", cls: str = "") -> str:
    lines = body.split("\n")
    tspans = []
    for i, line in enumerate(lines):
        dy = "0" if i == 0 else str(size + 2)
        tspans.append(f'<tspan x="{x:.1f}" dy="{dy}">{line}</tspan>')
    klass = f' class="{cls}"' if cls else ""
    return f'<text{klass} x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}">{"".join(tspans)}</text>'


def arrow(x1: float, y1: float, x2: float, y2: float) -> str:
    return f'<line class="arrow" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" marker-end="url(#arrowhead)"/>'


def mol(x: float, y: float, label: str, kind: str = "fused", note: str = "") -> str:
    # Stylized placeholders: enough to inspect route geometry while preserving a chemistry-like visual density.
    if kind == "taxol":
        shape = f'''
<path d="M{x-60},{y} L{x-36},{y-24} L{x+10},{y-18} L{x+42},{y+6} L{x+20},{y+42} L{x-35},{y+36} Z"/>
<path d="M{x-20},{y-20} L{x-2},{y+36} M{x+12},{y-16} L{x+22},{y+35} M{x-48},{y+2} L{x-78},{y-16}"/>
<text x="{x-58}" y="{y-22}" font-size="9">AcO</text>
<text x="{x+8}" y="{y-28}" font-size="9">O</text>
<text x="{x+34}" y="{y-4}" font-size="9">Me</text>
<text x="{x-8}" y="{y+50}" font-size="9">O</text>'''
    elif kind == "small":
        shape = f'''
<path d="M{x-30},{y-14} L{x-4},{y-30} L{x+28},{y-14} L{x+24},{y+22} L{x-14},{y+30} L{x-34},{y+8} Z"/>
<path d="M{x-12},{y-28} L{x+3},{y+22} M{x+24},{y-13} L{x-28},{y+10}"/>
<text x="{x-35}" y="{y-20}" font-size="9">Me</text>
<text x="{x+22}" y="{y-28}" font-size="9">OBn</text>
<text x="{x-42}" y="{y+18}" font-size="9">Br</text>'''
    else:
        shape = f'''
<path d="M{x-42},{y-18} L{x-18},{y-38} L{x+20},{y-30} L{x+42},{y-4} L{x+24},{y+34} L{x-24},{y+36} L{x-48},{y+8} Z"/>
<path d="M{x-18},{y-38} L{x-10},{y+34} M{x+18},{y-28} L{x+20},{y+34} M{x-44},{y+7} L{x+38},{y-5}"/>
<text x="{x-52}" y="{y-18}" font-size="9">Me</text>
<text x="{x+12}" y="{y-38}" font-size="9">O</text>
<text x="{x+30}" y="{y+18}" font-size="9">Me</text>'''
    return f'<g class="mol">{shape}{text(x, y+62, label, 11, "middle", "label")}{text(x, y+76, note, 9, "middle", "muted") if note else ""}</g>'


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="704" viewBox="0 0 960 704">',
        '<rect width="100%" height="100%" fill="white"/>',
        '''<style>
text { font-family: Arial, Helvetica, sans-serif; font-weight: 700; fill: #000; }
.mol path { fill: none; stroke: #000; stroke-width: 1.15; stroke-linecap: square; stroke-linejoin: miter; }
.arrow { stroke: #000; stroke-width: 1.05; fill: none; stroke-linecap: square; }
.yield { fill: #40558a; font-size: 10px; }
.label { font-size: 11px; }
.muted { font-size: 9px; }
.cond { font-size: 10px; }
</style>''',
        '''<defs><marker id="arrowhead" markerWidth="7" markerHeight="5" refX="6.7" refY="2.5" orient="auto"><polygon points="0 0, 7 2.5, 0 5" fill="#000"/></marker></defs>''',
    ]

    # Row 1
    parts += [
        mol(52, 92, "1", "small"),
        mol(318, 92, "2", "small"),
        mol(574, 92, "3", "small"),
        mol(838, 92, "4", "small"),
        arrow(118, 72, 258, 72),
        text(181, 46, "(i) Cl₃CC(=NH)OBn\n(ii) PBr₃, DMF; NaBH₄", 10, "middle", "cond"),
        text(181, 94, "46%, 2 steps", 10, "middle", "yield"),
        arrow(386, 72, 514, 72),
        text(450, 46, "(i) MsCl, LiAlH₄\n(ii) K₂OsO₄, NaIO₄", 10, "middle", "cond"),
        text(450, 94, "75%, 2 steps", 10, "middle", "yield"),
        arrow(646, 72, 784, 72),
        text(712, 46, "(i) TBSCl\n(ii) m-CPBA; MPP", 10, "middle", "cond"),
        text(712, 94, "53%, 2 steps", 10, "middle", "yield"),
        mol(742, 190, "5", "small"),
        arrow(836, 148, 836, 208),
        text(794, 158, "(7) t-BuLi, 5;\n2,2-DMP", 10, "middle", "cond"),
        text(886, 172, "76%", 10, "middle", "yield"),
    ]

    # Row 2
    parts += [
        mol(834, 278, "6", "fused"),
        mol(604, 278, "7", "fused"),
        mol(356, 278, "8", "fused"),
        mol(112, 278, "9 (X-ray)", "fused"),
        arrow(778, 248, 660, 248),
        text(710, 230, "t-BuLi, DMF\nthen NBS", 10, "middle", "cond"),
        text(710, 270, "61%", 10, "middle", "yield"),
        arrow(528, 248, 410, 248),
        text(468, 232, "SmI₂, Sm;\ntriphosgene", 10, "middle", "cond"),
        text(468, 270, "62%", 10, "middle", "yield"),
        arrow(282, 248, 164, 248),
        text(220, 224, "(i) 1 mol/L HCl\n(ii) Ac₂O\n(iii) TPAP, DBN", 10, "middle", "cond"),
        text(220, 280, "65%, 3 steps", 10, "middle", "yield"),
    ]

    # Row 3
    parts += [
        mol(112, 454, "10", "fused"),
        mol(462, 454, "11", "fused"),
        mol(810, 454, "12", "fused"),
        arrow(84, 338, 84, 396),
        text(60, 348, "69%\n2 steps", 10, "middle", "yield"),
        text(132, 352, "Pd/C, H₂; TESOTf\nPCC", 10, "middle", "cond"),
        arrow(204, 438, 382, 438),
        text(286, 398, "(i) TsNHNH₂, NaBH₄\n(ii) TMSim\n(iii) catecholborane;\nNaOAc, heated", 10, "middle", "cond"),
        text(286, 470, "37%, 3 steps", 10, "middle", "yield"),
        arrow(554, 438, 732, 438),
        text(642, 412, "hν, O₂, TPP;\nPMe₃", 10, "middle", "cond"),
        text(642, 470, "82%", 10, "middle", "yield"),
    ]

    # Row 4
    parts += [
        mol(830, 610, "13", "fused"),
        mol(484, 610, "14", "fused"),
        mol(142, 610, "Taxol", "taxol"),
        mol(324, 535, "15", "small"),
        arrow(812, 518, 812, 566),
        text(800, 532, "MsCl, OsO₄", 10, "middle", "cond"),
        text(852, 548, "75%", 10, "middle", "yield"),
        arrow(734, 600, 552, 600),
        text(642, 584, "DIPEA; Ac₂O; TBAF", 10, "middle", "cond"),
        text(642, 624, "32%", 10, "middle", "yield"),
        arrow(396, 600, 216, 600),
        text(324, 572, "PhLi, 15;\nHF-Py", 10, "middle", "cond"),
        text(324, 624, "68%", 10, "middle", "yield"),
    ]

    parts.append("</svg>")
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
