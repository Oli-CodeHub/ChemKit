#!/usr/bin/env python3
"""Clean the supplied Taxol route reference image for ChemKit examples."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance


SRC = Path("/var/folders/__/t65vg_bx3wg_3x16sx9x4b5w0000gn/T/codex-clipboard-f4ea7d7b-5538-4882-bf12-81fdfa0ac2b7.png")
OUT = Path("/Users/yl/Desktop/skills/ChemKit/examples/20260626-taxol-reference-cleaned.png")
SVG = Path("/Users/yl/Desktop/skills/ChemKit/examples/20260626-taxol-reference-cleaned.svg")


def main() -> None:
    img = Image.open(SRC).convert("RGB")

    # Remove the gray watermark in the lower-right margin without touching the
    # reaction scheme. The rectangle is intentionally conservative.
    draw = ImageDraw.Draw(img)
    draw.rectangle((610, 682, img.width, img.height), fill="white")

    # Light cleanup for paper-white background while keeping thin bonds readable.
    img = ImageEnhance.Contrast(img).enhance(1.08)
    img = ImageEnhance.Sharpness(img).enhance(1.15)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT)
    SVG.write_text(
        "\n".join(
            [
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{img.width}" height="{img.height}" viewBox="0 0 {img.width} {img.height}">',
                '<rect width="100%" height="100%" fill="white"/>',
                f'<image href="{OUT.name}" x="0" y="0" width="{img.width}" height="{img.height}"/>',
                "</svg>",
            ]
        ),
        encoding="utf-8",
    )
    print(OUT)
    print(SVG)


if __name__ == "__main__":
    main()
