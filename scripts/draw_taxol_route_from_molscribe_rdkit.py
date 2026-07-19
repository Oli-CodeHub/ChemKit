#!/usr/bin/env python3
"""Draw the Taxol screenshot recognition result with RDKit.

This script is intentionally route-specific, but it uses reusable
ChemKit modules for OCSR graph conversion, RDKit molecule drawing, route
layout, and QC reporting.
"""

from __future__ import annotations

from pathlib import Path

from chemkit_ocsr import candidates_from_predictions, load_predictions, write_qc_report
from chemkit_route_renderer import Arrow, Label, MolPlace, render_route_svg, screenshot_svg, write_svg


ROOT = Path("/Users/yl/Desktop/skills/ChemKit")
PRED = ROOT / "examples/20260626-taxol-molscribe-predictions.json"
OUT_DIR = ROOT / "examples"
SVG = OUT_DIR / "20260626-taxol-route-rdkit-from-ocsr-diagnostic.svg"
PNG = OUT_DIR / "20260626-taxol-route-rdkit-from-ocsr-diagnostic.png"
REPORT = OUT_DIR / "20260626-taxol-route-rdkit-from-ocsr-report.json"

WIDTH = 1320
HEIGHT = 1040


def taxol_places() -> list[MolPlace]:
    return [
        MolPlace("1", (80, 118), (150, 132), "1", 206),
        MolPlace("2", (360, 118), (150, 132), "2", 206),
        MolPlace("3", (655, 118), (150, 132), "3", 206),
        MolPlace("4", (1090, 120), (170, 150), "4", 226),
        MolPlace("5", (990, 262), (128, 112), "5", 338),
        MolPlace("6", (1095, 393), (174, 150), "6", 490),
        MolPlace("7", (785, 393), (184, 150), "7", 490),
        MolPlace("8", (475, 393), (174, 150), "8", 490),
        MolPlace("9", (145, 390), (204, 164), "9 (X-ray)", 502),
        MolPlace("10", (140, 650), (224, 172), "10", 778),
        MolPlace("11", (610, 650), (214, 172), "11", 778),
        MolPlace("12", (1070, 650), (224, 176), "12", 778),
        MolPlace("13", (1070, 900), (224, 176), "13", 1010),
        MolPlace("14", (620, 900), (214, 176), "14", 1010),
        MolPlace("15", (425, 760), (112, 84), "15", 815),
        MolPlace("taxol", (170, 900), (270, 176), "Taxol", 1010),
    ]


def taxol_arrows() -> list[Arrow]:
    return [
        Arrow(170, 118, 285, 118),
        Arrow(435, 118, 570, 118),
        Arrow(740, 118, 980, 118),
        Arrow(1090, 235, 1090, 310),
        Arrow(1015, 390, 895, 390),
        Arrow(700, 390, 585, 390),
        Arrow(390, 390, 250, 390),
        Arrow(145, 522, 145, 568),
        Arrow(245, 650, 500, 650),
        Arrow(720, 650, 955, 650),
        Arrow(1070, 790, 1070, 835),
        Arrow(970, 900, 735, 900),
        Arrow(515, 900, 300, 900),
    ]


def taxol_labels() -> list[Label]:
    return [
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
        Label(82, 538, "69%\n2 steps", "yield", 10.5),
        Label(215, 538, "Pd/C, H₂; TESOTf\nPCC", size=10.5),
        Label(375, 598, "(i) TsNHNH₂, NaBH₄\n(ii) TMSim\n(iii) catecholborane;\nNaOAc, heated", size=11, line_step=13),
        Label(375, 680, "37%, 3 steps", "yield", 11),
        Label(835, 622, "hν, O₂, TPP;\nPMe₃", size=11),
        Label(835, 680, "82%", "yield", 11),
        Label(1165, 805, "MsCl, OsO₄", size=11),
        Label(1165, 852, "75%", "yield", 11),
        Label(850, 873, "DIPEA; Ac₂O; TBAF", size=11),
        Label(850, 926, "32%", "yield", 11),
        Label(425, 867, "PhLi, 15;\nHF-Py", size=11),
        Label(425, 926, "68%", "yield", 11),
    ]


def main() -> None:
    predictions = load_predictions(PRED)
    candidates = candidates_from_predictions(predictions)
    write_qc_report(REPORT, candidates)

    svg = render_route_svg(
        candidates=candidates,
        places=taxol_places(),
        arrows=taxol_arrows(),
        labels=taxol_labels(),
        width=WIDTH,
        height=HEIGHT,
    )
    write_svg(SVG, svg)
    screenshot_svg(SVG, PNG, WIDTH, HEIGHT)

    print(SVG)
    print(PNG)
    print(REPORT)


if __name__ == "__main__":
    main()
