#!/usr/bin/env python3
"""Improved diagnostic route layout from MolScribe predictions.

This is intentionally not a final publication route: all MolScribe
SMILES for this source were invalid. The output is a cleaner diagnostic
view of the raw recognition graph.
"""

from __future__ import annotations

import html
import json
import math
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path("/Users/yl/Desktop/skills/ChemKit")
PRED = ROOT / "examples/20260626-taxol-molscribe-predictions.json"
OUT_DIR = ROOT / "examples"
SVG = OUT_DIR / "20260626-taxol-molscribe-redraw-v2-diagnostic.svg"
PNG = OUT_DIR / "20260626-taxol-molscribe-redraw-v2-diagnostic.png"

WIDTH = 1320
HEIGHT = 970


def esc(s: str) -> str:
    return html.escape(s, quote=True)


@dataclass(frozen=True)
class MolPlace:
    key: str
    center: tuple[float, float]
    box: tuple[float, float]
    label: str
    label_y: float
    scale: float = 1.0


@dataclass(frozen=True)
class Arrow:
    x1: float
    y1: float
    x2: float
    y2: float


@dataclass(frozen=True)
class Label:
    x: float
    y: float
    body: str
    cls: str = "cond"
    size: float = 12.0
    anchor: str = "middle"
    line_step: float = 14.0


def clean_atom_label(symbol: str) -> str:
    raw = symbol.strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    raw = raw.replace("@", "")
    raw = re.sub(r"^\d+", "", raw)
    raw = raw.replace("H", "") if raw.startswith("C") else raw

    hide = {"", "C", "CH", "CHH", "H", "T", "(T)", "O-", "IO", "ON", "OB", "Ac", "AcA", "AlSO"}
    if raw in hide:
        return ""

    aliases = {
        "OHC": "CHO",
        "AcO": "AcO",
        "OAc": "OAc",
        "TMSO": "TMSO",
        "OTES": "OTES",
        "OBn": "OBn",
        "OMe": "OMe",
        "Me": "Me",
        "Bz": "Bz",
        "Ph": "Ph",
        "Br": "Br",
        "N": "N",
        "O": "O",
        "S": "S",
    }
    return aliases.get(raw, raw if len(raw) <= 4 else "")


def molecule_bbox(pred: dict) -> tuple[float, float, float, float]:
    atoms = pred.get("atoms", [])
    xs = [float(a["x"]) for a in atoms]
    ys = [float(a["y"]) for a in atoms]
    return min(xs), min(ys), max(xs), max(ys)


def mol_coords(pred: dict, place: MolPlace) -> list[tuple[float, float]]:
    atoms = pred.get("atoms", [])
    min_x, min_y, max_x, max_y = molecule_bbox(pred)
    span_x = max(max_x - min_x, 1e-6)
    span_y = max(max_y - min_y, 1e-6)
    scale = min(place.box[0] / span_x, place.box[1] / span_y) * place.scale
    cx, cy = place.center
    raw_cx = (min_x + max_x) / 2
    raw_cy = (min_y + max_y) / 2
    return [
        (cx + (float(a["x"]) - raw_cx) * scale, cy + (float(a["y"]) - raw_cy) * scale)
        for a in atoms
    ]


def line(x1: float, y1: float, x2: float, y2: float, cls: str = "bond") -> str:
    return f'<line class="{cls}" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>'


def double_bond(x1: float, y1: float, x2: float, y2: float) -> str:
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy) or 1.0
    ox, oy = -dy / length * 1.8, dx / length * 1.8
    return "\n".join(
        [
            line(x1 + ox, y1 + oy, x2 + ox, y2 + oy),
            line(x1 - ox, y1 - oy, x2 - ox, y2 - oy),
        ]
    )


def wedge(x1: float, y1: float, x2: float, y2: float, dashed: bool = False) -> str:
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy) or 1.0
    if dashed:
        return f'<line class="wedge-dashed" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>'
    ox, oy = -dy / length * 3.6, dx / length * 3.6
    return f'<polygon class="wedge" points="{x1:.1f},{y1:.1f} {x2 + ox:.1f},{y2 + oy:.1f} {x2 - ox:.1f},{y2 - oy:.1f}"/>'


