#!/usr/bin/env python3
"""Fast first-pass route import for screenshot-based chemistry diagrams.

This is the safe fallback for complex structures: the supplied figure is kept
as the immutable visual evidence layer, while ChemKit records the import mode
for later OCR/vectorization. It guarantees a usable result without guessing
bond connectivity or stereochemistry.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get("CHEMKIT_REFERENCE_IMAGE", ROOT / "examples" / "complex-route-reference.png"))
OUT_DIR = ROOT / "examples"
PNG = OUT_DIR / "20260820-route-fast-reference.png"
SVG = OUT_DIR / "20260820-route-fast-reference.svg"
MANIFEST = OUT_DIR / "20260820-route-fast-reference.json"


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(f"Reference image not found: {SOURCE}")
    image = Image.open(SOURCE).convert("RGB")
    image.save(PNG, format="PNG")
    data = base64.b64encode(PNG.read_bytes()).decode("ascii")
    width, height = image.size
    SVG.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}"><image width="{width}" height="{height}" '
        f'href="data:image/png;base64,{data}"/></svg>\n',
        encoding="utf-8",
    )
    MANIFEST.write_text(json.dumps({
        "mode": "fast-reference-import",
        "source": str(SOURCE),
        "structure_policy": "immutable_reference_image",
        "semantic_vectorization": "deferred",
        "next_step": "run hybrid/vector mode only after user confirms low-confidence structures",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(PNG)
    print(SVG)
    print(MANIFEST)


if __name__ == "__main__":
    main()
