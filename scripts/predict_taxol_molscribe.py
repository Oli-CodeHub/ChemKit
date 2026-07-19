#!/usr/bin/env python3
"""Run MolScribe on the Taxol route molecule crops and save raw outputs."""

from __future__ import annotations

import json
from pathlib import Path

import torch
from molscribe import MolScribe


CKPT = Path("/Users/yl/Desktop/skills/ChemKit/plugins/cache/molscribe/swin_base_char_aux_1m.pth")
CROP_DIR = Path("/Users/yl/Desktop/skills/ChemKit/examples/20260626-taxol-reference-crops")
OUT = Path("/Users/yl/Desktop/skills/ChemKit/examples/20260626-taxol-molscribe-predictions.json")

ORDER = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "taxol"]


def image_for(key: str) -> Path:
    return CROP_DIR / f"compound_{key}.png"


def main() -> None:
    if not CKPT.exists():
        raise FileNotFoundError(CKPT)

    model = MolScribe(str(CKPT), device=torch.device("cpu"))
    results = {}
    for key in ORDER:
        image = image_for(key)
        if not image.exists():
            raise FileNotFoundError(image)
        print(f"predict {key}: {image}")
        results[key] = model.predict_image_file(
            str(image), return_atoms_bonds=True, return_confidence=True
        )

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
