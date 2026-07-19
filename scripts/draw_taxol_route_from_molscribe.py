#!/usr/bin/env python3
"""Draw a Taxol route from MolScribe atom/bond predictions."""

from __future__ import annotations

import html
import json
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path


PRED = Path("/Users/yl/Desktop/skills/ChemKit/examples/20260626-taxol-molscribe-predictions.json")
OUT_DIR = Path("/Users/yl/Desktop/skills/ChemKit/examples")
SVG = OUT_DIR / "20260626-taxol-molscribe-redraw.svg"
PNG = OUT_DIR / "20260626-taxol-molscribe-redraw.png"

SCALE = 1.22
PAD_X = 30
PAD_Y = 24
WIDTH = int(922 * SCALE + PAD_X * 2)
HEIGHT = int(736 * SCALE + PAD_Y * 2)


def sx(x: float) -> float:
    return PAD_X + x * SCALE


def sy(y: float) -> float:
    return PAD_Y + y * SCALE


def esc(s: str) -> str:
    return html.escape(s, quote=True)


@dataclass(frozen=True)
class MolPlace:
    key: str
    center: tuple[float, float]
    size: tuple[float, float]
    label: str
    label_offset: tuple[float, float]
    scale: float = 1.0


@dataclass(frozen=True)
class Label:
    x: float
    y: float
    body: str
    size: int = 12
    cls: str = "cond"
    anchor: str = "middle"
    line_step: int = 15


@dataclass(frozen=True)
class Arrow:
    x1: float
    y1: float
    x2: float
    y2: float


def text(label: Label) -> str:
    parts = []
    for idx, line in enumerate(label.body.split("\n")):
        y = sy(label.y) + idx * label.line_step * SCALE
        parts.append(
            f'<text class="{label.cls}" x="{sx(label.x):.1f}" y="{y:.1f}" '
            f'font-size="{label.size * SCALE:.1f}" text-anchor="{label.anchor}">{esc(line)}</text>'
        )
    return "\n".join(parts)


def arrow(a: Arrow) -> str:
    return (
        f'<line class="arrow" x1="{sx(a.x1):.1f}" y1="{sy(a.y1):.1f}" '
        f'x2="{sx(a.x2):.1f}" y2="{sy(a.y2):.1f}" marker-end="url(#arrowhead)"/>'
    )


def atom_label(symbol: str) -> str:
    raw = symbol.strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    raw = raw.replace("@", "")
    raw = raw.replace("10", "").replace("14", "")
    if raw in {"C", "CH", "CHH", "H", ""}:
        return ""
    return raw


def mol_coords(pred: dict, place: MolPlace) -> list[tuple[float, float]]:
    atoms = pred.get("atoms", [])
    xs = [a["x"] for a in atoms]
    ys = [a["y"] for a in atoms]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(max_x - min_x, 1e-6)
    span_y = max(max_y - min_y, 1e-6)
    target_w = place.size[0] * SCALE * place.scale
    target_h = place.size[1] * SCALE * place.scale
    scale = min(target_w / span_x, target_h / span_y)
    cx = sx(place.center[0])
    cy = sy(place.center[1])
    return [
        (cx + ((a["x"] - (min_x + max_x) / 2) * scale), cy + ((a["y"] - (min_y + max_y) / 2) * scale))
        for a in atoms
    ]


def line(x1: float, y1: float, x2: float, y2: float, cls: str = "bond") -> str:
    return f'<line class="{cls}" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>'


def double_bond(x1: float, y1: float, x2: float, y2: float) -> str:
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy) or 1.0
    ox, oy = -dy / length * 2.2, dx / length * 2.2
    return "\n".join(
        [
            line(x1 + ox, y1 + oy, x2 + ox, y2 + oy),
            line(x1 - ox, y1 - oy, x2 - ox, y2 - oy),
        ]
    )


