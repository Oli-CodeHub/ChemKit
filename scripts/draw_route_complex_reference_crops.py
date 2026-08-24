#!/usr/bin/env python3
"""Fast hybrid redraw for a screenshot-based synthetic route.

Complex structures remain as evidence-preserving image crops. ChemKit redraws
the route-level elements (arrows, labels, plus signs, and numbering), avoiding
low-confidence chemical hallucinations while keeping the first render fast.
"""

from __future__ import annotations

import base64
import html
import json
import os
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get("CHEMKIT_REFERENCE_IMAGE", ROOT / "examples" / "complex-route-reference.png"))
OUT_DIR = ROOT / "examples"
SVG = OUT_DIR / "20260820-route-hybrid-reference.svg"
PNG = OUT_DIR / "20260820-route-hybrid-reference.png"
MANIFEST = OUT_DIR / "20260820-route-hybrid-reference.json"
WIDTH, HEIGHT = 3150, 1834


@dataclass(frozen=True)
class Crop:
    name: str
    source_box: tuple[int, int, int, int]
    target_box: tuple[int, int, int, int]
    label: str


CROPS = [
    Crop("1", (0, 220, 470, 480), (55, 205, 445, 520), "1"),
    # Start just after the preceding arrowhead so the scaffold is never cut
    # by the edge masks below.
    Crop("3w", (730, 220, 1350, 535), (720, 205, 1400, 525), "3w"),
    Crop("2", (1630, 0, 2260, 540), (1600, 55, 2310, 555), "2"),
    Crop("3", (2410, 0, 3148, 540), (2370, 55, 3135, 555), "3"),
    Crop("4", (0, 700, 640, 1080), (35, 700, 625, 1120), "4"),
    Crop("5a-5d", (730, 680, 1520, 1060), (735, 700, 1510, 1120), "5a–5d"),
    Crop("6a-6d", (1620, 580, 3060, 1100), (1580, 600, 3070, 1135), "6a–6d"),
    Crop("7", (680, 1220, 1660, 1720), (700, 1150, 1650, 1805), "7"),
    Crop("A1-A4", (1880, 1180, 3148, 1780), (1880, 1110, 3145, 1815), "A1–A4  n=1, 2, 6, 10"),
]


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def trim_crop(image: Image.Image, pad: int = 8) -> Image.Image:
    image = image.convert("RGB")
    white = Image.new("RGB", image.size, "white")
    diff = ImageChops.difference(image, white).convert("L")
    mask = diff.point(lambda value: 255 if value > 18 else 0)
    bbox = mask.getbbox()
    if not bbox:
        return image
    left = max(0, bbox[0] - pad)
    top = max(0, bbox[1] - pad)
    right = min(image.width, bbox[2] + pad)
    bottom = min(image.height, bbox[3] + pad)
    return image.crop((left, top, right, bottom))


def image_tag(image: Image.Image, target_box: tuple[int, int, int, int]) -> str:
    left, top, right, bottom = target_box
    import io

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    data = base64.b64encode(buffer.getvalue()).decode("ascii")
    return (
        f'<image x="{left}" y="{top}" width="{right-left}" height="{bottom-top}" '
        f'preserveAspectRatio="xMidYMid meet" href="data:image/png;base64,{data}"/>'
    )


def clean_reference_crop(name: str, image: Image.Image) -> Image.Image:
    """Remove source arrows/labels at crop edges without touching the scaffold."""
    # The supplied raster has a slightly gray paper background. Normalize it
    # so separately placed structure crops disappear into the white canvas.
    image = image.convert("RGB")
    near_white = image.convert("L").point(lambda value: 255 if value >= 245 else 0)
    image = Image.composite(Image.new("RGB", image.size, "white"), image, near_white)
    draw = ImageDraw.Draw(image)
    width, height = image.size
    masks = {
        "1": ((0, 0, 0, 0), (width - 35, 0, width, height), (0, height - 35, width, height)),
        "3w": ((0, 0, 20, height), (width - 35, 0, width, height)),
        "2": ((0, 0, 20, height), (width - 60, 0, width, height)),
        "3": ((0, 0, 20, height),),
        # The source boxes end before the component labels.  Do not mask the
        # bottom: several carbonyls and ring vertices extend very low.
        "4": (),
        "5a-5d": ((0, 0, 20, height), (width - 35, 0, width, height)),
        "6a-6d": ((0, 0, 20, height),),
        "7": (),
        "A1-A4": (),
    }
    for box in masks.get(name, ()):
        draw.rectangle(box, fill="white")
    return trim_crop(image)