def draw_atom_text(label: str, x: float, y: float) -> str:
    return (
        f'<text class="atom-halo" x="{x:.1f}" y="{y + 3.5:.1f}" text-anchor="middle">{esc(label)}</text>'
        f'<text class="atom" x="{x:.1f}" y="{y + 3.5:.1f}" text-anchor="middle">{esc(label)}</text>'
    )


def draw_molecule(pred: dict, place: MolPlace) -> str:
    atoms = pred.get("atoms", [])
    coords = mol_coords(pred, place)
    parts = [f'<g class="mol" data-key="{esc(place.key)}">']
    for bond in pred.get("bonds", []):
        i, j = bond["endpoint_atoms"]
        if i >= len(coords) or j >= len(coords):
            continue
        x1, y1 = coords[i]
        x2, y2 = coords[j]
        kind = bond.get("bond_type", "single")
        if kind == "double":
            parts.append(double_bond(x1, y1, x2, y2))
        elif kind == "solid wedge":
            parts.append(wedge(x1, y1, x2, y2))
        elif kind == "dashed wedge":
            parts.append(wedge(x1, y1, x2, y2, dashed=True))
        else:
            parts.append(line(x1, y1, x2, y2))
    for atom, (x, y) in zip(atoms, coords):
        label = clean_atom_label(atom.get("atom_symbol", ""))
        if label:
            parts.append(draw_atom_text(label, x, y))
    parts.append(f'<text class="num" x="{place.center[0]:.1f}" y="{place.label_y:.1f}" text-anchor="middle">{esc(place.label)}</text>')
    if float(pred.get("confidence", 0)) < 0.5:
        parts.append(
            f'<text class="lowconf" x="{place.center[0]:.1f}" y="{place.label_y + 14:.1f}" text-anchor="middle">low confidence</text>'
        )
    parts.append("</g>")
    return "\n".join(parts)


def draw_arrow(arrow: Arrow) -> str:
    return (
        f'<line class="arrow" x1="{arrow.x1:.1f}" y1="{arrow.y1:.1f}" '
        f'x2="{arrow.x2:.1f}" y2="{arrow.y2:.1f}" marker-end="url(#arrowhead)"/>'
    )


def draw_label(label: Label) -> str:
    lines = []
    for idx, text in enumerate(label.body.split("\n")):
        y = label.y + idx * label.line_step
        lines.append(
            f'<text class="{label.cls}" x="{label.x:.1f}" y="{y:.1f}" '
            f'font-size="{label.size:.1f}" text-anchor="{label.anchor}">{esc(text)}</text>'
        )
    return "\n".join(lines)