def wedge(x1: float, y1: float, x2: float, y2: float, dashed: bool = False) -> str:
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy) or 1.0
    ox, oy = -dy / length * 4.2, dx / length * 4.2
    if dashed:
        return f'<line class="wedge-dashed" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>'
    return (
        f'<polygon class="wedge" points="{x1:.1f},{y1:.1f} '
        f'{x2 + ox:.1f},{y2 + oy:.1f} {x2 - ox:.1f},{y2 - oy:.1f}"/>'
    )


def draw_molecule(pred: dict, place: MolPlace) -> str:
    atoms = pred.get("atoms", [])
    coords = mol_coords(pred, place)
    parts = [f'<g class="mol" data-key="{esc(place.key)}">']
    for b in pred.get("bonds", []):
        i, j = b["endpoint_atoms"]
        if i >= len(coords) or j >= len(coords):
            continue
        x1, y1 = coords[i]
        x2, y2 = coords[j]
        kind = b["bond_type"]
        if kind == "double":
            parts.append(double_bond(x1, y1, x2, y2))
        elif kind == "solid wedge":
            parts.append(wedge(x1, y1, x2, y2))
        elif kind == "dashed wedge":
            parts.append(wedge(x1, y1, x2, y2, dashed=True))
        else:
            parts.append(line(x1, y1, x2, y2))
    for atom, (x, y) in zip(atoms, coords):
        label = atom_label(atom["atom_symbol"])
        if not label:
            continue
        parts.append(
            f'<text class="atom" x="{x:.1f}" y="{y + 4:.1f}" text-anchor="middle">{esc(label)}</text>'
        )
    conf = pred.get("confidence", 0)
    if conf < 0.5:
        x = sx(place.center[0] + place.size[0] * 0.45)
        y = sy(place.center[1] - place.size[1] * 0.45)
        parts.append(f'<text class="warn" x="{x:.1f}" y="{y:.1f}" text-anchor="middle">?</text>')
    parts.append("</g>")
    return "\n".join(parts)


