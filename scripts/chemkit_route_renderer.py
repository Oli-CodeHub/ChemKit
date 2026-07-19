#!/usr/bin/env python3
"""Reusable SVG route renderer for ChemKit RDKit molecules."""

from __future__ import annotations

import html
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from rdkit import Chem
from rdkit.Chem.Draw import rdMolDraw2D

from chemkit_ocsr import OcsrCandidate


def esc(text: str) -> str:
    return html.escape(text, quote=True)


@dataclass(frozen=True)
class MolPlace:
    key: str
    center: tuple[float, float]
    box: tuple[float, float]
    label: str
    label_y: float


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


@dataclass(frozen=True)
class RouteStyle:
    condition_font_size: float = 14.0
    label_font_size: float = 14.0
    qc_font_size: float = 8.5
    arrow_width: float = 1.15
    arrowhead_width: float = 7.0
    arrowhead_height: float = 5.0
    bond_line_width: float = 1.6
    fixed_bond_length: float | None = None
    atom_font_size: int = 16
    atom_font_file: str = "/System/Library/Fonts/Supplemental/Arial Black.ttf"
    multiple_bond_offset: float = 0.16
    molecule_padding: float = 0.04
    text_stroke_width: float = 0.35
    stereo_dash_width_scale: float = 0.72


def chemdraw_compact_style() -> RouteStyle:
    """ChemDraw-like compact paper-scheme profile."""
    return RouteStyle(
        condition_font_size=14.0,
        label_font_size=14.0,
        qc_font_size=8.5,
        arrow_width=1.2,
        arrowhead_width=7.0,
        arrowhead_height=4.8,
        bond_line_width=1.65,
        fixed_bond_length=20.0,
        atom_font_size=18,
        multiple_bond_offset=0.16,
        molecule_padding=0.02,
        text_stroke_width=0.24,
    )


def inner_svg(svg: str) -> str:
    start = svg.find(">", svg.find("<svg")) + 1
    end = svg.rfind("</svg>")
    return svg[start:end]


def strengthen_stereo_dash_bonds(svg: str, style: RouteStyle) -> str:
    """Make RDKit dashed wedge segments match the route's visual weight."""
    target_width = style.bond_line_width * style.stereo_dash_width_scale
    thin_threshold = style.bond_line_width * 0.65

    def replace_width(match: re.Match[str]) -> str:
        path = match.group(0)
        width = float(match.group("width"))
        if width >= thin_threshold:
            return path
        return path.replace(f"stroke-width:{width:g}px", f"stroke-width:{target_width:.2f}px")

    return re.sub(
        r"<path class='bond-[^']+'[^>]*stroke-width:(?P<width>[0-9.]+)px[^>]*/>",
        replace_width,
        svg,
    )


def draw_mol_svg(mol: Chem.Mol, width: int, height: int, style: RouteStyle) -> str:
    drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
    opts = drawer.drawOptions()
    opts.clearBackground = False
    opts.padding = style.molecule_padding
    opts.fixedFontSize = style.atom_font_size
    opts.minFontSize = style.atom_font_size
    opts.maxFontSize = style.atom_font_size
    opts.bondLineWidth = style.bond_line_width
    if style.fixed_bond_length is not None:
        opts.fixedBondLength = style.fixed_bond_length
    opts.multipleBondOffset = style.multiple_bond_offset
    if style.atom_font_file and Path(style.atom_font_file).exists():
        opts.fontFile = style.atom_font_file
    opts.useBWAtomPalette()
    drawer.DrawMolecule(mol)
    drawer.FinishDrawing()
    return strengthen_stereo_dash_bonds(inner_svg(drawer.GetDrawingText()), style)


def draw_molecule(candidate: OcsrCandidate, place: MolPlace, style: RouteStyle) -> str:
    w, h = int(place.box[0]), int(place.box[1])
    x = place.center[0] - w / 2
    y = place.center[1] - h / 2
    mol_svg = draw_mol_svg(candidate.mol, w, h, style)
    parts = [
        f'<g class="mol" data-key="{esc(place.key)}" transform="translate({x:.1f},{y:.1f})">',
        mol_svg,
        "</g>",
        f'<text class="num" x="{place.center[0]:.1f}" y="{place.label_y:.1f}" text-anchor="middle">{esc(place.label)}</text>',
    ]
    if not candidate.is_sanitized:
        parts.append(
            f'<text class="qc" x="{place.center[0]:.1f}" y="{place.label_y + 13:.1f}" text-anchor="middle">check structure</text>'
        )
    return "\n".join(parts)


def draw_arrow(arrow: Arrow) -> str:
    return (
        f'<line class="arrow" x1="{arrow.x1:.1f}" y1="{arrow.y1:.1f}" '
        f'x2="{arrow.x2:.1f}" y2="{arrow.y2:.1f}" marker-end="url(#arrowhead)"/>'
    )


def draw_label(label: Label) -> str:
    parts = []
    for idx, line in enumerate(label.body.split("\n")):
        y = label.y + idx * label.line_step
        parts.append(
            f'<text class="{label.cls}" x="{label.x:.1f}" y="{y:.1f}" '
            f'font-size="{label.size:.1f}" text-anchor="{label.anchor}">{esc(line)}</text>'
        )
    return "\n".join(parts)


def render_route_svg(
    candidates: dict[str, OcsrCandidate],
    places: list[MolPlace],
    arrows: list[Arrow],
    labels: list[Label],
    width: int,
    height: int,
    style: RouteStyle | None = None,
) -> str:
    style = style or RouteStyle()
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f"""<style>
text {{ font-family: "Arial Black", "Arial Bold", Arial, Helvetica, sans-serif; font-weight: 900; fill: #000; stroke: #000; stroke-width: {style.text_stroke_width:.2f}; paint-order: stroke fill; }}
.cond {{ font-size: {style.condition_font_size:.1f}px; }}
.yield {{ fill: #42517f; stroke: #42517f; font-weight: 700; }}
.num {{ font-size: {style.label_font_size:.1f}px; font-weight: 700; }}
.qc {{ fill: #9d1b1b; stroke: #9d1b1b; font-size: {style.qc_font_size:.1f}px; font-weight: 700; }}
.arrow {{ stroke: #000; stroke-width: {style.arrow_width:.2f}; fill: none; stroke-linecap: square; }}
</style>""",
        f'<defs><marker id="arrowhead" markerWidth="{style.arrowhead_width:.1f}" markerHeight="{style.arrowhead_height:.1f}" refX="{style.arrowhead_width - 0.3:.1f}" refY="{style.arrowhead_height / 2:.1f}" orient="auto"><polygon points="0 0, {style.arrowhead_width:.1f} {style.arrowhead_height / 2:.1f}, 0 {style.arrowhead_height:.1f}" fill="#000"/></marker></defs>',
    ]
    parts.extend(draw_arrow(arrow) for arrow in arrows)
    parts.extend(draw_label(label) for label in labels)
    parts.extend(draw_molecule(candidates[place.key], place, style) for place in places)
    parts.append("</svg>")
    return "\n".join(parts)


def write_svg(path: str | Path, svg: str) -> Path:
    output = Path(path)
    output.write_text(svg, encoding="utf-8")
    return output


def screenshot_svg(svg_path: str | Path, png_path: str | Path, width: int, height: int) -> bool:
    chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    if not chrome.exists():
        return False
    subprocess.run(
        [
            str(chrome),
            "--headless=new",
            "--disable-gpu",
            f"--screenshot={Path(png_path)}",
            f"--window-size={width},{height}",
            Path(svg_path).resolve().as_uri(),
        ],
        check=True,
    )
    return True
