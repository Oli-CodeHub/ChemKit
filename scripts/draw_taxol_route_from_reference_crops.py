#!/usr/bin/env python3
"""Redraw the supplied Taxol route using structure crops plus ChemKit route styling.

This is an intermediate fidelity mode: preserve complex structures from the
reference image as bitmap crops, but redraw route arrows, conditions, yields,
and numbering as clean vector text/lines. It avoids pretending that low-res
OCSR has recovered every stereocenter.
"""

from __future__ import annotations

import html
import subprocess
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops


SRC = Path("/var/folders/__/t65vg_bx3wg_3x16sx9x4b5w0000gn/T/codex-clipboard-f4ea7d7b-5538-4882-bf12-81fdfa0ac2b7.png")
OUT_DIR = Path("/Users/yl/Desktop/skills/ChemKit/examples")
CROP_DIR = OUT_DIR / "20260626-taxol-reference-crops"
SVG = OUT_DIR / "20260626-taxol-reference-redraw.svg"
PNG = OUT_DIR / "20260626-taxol-reference-redraw.png"

SCALE = 1.22
PAD_X = 28
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
class Crop:
    key: str
    box: tuple[int, int, int, int]
    center: tuple[float, float]
    label: str
    label_offset: tuple[float, float] = (0, 50)
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


def trim_crop(img: Image.Image, box: tuple[int, int, int, int], pad: int = 4) -> Image.Image:
    crop = img.crop(box).convert("RGB")
    bg = Image.new("RGB", crop.size, "white")
    diff = ImageChops.difference(crop, bg).convert("L")
    mask = diff.point(lambda p: 255 if p > 22 else 0)
    bbox = mask.getbbox()
    if not bbox:
        return crop
    left = max(bbox[0] - pad, 0)
    top = max(bbox[1] - pad, 0)
    right = min(bbox[2] + pad, crop.width)
    bottom = min(bbox[3] + pad, crop.height)
    return crop.crop((left, top, right, bottom))


def write_text(label: Label) -> str:
    lines = label.body.split("\n")
    parts = []
    for idx, line in enumerate(lines):
        y = sy(label.y) + idx * label.line_step * SCALE
        parts.append(
            f'<text class="{label.cls}" x="{sx(label.x):.1f}" y="{y:.1f}" '
            f'font-size="{label.size * SCALE:.1f}" text-anchor="{label.anchor}">{esc(line)}</text>'
        )
    return "\n".join(parts)


def write_arrow(a: Arrow) -> str:
    return (
        f'<line class="arrow" x1="{sx(a.x1):.1f}" y1="{sy(a.y1):.1f}" '
        f'x2="{sx(a.x2):.1f}" y2="{sy(a.y2):.1f}" marker-end="url(#arrowhead)"/>'
    )


def main() -> None:
    if not SRC.exists():
        raise FileNotFoundError(SRC)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CROP_DIR.mkdir(parents=True, exist_ok=True)

    img = Image.open(SRC).convert("RGB")

    # Boxes are molecule-only regions from the user-supplied route. Numbers,
    # yields, arrows, and condition text are redrawn below.
    crops = [
        Crop("1", (5, 18, 104, 112), (53, 70), "1", (0, 58), 1.00),
        Crop("2", (276, 18, 372, 118), (325, 72), "2", (0, 62), 1.00),
        Crop("3", (532, 18, 626, 118), (580, 72), "3", (0, 62), 1.00),
        Crop("4", (792, 6, 902, 125), (848, 68), "4", (0, 72), 1.00),
        Crop("5", (682, 126, 770, 210), (729, 168), "5", (0, 58), 0.95),
        Crop("6", (744, 214, 842, 316), (784, 266), "6", (0, 60), 1.00),
        Crop("7", (506, 216, 626, 318), (566, 266), "7", (0, 62), 1.00),
        Crop("8", (286, 214, 398, 318), (343, 266), "8", (0, 62), 1.00),
        Crop("9", (18, 204, 158, 320), (84, 262), "9 (X-ray)", (0, 76), 1.00),
        Crop("10", (0, 386, 174, 516), (82, 452), "10", (0, 80), 1.00),
        Crop("11", (360, 386, 526, 514), (452, 452), "11", (0, 80), 1.00),
        Crop("12", (695, 384, 875, 515), (795, 452), "12", (0, 80), 1.00),
        Crop("13", (695, 552, 875, 686), (795, 620), "13", (0, 76), 1.00),
        Crop("14", (382, 548, 536, 684), (458, 620), "14", (0, 76), 1.00),
        Crop("15", (276, 502, 368, 560), (322, 532), "15", (0, 58), 1.00),
        Crop("taxol", (0, 562, 260, 686), (126, 620), "Taxol", (0, 78), 1.00),
    ]

    crop_meta: dict[str, tuple[str, int, int]] = {}
    for c in crops:
        cimg = trim_crop(img, c.box)
        path = CROP_DIR / f"compound_{c.key}.png"
        cimg.save(path)
        crop_meta[c.key] = (path.relative_to(OUT_DIR).as_posix(), cimg.width, cimg.height)

    arrows = [
        Arrow(112, 70, 262, 70),
        Arrow(387, 70, 513, 70),
        Arrow(647, 70, 783, 70),
        Arrow(838, 131, 838, 210),
        Arrow(725, 248, 632, 248),
        Arrow(494, 248, 404, 248),
        Arrow(287, 248, 154, 248),
        Arrow(76, 333, 76, 390),
        Arrow(196, 456, 340, 456),
        Arrow(554, 456, 684, 456),
        Arrow(802, 520, 802, 572),
        Arrow(725, 620, 548, 620),
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
text {
  font-family: "Arial Black", "Arial Bold", Arial, Helvetica, sans-serif;
  font-weight: 900;
  fill: #000;
  stroke: #000;
  stroke-width: 0.22;
  paint-order: stroke fill;
}
.yield { fill: #40558a; stroke: #40558a; }
.num { font-size: 16px; }
.arrow { stroke: #000; stroke-width: 1.4; fill: none; stroke-linecap: square; }
</style>""",
        """<defs>
<marker id="arrowhead" markerWidth="8" markerHeight="6" refX="7.8" refY="3" orient="auto">
  <polygon points="0 0, 8 3, 0 6" fill="#000"/>
</marker>
</defs>""",
    ]

    for c in crops:
        href, w, h = crop_meta[c.key]
        draw_w = w * SCALE * c.scale
        draw_h = h * SCALE * c.scale
        x = sx(c.center[0]) - draw_w / 2
        y = sy(c.center[1]) - draw_h / 2
        parts.append(f'<image href="{href}" x="{x:.1f}" y="{y:.1f}" width="{draw_w:.1f}" height="{draw_h:.1f}"/>')

    parts.extend(write_arrow(a) for a in arrows)
    parts.extend(write_text(label) for label in labels)

    for c in crops:
        lx = sx(c.center[0] + c.label_offset[0])
        ly = sy(c.center[1] + c.label_offset[1])
        parts.append(f'<text class="num" x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle">{esc(c.label)}</text>')

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
