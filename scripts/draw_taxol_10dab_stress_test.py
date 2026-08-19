#!/usr/bin/env python3
"""High-intensity ChemKit layout test for the supplied 10-DAB/Taxol route.

The complex taxane and beta-lactam structures are preserved as tightly
cropped source images because the supplied raster is not sufficient to
reliably reconstruct every stereocenter with RDKit. Route geometry,
typography, arrows, conditions, and spacing use the current ChemKit profile.
"""

from __future__ import annotations

import html
from pathlib import Path
import subprocess

from PIL import Image, ImageChops, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "examples"
CROP_DIR = OUT_DIR / "20260819-taxol-10dab-stress-crops"
SVG = OUT_DIR / "20260819-taxol-10dab-stress-test.svg"
PNG = OUT_DIR / "20260819-taxol-10dab-stress-test.png"
SOURCE = Path(
    "/var/folders/__/t65vg_bx3wg_3x16sx9x4b5w0000gn/"
    "T/codex-clipboard-5015e6a5-ccb9-4652-abf5-1911f6c46e9f.png"
)

WIDTH = 1800
HEIGHT = 1100
FONT_PATH = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_FALLBACK = "/System/Library/Fonts/Arial.ttf"


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def trim_crop(image: Image.Image, pad: int = 6) -> Image.Image:
    image = image.convert("RGB")
    white = Image.new("RGB", image.size, "white")
    diff = ImageChops.difference(image, white).convert("L")
    mask = diff.point(lambda value: 255 if value > 22 else 0)
    bbox = mask.getbbox()
    if not bbox:
        return image
    left = max(0, bbox[0] - pad)
    top = max(0, bbox[1] - pad)
    right = min(image.width, bbox[2] + pad)
    bottom = min(image.height, bbox[3] + pad)
    return image.crop((left, top, right, bottom))


def write_crops() -> dict[str, tuple[str, int, int]]:
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    CROP_DIR.mkdir(parents=True, exist_ok=True)
    source = Image.open(SOURCE).convert("RGB")

    boxes = {
        # Structure only; labels below are redrawn as vector text.
        "dab": (0, 0, 315, 215),
        "protected": (495, 0, 800, 220),
        "beta_lactam": (315, 200, 485, 320),
        "side_chain": (315, 380, 525, 545),
    }
    outputs: dict[str, Image.Image] = {
        name: trim_crop(source.crop(box)) for name, box in boxes.items()
    }

    # The final taxane has the same supplied scaffold and lower protecting
    # groups as the protected intermediate; only OTES -> OH changes. Reuse
    # that clean source crop, replacing only the top-right label. This also
    # avoids copying the source screenshot watermark into the test output.
    final = source.crop(boxes["protected"]).convert("RGB")
    draw = ImageDraw.Draw(final)
    draw.rectangle((207, 0, final.width, 40), fill="white")
    font_path = FONT_PATH if Path(FONT_PATH).exists() else FONT_FALLBACK
    draw.text((220, 3), "OH", font=ImageFont.truetype(font_path, 24), fill="black")
    outputs["final_taxane"] = trim_crop(final)

    meta: dict[str, tuple[str, int, int]] = {}
    for name, image in outputs.items():
        path = CROP_DIR / f"{name}.png"
        image.save(path)
        meta[name] = (path.relative_to(OUT_DIR).as_posix(), image.width, image.height)
    return meta


def image_tag(meta: tuple[str, int, int], center: tuple[float, float], scale: float) -> str:
    href, width, height = meta
    draw_width = width * scale
    draw_height = height * scale
    x = center[0] - draw_width / 2
    y = center[1] - draw_height / 2
    return (
        f'<image href="{esc(href)}" x="{x:.1f}" y="{y:.1f}" '
        f'width="{draw_width:.1f}" height="{draw_height:.1f}"/>'
    )


def text_tag(
    x: float,
    y: float,
    body: str,
    size: float = 25.0,
    anchor: str = "middle",
    line_step: float = 27.0,
    cls: str = "text",
) -> str:
    lines = body.split("\n")
    return "\n".join(
        f'<text class="{cls}" x="{x:.1f}" y="{y + idx * line_step:.1f}" '
        f'font-size="{size:.1f}" text-anchor="{anchor}">{esc(line)}</text>'
        for idx, line in enumerate(lines)
    )


def arrow_tag(x1: float, y1: float, x2: float, y2: float) -> str:
    return (
        f'<line class="arrow" x1="{x1:.1f}" y1="{y1:.1f}" '
        f'x2="{x2:.1f}" y2="{y2:.1f}" marker-end="url(#arrowhead)"/>'
    )


def main() -> None:
    meta = write_crops()
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
        '<rect width="100%" height="100%" fill="white"/>',
        """<style>
text { font-family: "Arial Bold", Arial, Helvetica, sans-serif; font-weight: 700; fill: #000; stroke: none; }
.condition { font-size: 25px; }
.caption { font-size: 25px; }
.arrow { stroke: #000; stroke-width: 2.1; fill: none; stroke-linecap: square; }
</style>""",
        '<defs><marker id="arrowhead" markerUnits="userSpaceOnUse" markerWidth="18" markerHeight="11" refX="17.7" refY="5.5" orient="auto"><polygon points="0 0, 18 5.5, 0 11" fill="#000"/></marker></defs>',
    ]

    scale = 1.45
    parts.extend(
        [
            image_tag(meta["dab"], (300, 220), scale),
            image_tag(meta["protected"], (1450, 220), scale),
            image_tag(meta["beta_lactam"], (900, 510), scale),
            image_tag(meta["side_chain"], (820, 850), scale),
            image_tag(meta["final_taxane"], (1450, 850), scale),
        ]
    )

    # Top protection/activation step.
    parts.append(arrow_tag(675, 220, 1085, 220))
    parts.append(text_tag(880, 142, "1. TESCl, Py\n2. AcCl, Py", cls="condition"))
    parts.append(text_tag(880, 280, "74%\n2 steps", cls="condition"))

    # A-mediated side-chain installation.
    parts.append(arrow_tag(1450, 355, 1450, 720))
    parts.append(text_tag(1510, 490, "A, DMAP\nPy; 92%", anchor="start", cls="condition"))

    # Final deprotection to Taxol (left-pointing arrow).
    parts.append(arrow_tag(560, 850, 280, 850))
    parts.append(text_tag(420, 790, "0.5% HCl", cls="condition"))
    parts.append(text_tag(420, 915, "90%", cls="condition"))

    parts.extend(
        [
            text_tag(300, 515, "10-deacetylbaccatin III\n(10-DAB)", cls="caption"),
            text_tag(900, 655, "A", cls="caption"),
            text_tag(165, 865, "(-)-Taxol", cls="caption"),
        ]
    )
    parts.append("</svg>")
    SVG.write_text("\n".join(parts), encoding="utf-8")

    chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    if not chrome.exists():
        raise RuntimeError("Google Chrome is required to render the PNG preview")
    subprocess.run(
        [
            str(chrome),
            "--headless=new",
            "--disable-gpu",
            f"--screenshot={PNG}",
            f"--window-size={WIDTH},{HEIGHT}",
            SVG.as_uri(),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(SVG)
    print(PNG)


if __name__ == "__main__":
    main()
