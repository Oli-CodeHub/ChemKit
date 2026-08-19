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
    condition_line_step: float = 16.0
    condition_above_baseline_gap: float = 18.0
    condition_below_baseline_gap: float = 32.0
    label_font_size: float = 14.0
    structure_label_baseline_padding: float = 22.0
    qc_font_size: float = 8.5
    arrow_width: float = 1.15
    arrowhead_width: float = 7.0
    arrowhead_height: float = 5.0
    bond_line_width: float = 1.6
    fixed_bond_length: float | None = 17.0
    atom_font_size: int = 16
    atom_font_file: str = "/System/Library/Fonts/Supplemental/Arial Black.ttf"
    multiple_bond_offset: float = 0.16
    molecule_padding: float = 0.04
    additional_atom_label_padding: float = 0.02
    scale_bond_width: bool = False
    single_colour_wedge_bonds: bool = True
    molecule_temp_canvas: tuple[int, int] = (1600, 1000)
    molecule_crop_padding: float = 4.0
    route_font_family: str = '"Arial Black", "Arial Bold", Arial, Helvetica, sans-serif'
    route_font_weight: int = 900
    text_stroke_width: float = 0.35
    stereo_dash_width_scale: float = 0.72


def chemdraw_compact_style() -> RouteStyle:
    """ChemDraw/ACS-like compact paper-scheme profile."""
    return RouteStyle(
        condition_font_size=25.0,
        condition_line_step=27.0,
        condition_above_baseline_gap=20.0,
        condition_below_baseline_gap=34.0,
        label_font_size=25.0,
        structure_label_baseline_padding=35.0,
        qc_font_size=8.5,
        arrow_width=2.1,
        arrowhead_width=18.0,
        arrowhead_height=11.0,
        bond_line_width=2.05,
        fixed_bond_length=25.5,
        atom_font_size=26,
        atom_font_file="/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        multiple_bond_offset=0.18,
        molecule_padding=0.01,
        additional_atom_label_padding=0.03,
        route_font_family='"Arial Bold", Arial, Helvetica, sans-serif',
        route_font_weight=700,
        text_stroke_width=0.0,
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


def svg_content_bbox(svg_body: str, padding: float = 0.0) -> tuple[float, float, float, float]:
    """Return the visual bbox of RDKit paths and basic SVG primitives."""
    xs: list[float] = []
    ys: list[float] = []

    for path_data in re.findall(r"\sd=['\"]([^'\"]+)['\"]", svg_body):
        values = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", path_data)]
        for idx in range(0, len(values) - 1, 2):
            xs.append(values[idx])
            ys.append(values[idx + 1])

    for tag in re.findall(r"<(?:circle|ellipse|rect)\b[^>]*>", svg_body):
        attrs = dict(re.findall(r"([a-zA-Z]+)=['\"]([^'\"]+)['\"]", tag))
        if "cx" in attrs and "cy" in attrs:
            cx = float(attrs["cx"])
            cy = float(attrs["cy"])
            rx = float(attrs.get("rx") or attrs.get("r") or 0)
            ry = float(attrs.get("ry") or attrs.get("r") or 0)
            xs.extend([cx - rx, cx + rx])
            ys.extend([cy - ry, cy + ry])
        elif all(key in attrs for key in ("x", "y", "width", "height")):
            x = float(attrs["x"])
            y = float(attrs["y"])
            width = float(attrs["width"])
            height = float(attrs["height"])
            xs.extend([x, x + width])
            ys.extend([y, y + height])

    if not xs or not ys:
        raise ValueError("Could not calculate molecule SVG content bbox")
    return (
        min(xs) - padding,
        min(ys) - padding,
        max(xs) + padding,
        max(ys) + padding,
    )


def estimate_effective_bond_length(svg_body: str) -> float:
    """Estimate the untrimmed bond length from RDKit SVG path segments."""
    max_segment_by_bond: dict[int, float] = {}
    pattern = re.compile(
        r"<path class='bond-(?P<bond>\d+) atom-\d+ atom-\d+' "
        r"d='M (?P<x1>[0-9.]+),(?P<y1>[0-9.]+) L (?P<x2>[0-9.]+),(?P<y2>[0-9.]+)'"
    )
    for match in pattern.finditer(svg_body):
        dx = float(match.group("x2")) - float(match.group("x1"))
        dy = float(match.group("y2")) - float(match.group("y1"))
        length = (dx * dx + dy * dy) ** 0.5
        bond_idx = int(match.group("bond"))
        max_segment_by_bond[bond_idx] = max(max_segment_by_bond.get(bond_idx, 0.0), length)

    if not max_segment_by_bond:
        raise ValueError("Could not estimate an effective bond length")
    lengths = list(max_segment_by_bond.values())
    longest = max(lengths)
    full_lengths = sorted(length for length in lengths if length >= longest * 0.85)
    midpoint = len(full_lengths) // 2
    if len(full_lengths) % 2:
        return full_lengths[midpoint]
    return (full_lengths[midpoint - 1] + full_lengths[midpoint]) / 2


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
    opts.additionalAtomLabelPadding = style.additional_atom_label_padding
    opts.scaleBondWidth = style.scale_bond_width
    opts.singleColourWedgeBonds = style.single_colour_wedge_bonds
    if style.atom_font_file and Path(style.atom_font_file).exists():
        opts.fontFile = style.atom_font_file
    opts.useBWAtomPalette()
    drawer.DrawMolecule(mol)
    drawer.FinishDrawing()
    return strengthen_stereo_dash_bonds(inner_svg(drawer.GetDrawingText()), style)


def draw_mol_svg_at_fixed_scale(
    mol: Chem.Mol,
    style: RouteStyle,
) -> tuple[str, tuple[float, float, float, float], float]:
    """Draw on a shared large canvas, then report bbox and effective bond length."""
    width, height = style.molecule_temp_canvas
    body = draw_mol_svg(mol, width, height, style)
    bbox = svg_content_bbox(body, style.molecule_crop_padding)
    if bbox[0] <= 0 or bbox[1] <= 0 or bbox[2] >= width or bbox[3] >= height:
        raise ValueError("Molecule reached the temporary canvas edge; increase molecule_temp_canvas")
    return body, bbox, estimate_effective_bond_length(body)


def placed_molecule_bbox(
    candidate: OcsrCandidate,
    place: MolPlace,
    style: RouteStyle,
) -> tuple[float, float, float, float]:
    """Return a molecule's final visual bbox after center-only placement."""
    _, bbox, _ = draw_mol_svg_at_fixed_scale(candidate.mol, style)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    return (
        place.center[0] - width / 2,
        place.center[1] - height / 2,
        place.center[0] + width / 2,
        place.center[1] + height / 2,
    )


def horizontal_gap_center(
    left_bbox: tuple[float, float, float, float],
    right_bbox: tuple[float, float, float, float],
) -> float:
    """Return the midpoint of the visible horizontal gap between molecules."""
    if left_bbox[2] >= right_bbox[0]:
        raise ValueError("Molecule bboxes overlap; no horizontal gap is available")
    return (left_bbox[2] + right_bbox[0]) / 2


def shared_structure_label_baseline(
    molecule_bboxes: list[tuple[float, float, float, float]],
    style: RouteStyle,
) -> float:
    """Place every structure label below the lowest visible molecule edge."""
    if not molecule_bboxes:
        raise ValueError("At least one molecule bbox is required")
    return max(bbox[3] for bbox in molecule_bboxes) + style.structure_label_baseline_padding


def centered_arrow_in_gap(
    left_bbox: tuple[float, float, float, float],
    right_bbox: tuple[float, float, float, float],
    y: float,
    length: float,
    minimum_clearance: float = 12.0,
) -> Arrow:
    """Center a fixed-length arrow in the visible gap between two molecules."""
    gap = right_bbox[0] - left_bbox[2]
    if gap < length + 2 * minimum_clearance:
        raise ValueError(
            f"Horizontal gap {gap:.1f}px is too small for a {length:.1f}px arrow "
            f"with {minimum_clearance:.1f}px clearances"
        )
    center = horizontal_gap_center(left_bbox, right_bbox)
    return Arrow(center - length / 2, y, center + length / 2, y)


def draw_molecule(candidate: OcsrCandidate, place: MolPlace, style: RouteStyle) -> str:
    mol_svg, bbox, effective_bond_length = draw_mol_svg_at_fixed_scale(candidate.mol, style)
    x = place.center[0] - (bbox[0] + bbox[2]) / 2
    y = place.center[1] - (bbox[1] + bbox[3]) / 2
    parts = [
        f'<g class="mol" data-key="{esc(place.key)}" data-effective-bond-length="{effective_bond_length:.2f}" transform="translate({x:.1f},{y:.1f})">',
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


def condition_labels_for_arrow(
    arrow: Arrow,
    above: str = "",
    below: str = "",
    style: RouteStyle | None = None,
) -> list[Label]:
    """Place conditions close to an arrow using the nearest text baseline.

    The last line above the arrow is the anchor. This prevents a two- or
    three-line reagent block from drifting upward when more lines are added.
    """
    style = style or RouteStyle()
    center_x = (arrow.x1 + arrow.x2) / 2
    arrow_y = (arrow.y1 + arrow.y2) / 2
    labels: list[Label] = []

    above_lines = above.splitlines()
    if above_lines:
        first_baseline = (
            arrow_y
            - style.condition_above_baseline_gap
            - style.condition_line_step * (len(above_lines) - 1)
        )
        labels.append(
            Label(
                center_x,
                first_baseline,
                "\n".join(above_lines),
                "cond",
                style.condition_font_size,
                line_step=style.condition_line_step,
            )
        )

    if below:
        labels.append(
            Label(
                center_x,
                arrow_y + style.condition_below_baseline_gap,
                below,
                "cond",
                style.condition_font_size,
                line_step=style.condition_line_step,
            )
        )

    return labels


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
text {{ font-family: {style.route_font_family}; font-weight: {style.route_font_weight}; fill: #000; stroke: #000; stroke-width: {style.text_stroke_width:.2f}; paint-order: stroke fill; }}
.cond {{ font-size: {style.condition_font_size:.1f}px; }}
.yield {{ fill: #42517f; stroke: #42517f; font-weight: 700; }}
.num {{ font-size: {style.label_font_size:.1f}px; font-weight: 700; }}
.qc {{ fill: #9d1b1b; stroke: #9d1b1b; font-size: {style.qc_font_size:.1f}px; font-weight: 700; }}
.arrow {{ stroke: #000; stroke-width: {style.arrow_width:.2f}; fill: none; stroke-linecap: square; }}
</style>""",
        f'<defs><marker id="arrowhead" markerUnits="userSpaceOnUse" markerWidth="{style.arrowhead_width:.1f}" markerHeight="{style.arrowhead_height:.1f}" refX="{style.arrowhead_width - 0.3:.1f}" refY="{style.arrowhead_height / 2:.1f}" orient="auto"><polygon points="0 0, {style.arrowhead_width:.1f} {style.arrowhead_height / 2:.1f}, 0 {style.arrowhead_height:.1f}" fill="#000"/></marker></defs>',
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