def main() -> None:
    data = json.loads(PRED.read_text(encoding="utf-8"))

    places = [
        MolPlace("1", (75, 118), (118, 112), "1", 206),
        MolPlace("2", (360, 118), (118, 118), "2", 206),
        MolPlace("3", (655, 118), (122, 116), "3", 206),
        MolPlace("4", (1090, 118), (136, 140), "4", 226),
        MolPlace("5", (990, 262), (98, 92), "5", 338, 0.96),
        MolPlace("6", (1095, 393), (144, 138), "6", 490),
        MolPlace("7", (785, 393), (152, 138), "7", 490),
        MolPlace("8", (475, 393), (144, 138), "8", 490),
        MolPlace("9", (145, 390), (172, 142), "9 (X-ray)", 502),
        MolPlace("10", (140, 610), (198, 154), "10", 738),
        MolPlace("11", (610, 610), (186, 154), "11", 738),
        MolPlace("12", (1070, 610), (196, 158), "12", 738),
        MolPlace("13", (1070, 845), (198, 158), "13", 948),
        MolPlace("14", (620, 845), (188, 160), "14", 948),
        MolPlace("15", (425, 720), (95, 66), "15", 775),
        MolPlace("taxol", (170, 845), (240, 152), "Taxol", 948),
    ]

    arrows = [
        Arrow(165, 118, 285, 118),
        Arrow(435, 118, 570, 118),
        Arrow(740, 118, 980, 118),
        Arrow(1090, 235, 1090, 310),
        Arrow(1015, 390, 895, 390),
        Arrow(700, 390, 585, 390),
        Arrow(390, 390, 250, 390),
        Arrow(145, 518, 145, 540),
        Arrow(245, 610, 500, 610),
        Arrow(720, 610, 955, 610),
        Arrow(1070, 745, 1070, 780),
        Arrow(970, 845, 735, 845),
        Arrow(515, 845, 300, 845),
    ]

    labels = [
        Label(225, 79, "(i) Cl₃CC(=NH)OBn\n(ii) PBr₃, DMF; NaBH₄"),
        Label(225, 143, "46%, 2 steps", "yield", 11),
        Label(505, 79, "(i) MsCl, LiAlH₄\n(ii) K₂OsO₄, NaIO₄"),
        Label(505, 143, "75%, 2 steps", "yield", 11),
        Label(860, 79, "(i) TBSCl\n(ii) m-CPBA; MPP"),
        Label(860, 143, "53%, 2 steps", "yield", 11),
        Label(1180, 265, "(7) t-BuLi, 5;\n2,2-DMP", size=11),
        Label(1180, 325, "76%", "yield", 11),
        Label(940, 362, "t-BuLi, DMF\nthen NBS", size=11),
        Label(940, 424, "61%", "yield", 11),
        Label(645, 362, "SmI₂, Sm;\ntriphosgene", size=11),
        Label(645, 424, "62%", "yield", 11),
        Label(320, 348, "(i) 1 mol/L HCl\n(ii) Ac₂O\n(iii) TPAP, DBN", size=11),
        Label(320, 424, "65%, 3 steps", "yield", 11),
        Label(95, 532, "69%\n2 steps", "yield", 11),
        Label(205, 530, "Pd/C, H₂; TESOTf\nPCC", size=11),
        Label(375, 558, "(i) TsNHNH₂, NaBH₄\n(ii) TMSim\n(iii) catecholborane;\nNaOAc, heated", size=11, line_step=13),
        Label(375, 640, "37%, 3 steps", "yield", 11),
        Label(835, 582, "hν, O₂, TPP;\nPMe₃", size=11),
        Label(835, 640, "82%", "yield", 11),
        Label(1165, 755, "MsCl, OsO₄", size=11),
        Label(1165, 812, "75%", "yield", 11),
        Label(850, 818, "DIPEA; Ac₂O; TBAF", size=11),
        Label(850, 876, "32%", "yield", 11),
        Label(425, 812, "PhLi, 15;\nHF-Py", size=11),
        Label(425, 876, "68%", "yield", 11),
    ]

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
        '<rect width="100%" height="100%" fill="white"/>',
        """<style>
text { font-family: Arial, Helvetica, sans-serif; font-weight: 700; fill: #000; }
.atom { font-size: 11px; fill: #000; stroke: none; }
.atom-halo { font-size: 11px; fill: none; stroke: #fff; stroke-width: 3.2; stroke-linejoin: round; }
.cond { font-size: 12px; fill: #000; }
.yield { fill: #42517f; font-weight: 700; }
.num { font-size: 13px; font-weight: 700; }
.lowconf { fill: #9d1b1b; font-size: 8.5px; font-weight: 700; }
.bond { stroke: #000; stroke-width: 1.25; fill: none; stroke-linecap: square; }
.wedge { fill: #000; stroke: none; }
.wedge-dashed { stroke: #000; stroke-width: 1.05; stroke-dasharray: 2.4 2.2; fill: none; }
.arrow { stroke: #000; stroke-width: 1.15; fill: none; stroke-linecap: square; }
.note { fill: #777; font-size: 10px; font-weight: 600; }
</style>""",
        '<defs><marker id="arrowhead" markerWidth="7" markerHeight="5" refX="6.7" refY="2.5" orient="auto"><polygon points="0 0, 7 2.5, 0 5" fill="#000"/></marker></defs>',
        '<text class="note" x="24" y="28">OCSR diagnostic redraw: structures are not final; source SMILES were invalid.</text>',
    ]
    parts.extend(draw_arrow(a) for a in arrows)
    parts.extend(draw_label(l) for l in labels)
    parts.extend(draw_molecule(data[p.key], p) for p in places)
    parts.append("</svg>")
    SVG.write_text("\n".join(parts), encoding="utf-8")

    chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    if chrome.exists():
        subprocess.run(
            [
                str(chrome),
                "--headless=new",
                "--disable-gpu",
                f"--screenshot={PNG}",
                f"--window-size={WIDTH},{HEIGHT}",
                SVG.resolve().as_uri(),
            ],
            check=True,
        )
    print(SVG)
    print(PNG)


if __name__ == "__main__":
    main()