def main() -> None:
    data = json.loads(PRED.read_text(encoding="utf-8"))

    places = [
        MolPlace("1", (53, 70), (100, 92), "1", (0, 58)),
        MolPlace("2", (325, 72), (98, 98), "2", (0, 62)),
        MolPlace("3", (580, 72), (96, 96), "3", (0, 62)),
        MolPlace("4", (848, 68), (110, 118), "4", (0, 72)),
        MolPlace("5", (729, 168), (86, 82), "5", (0, 58), 0.95),
        MolPlace("6", (784, 266), (112, 110), "6", (0, 60)),
        MolPlace("7", (566, 266), (122, 104), "7", (0, 62)),
        MolPlace("8", (343, 266), (112, 104), "8", (0, 62)),
        MolPlace("9", (84, 262), (144, 116), "9 (X-ray)", (0, 76)),
        MolPlace("10", (82, 452), (174, 130), "10", (0, 80)),
        MolPlace("11", (452, 452), (160, 128), "11", (0, 80)),
        MolPlace("12", (795, 452), (170, 132), "12", (0, 80)),
        MolPlace("13", (795, 620), (174, 132), "13", (0, 76)),
        MolPlace("14", (458, 620), (154, 136), "14", (0, 76)),
        MolPlace("15", (322, 532), (92, 58), "15", (0, 58)),
        MolPlace("taxol", (126, 620), (240, 124), "Taxol", (0, 78)),
    ]
    arrows = [
        Arrow(112, 70, 262, 70), Arrow(387, 70, 513, 70), Arrow(647, 70, 783, 70),
        Arrow(838, 131, 838, 210), Arrow(725, 248, 632, 248), Arrow(494, 248, 404, 248),
        Arrow(287, 248, 154, 248), Arrow(76, 333, 76, 390), Arrow(196, 456, 340, 456),
        Arrow(554, 456, 684, 456), Arrow(802, 520, 802, 572), Arrow(725, 620, 548, 620),
        Arrow(384, 620, 254, 620),
    ]
    labels = [
        Label(188, 37, "(i) Cl₃CC(=NH)OBn\n(ii) PBr₃, DMF; NaBH₄", 12),
        Label(188, 93, "46%, 2 steps", 11, "yield"),
        Label(451, 37, "(i) MsCl, LiAlH₄\n(ii) K₂OsO₄, NaIO₄", 12),
        Label(451, 93, "75%, 2 steps", 11, "yield"),
        Label(713, 37, "(i) TBSCl\n(ii) m-CPBA; MPP", 12),
        Label(713, 93, "53%, 2 steps", 11, "yield"),
        Label(790, 153, "(7) t-BuLi, 5;\n2,2-DMP", 11),
        Label(881, 169, "76%", 11, "yield"),
        Label(698, 232, "t-BuLi, DMF\nthen NBS", 11),
        Label(704, 275, "61%", 11, "yield"),
        Label(452, 234, "SmI₂, Sm;\ntriphosgene", 11),
        Label(454, 276, "62%", 11, "yield"),
        Label(222, 218, "(i) 1 mol/L HCl\n(ii) Ac₂O\n(iii) TPAP, DBN", 11),
        Label(218, 276, "65%, 3 steps", 11, "yield"),
        Label(52, 349, "69%\n2 steps", 11, "yield"),
        Label(116, 354, "Pd/C, H₂; TESOTf\nPCC", 11),
        Label(278, 403, "(i) TsNHNH₂, NaBH₄\n(ii) TMSim\n(iii) catecholborane;\nNaOAc, heated", 11, line_step=14),
        Label(278, 476, "37%, 3 steps", 11, "yield"),
        Label(622, 432, "hν, O₂, TPP;\nPMe₃", 11),
        Label(622, 476, "82%", 11, "yield"),
        Label(782, 538, "MsCl, OsO₄", 11),
        Label(833, 558, "75%", 11, "yield"),
        Label(637, 604, "DIPEA; Ac₂O; TBAF", 11),
        Label(637, 657, "32%", 11, "yield"),
        Label(322, 585, "PhLi, 15;\nHF-Py", 11),
        Label(322, 657, "68%", 11, "yield"),
    ]

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
        '<rect width="100%" height="100%" fill="white"/>',
        """<style>
text { font-family: "Arial Black", "Arial Bold", Arial, Helvetica, sans-serif; font-weight: 900; fill: #000; stroke: #000; stroke-width: 0.18; paint-order: stroke fill; }
.atom { font-size: 13.5px; }
.yield { fill: #40558a; stroke: #40558a; }
.num { font-size: 16px; }
.warn { fill: #b00020; stroke: #b00020; font-size: 14px; }
.bond { stroke: #000; stroke-width: 1.55; fill: none; stroke-linecap: square; }
.wedge { fill: #000; stroke: none; }
.wedge-dashed { stroke: #000; stroke-width: 1.45; stroke-dasharray: 3 3; fill: none; }
.arrow { stroke: #000; stroke-width: 1.35; fill: none; stroke-linecap: square; }
</style>""",
        """<defs><marker id="arrowhead" markerWidth="8" markerHeight="6" refX="7.8" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="#000"/></marker></defs>""",
    ]
    parts.extend(draw_molecule(data[p.key], p) for p in places)
    parts.extend(arrow(a) for a in arrows)
    parts.extend(text(label) for label in labels)
    for p in places:
        parts.append(
            f'<text class="num" x="{sx(p.center[0] + p.label_offset[0]):.1f}" '
            f'y="{sy(p.center[1] + p.label_offset[1]):.1f}" text-anchor="middle">{esc(p.label)}</text>'
        )
    parts.append("</svg>")
    SVG.write_text("\n".join(parts), encoding="utf-8")

    chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    if chrome.exists():
        subprocess.run(
            [
                str(chrome), "--headless=new", "--disable-gpu",
                f"--screenshot={PNG}", f"--window-size={WIDTH},{HEIGHT}", SVG.resolve().as_uri(),
            ],
            check=True,
        )
    print(SVG)
    print(PNG)


if __name__ == "__main__":
    main()