def text(x: float, y: float, body: str, size: float = 32, anchor: str = "middle", cls: str = "label") -> str:
    return f'<text class="{cls}" x="{x:.1f}" y="{y:.1f}" font-size="{size:.1f}" text-anchor="{anchor}">{esc(body)}</text>'


def arrow(x1: float, y: float, x2: float, label: str) -> list[str]:
    center = (x1 + x2) / 2
    return [
        f'<line class="arrow" x1="{x1:.1f}" y1="{y:.1f}" x2="{x2:.1f}" y2="{y:.1f}" marker-end="url(#arrowhead)"/>',
        text(center, y - 22, label, 30),
    ]


def plus(x: float, y: float) -> str:
    return text(x, y, "+", 36)


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(
            f"Reference image not found: {SOURCE}. Set CHEMKIT_REFERENCE_IMAGE to the supplied image path."
        )
    source = Image.open(SOURCE).convert("RGB")
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
        '<rect width="100%" height="100%" fill="white"/>',
        """<style>
        text { font-family: "Arial", "PingFang SC", sans-serif; font-weight: 700; fill: #000; }
        .label { font-size: 30px; }
        .arrow { stroke: #000; stroke-width: 2.4; fill: none; }
        </style>""",
        '<defs><marker id="arrowhead" markerUnits="userSpaceOnUse" markerWidth="20" markerHeight="14" refX="18" refY="7" orient="auto"><polygon points="0 0, 20 7, 0 14" fill="#000"/></marker></defs>',
    ]

    for crop in CROPS:
        image = clean_reference_crop(crop.name, source.crop(crop.source_box))
        parts.append(image_tag(image, crop.target_box))
        left, top, right, bottom = crop.target_box
        label_y = min(bottom + 38, HEIGHT - 28)
        parts.append(text((left + right) / 2, label_y, crop.label, 30))

    # A few source arrowheads sit just outside the scaffold crop.  Erase only
    # those narrow inter-component strips; the ChemKit arrows are added below.
    parts.extend([
        '<rect x="1365" y="320" width="75" height="105" fill="white"/>',
        '<rect x="2325" y="335" width="170" height="125" fill="white"/>',
        '<rect x="1560" y="840" width="330" height="140" fill="white"/>',
    ])

    # Top row: 1 -> 3w -> 2 -> 3
    parts.extend(arrow(475, 370, 700, "a"))
    parts.extend(arrow(1425, 370, 1580, "b"))
    parts.extend(arrow(2320, 370, 2360, "c"))

    # Coupling row: 4 + 5a–5d -> 6a–6d
    parts.append(plus(680, 925))
    parts.extend(arrow(1515, 925, 1570, "d"))

    # Final assembly row: 7 -> A1–A4
    parts.extend(arrow(1670, 1460, 1855, "e"))

    parts.append(text(40, HEIGHT - 28, "结构裁切保真模式：复杂结构保留原图，箭头与编号按 ChemKit 规则重绘。", 20, "start", "note"))
    parts.append("</svg>")
    SVG.write_text("\n".join(parts), encoding="utf-8")
    MANIFEST.write_text(json.dumps({
        "mode": "fast-hybrid-reference",
        "source": str(SOURCE),
        "structure_policy": "preserve_reference_crops",
        "redrawn_elements": ["arrows", "conditions", "plus_signs", "labels"],
        "semantic_vectorization": "not_attempted_for_low_confidence_structures",
        "qc": "visual_layout_and_route_connectivity",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Use the shared browser-agnostic SVG rasterizer when available.
    import sys

    if str(ROOT / "scripts") not in sys.path:
        sys.path.insert(0, str(ROOT / "scripts"))
    from chemkit_route_renderer import screenshot_svg

    screenshot_svg(SVG, PNG, WIDTH, HEIGHT)
    print(SVG)
    print(PNG)
    print(MANIFEST)


if __name__ == "__main__":
    main()
