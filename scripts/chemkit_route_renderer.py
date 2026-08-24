#!/usr/bin/env python3
"""Reusable SVG route renderer for ChemKit RDKit molecules."""

from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import sys
import webbrowser
from dataclasses import dataclass
from pathlib import Path

from rdkit import Chem
from rdkit.Chem.Draw import rdMolDraw2D

from chemkit_emphasis import EmphasisSpec, hex_to_rgb
from chemkit_model import MoleculeCandidate


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
class BracketOperation:
    """ChemDraw-style bracketed operation pointing to a target structure."""

    x_left: float
    x_right: float
    y_top: float
    y_left_bottom: float
    y_arrow_end: float


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


def _highlight_draw_args(emphasis: list[EmphasisSpec] | None) -> tuple[list[int], dict[int, tuple[float, float, float]]]:
    if not emphasis:
        return [], {}
    atoms: set[int] = set()
    atom_colors: dict[int, tuple[float, float, float]] = {}
    for spec in emphasis:
        rgb = hex_to_rgb(spec.color)
        if spec.mode in {"atom", "group"}:
            atoms.update(spec.atoms)
            atom_colors.update({index: rgb for index in spec.atoms})
    return sorted(atoms), atom_colors


def _apply_bond_emphasis(svg_body: str, emphasis: list[EmphasisSpec] | None, style: RouteStyle) -> str:
    """Recolor and thicken original RDKit bond paths in place.

    RDKit's highlight API draws a second overlay line. For ChemDraw-like
    emphasis we instead edit the original bond path style, so the selected
    bond is one red/thick line rather than a red line over a black line.
    """
    if not emphasis:
        return svg_body
    bond_styles: dict[int, tuple[str, float]] = {}
    for spec in emphasis:
        if spec.mode not in {"bond", "group"}:
            continue
        for bond_index in spec.bonds:
            previous = bond_styles.get(bond_index)
            if previous is None or spec.bond_width_multiplier >= previous[1]:
                bond_styles[bond_index] = (spec.color, spec.bond_width_multiplier)
    if not bond_styles:
        return svg_body

    pattern = re.compile(
        r"<path class='(?P<class>bond-(?P<bond>\d+)[^']*)'(?P<attrs>[^>]*)style='(?P<style>[^']*)'(?P<tail>[^>]*)/>"
    )

    def replace(match: re.Match[str]) -> str:
        bond_index = int(match.group("bond"))
        if bond_index not in bond_styles:
            return match.group(0)
        color, multiplier = bond_styles[bond_index]
        path_style = match.group("style")
        path_style = re.sub(r"stroke:[^;]+", f"stroke:{color}", path_style)
        path_style = re.sub(r"fill:(?!none;)[^;]+", f"fill:{color}", path_style)
        width_match = re.search(r"stroke-width:([0-9.]+)px", path_style)
        if width_match:
            width = float(width_match.group(1))
            path_style = path_style.replace(
                f"stroke-width:{width_match.group(1)}px",
                f"stroke-width:{width * multiplier:.2f}px",
            )
        else:
            path_style += f";stroke-width:{style.bond_line_width * multiplier:.2f}px"
        return f"<path class='{match.group('class')}'{match.group('attrs')}style='{path_style}'{match.group('tail')}/>"

    return pattern.sub(replace, svg_body)


def _apply_atom_emphasis(svg_body: str, emphasis: list[EmphasisSpec] | None) -> str:
    """Recolor RDKit's original atom glyph paths without drawing ellipses."""
    if not emphasis:
        return svg_body
    atom_colors: dict[int, str] = {}
    for spec in emphasis:
        if spec.mode not in {"atom", "group", "bond"}:
            continue
        for atom_index in spec.atoms:
            atom_colors[atom_index] = spec.color
    if not atom_colors:
        return svg_body

    pattern = re.compile(
        r"<path class='atom-(?P<atom>\d+)'(?P<body>.*?)(?P<fill>fill=')(?P<color>[^']+)(?P<tail>'/>)",
        re.DOTALL,
    )

    def replace(match: re.Match[str]) -> str:
        atom_index = int(match.group("atom"))
        color = atom_colors.get(atom_index)
        if color is None:
            return match.group(0)
        return (
            f"<path class='atom-{atom_index}'{match.group('body')}"
            f"{match.group('fill')}{color}{match.group('tail')}"
        )

    return pattern.sub(replace, svg_body)


def draw_mol_svg(
    mol: Chem.Mol,
    width: int,
    height: int,
    style: RouteStyle,
    emphasis: list[EmphasisSpec] | None = None,
) -> str:
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
    # Always draw the ordinary molecule first.  RDKit's highlight API adds
    # translucent ellipses around atoms; ChemDraw-style emphasis instead
    # recolors the original bond and atom glyph paths in place below.
    drawer.DrawMolecule(mol)
    stereo_h_overlay = draw_stereo_h_overlay(drawer, mol, style)
    repeat_overlay = draw_repeat_unit_overlay(drawer, mol, style)
    drawer.FinishDrawing()
    body = strengthen_stereo_dash_bonds(inner_svg(drawer.GetDrawingText()), style)
    body = _apply_bond_emphasis(body, emphasis, style)
    body = _apply_atom_emphasis(body, emphasis)
    return body + stereo_h_overlay + repeat_overlay


def draw_stereo_h_overlay(
    drawer: rdMolDraw2D.MolDraw2DSVG,
    mol: Chem.Mol,
    style: RouteStyle,
) -> str:
    """Draw explicit hashed H marks when a source crop shows direct H bonds.

    RDKit often represents an implicit chiral H by wedging an adjacent ring
    bond.  ChemDraw screenshots commonly show the H itself on a short hashed
    bond.  A route script can opt in with ``_chemkit_stereo_h_atoms`` mapping
    atom indices to screen-space direction vectors (for example ``[0, -1]``).
    The chemical chiral tag remains on the molecule; this is only a depiction
    correction for the source's explicit-H convention.
    """
    if not mol.HasProp("_chemkit_stereo_h_atoms"):
        return ""
    try:
        marks = json.loads(mol.GetProp("_chemkit_stereo_h_atoms"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return ""
    width = style.bond_line_width * style.stereo_dash_width_scale
    parts: list[str] = []
    for raw_index, raw_direction in marks.items():
        try:
            point = drawer.GetDrawCoords(int(raw_index))
            dx, dy = float(raw_direction[0]), float(raw_direction[1])
        except (TypeError, ValueError, KeyError, IndexError):
            continue
        length = (dx * dx + dy * dy) ** 0.5
        if length == 0:
            continue
        dx, dy = dx / length, dy / length
        start = (point.x + dx * 5.0, point.y + dy * 5.0)
        end = (point.x + dx * 27.0, point.y + dy * 27.0)
        # A short dashed line avoids inventing a new solid wedge while making
        # the H direction explicit and visually consistent with ChemDraw.
        parts.append(
            f'<path class="stereo-hash" d="M {start[0]:.2f},{start[1]:.2f} L {end[0]:.2f},{end[1]:.2f}" '
            f'style="fill:none;stroke:#000;stroke-width:{width:.2f}px;stroke-dasharray:2.6,2.6;stroke-linecap:butt"/>'
        )
    return "\n".join(parts)


def draw_repeat_unit_overlay(drawer: rdMolDraw2D.MolDraw2DSVG, mol: Chem.Mol, style: RouteStyle) -> str:
    """Add ChemDraw-style parentheses and ``n`` around one skeletal repeat atom.

    Molecules opt in by storing a short real linker in
    ``_chemkit_repeat_atom_indices`` and the specific carbon to be repeated in
    ``_chemkit_repeat_atom``. The chain remains real chemistry; only the chosen
    carbon vertex receives the ``( )n`` annotation, matching ChemDraw's
    ``-CH2-(CH2)n-CH2-`` convention rather than boxing the whole chain.
    """
    if not mol.HasProp("_chemkit_repeat_atom_indices"):
        return ""
    try:
        atom_indices = [int(index) for index in json.loads(mol.GetProp("_chemkit_repeat_atom_indices"))]
        anchor_index = int(mol.GetProp("_chemkit_repeat_atom")) if mol.HasProp("_chemkit_repeat_atom") else atom_indices[len(atom_indices) // 2]
        point = drawer.GetDrawCoords(anchor_index)
    except Exception:
        return ""
    if not atom_indices:
        return ""
    font_size = max(22.0, style.atom_font_size * 1.05)
    n_size = max(18.0, style.atom_font_size * 0.82)
    # Keep parentheses close to the selected carbon vertex. The n marker is
    # deliberately outside and slightly below/right, as in the reference crop.
    half_width = font_size * 0.26
    top = point.y - font_size * 0.58
    bottom = point.y + font_size * 0.58
    left = point.x - half_width
    right = point.x + half_width
    baseline = point.y + font_size * 0.42
    # Invisible rect makes the overlay part of the molecule bbox calculation.
    overlay = [
        f'<rect x="{left - 5:.2f}" y="{top - 2:.2f}" width="{right - left + n_size + 12:.2f}" height="{bottom - top + n_size * 0.75:.2f}" fill="none" stroke="none"/>',
        # Center each glyph on its target x coordinate so the midpoint between
        # the visible parentheses is exactly the selected carbon vertex.
        f'<text class="repeat-paren" text-anchor="middle" x="{left:.2f}" y="{baseline:.2f}" font-size="{font_size:.1f}px">(</text>',
        f'<text class="repeat-paren" text-anchor="middle" x="{right:.2f}" y="{baseline:.2f}" font-size="{font_size:.1f}px">)</text>',
        f'<text class="repeat-n" x="{right + n_size * 0.42:.2f}" y="{point.y + font_size * 0.70:.2f}" font-size="{n_size:.1f}px" font-style="normal">n</text>',
    ]
    return "\n".join(overlay)


def draw_mol_svg_at_fixed_scale(
    mol: Chem.Mol,
    style: RouteStyle,
    emphasis: list[EmphasisSpec] | None = None,
) -> tuple[str, tuple[float, float, float, float], float]:
    """Draw on a shared large canvas, then report bbox and effective bond length."""
    width, height = style.molecule_temp_canvas
    body = draw_mol_svg(mol, width, height, style, emphasis)
    bbox = svg_content_bbox(body, style.molecule_crop_padding)
    if bbox[0] <= 0 or bbox[1] <= 0 or bbox[2] >= width or bbox[3] >= height:
        raise ValueError("Molecule reached the temporary canvas edge; increase molecule_temp_canvas")
    return body, bbox, estimate_effective_bond_length(body)


def placed_molecule_bbox(
    candidate: MoleculeCandidate,
    place: MolPlace,
    style: RouteStyle,
    emphasis: list[EmphasisSpec] | None = None,
) -> tuple[float, float, float, float]:
    """Return a molecule's final visual bbox after center-only placement."""
    _, bbox, _ = draw_mol_svg_at_fixed_scale(candidate.mol, style, emphasis)
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


def draw_molecule(
    candidate: MoleculeCandidate,
    place: MolPlace,
    style: RouteStyle,
    emphasis: list[EmphasisSpec] | None = None,
) -> str:
    mol_svg, bbox, effective_bond_length = draw_mol_svg_at_fixed_scale(candidate.mol, style, emphasis)
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


def draw_bracket_operation(operation: BracketOperation) -> str:
    """Draw a top bracket with a right-hand downward reaction arrow."""
    return "\n".join(
        (
            f'<line class="arrow" x1="{operation.x_left:.1f}" y1="{operation.y_top:.1f}" '
            f'x2="{operation.x_right:.1f}" y2="{operation.y_top:.1f}"/>',
            f'<line class="arrow" x1="{operation.x_left:.1f}" y1="{operation.y_top:.1f}" '
            f'x2="{operation.x_left:.1f}" y2="{operation.y_left_bottom:.1f}"/>',
            f'<line class="arrow" x1="{operation.x_right:.1f}" y1="{operation.y_top:.1f}" '
            f'x2="{operation.x_right:.1f}" y2="{operation.y_arrow_end:.1f}" marker-end="url(#arrowhead)"/>',
        )
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


def estimate_condition_text_width(
    above: str = "",
    below: str = "",
    style: RouteStyle | None = None,
    glyph_width_factor: float = 0.55,
) -> float:
    """Estimate the widest condition line in route pixels.

    SVG text is rendered by the selected system font, so exact glyph metrics
    are not available during layout.  This conservative estimate is stable
    across platforms and is intentionally based on the final condition font,
    not on a hard-coded arrow length.
    """
    style = style or RouteStyle()
    lines = [line for block in (above, below) for line in block.splitlines() if line]
    if not lines:
        return 0.0
    return max(len(line) for line in lines) * style.condition_font_size * glyph_width_factor


def arrow_length_for_conditions(
    above: str = "",
    below: str = "",
    style: RouteStyle | None = None,
    minimum_length: float = 90.0,
    side_padding: float = 24.0,
) -> float:
    """Return an arrow length that contains its condition block visually."""
    return max(
        minimum_length,
        estimate_condition_text_width(above, below, style) + 2.0 * side_padding,
    )


def condition_labels_for_bracket(
    bracket: BracketOperation,
    above: str,
    style: RouteStyle | None = None,
    nearest_gap: float = 14.0,
) -> list[Label]:
    """Anchor a multiline condition block above a bracket operation."""
    style = style or RouteStyle()
    lines = above.splitlines()
    if not lines:
        return []
    first_baseline = (
        bracket.y_top
        - nearest_gap
        - style.condition_line_step * (len(lines) - 1)
    )
    return [
        Label(
            (bracket.x_left + bracket.x_right) / 2,
            first_baseline,
            above,
            "cond",
            style.condition_font_size,
            line_step=style.condition_line_step,
        )
    ]


def render_route_svg(
    candidates: dict[str, MoleculeCandidate],
    places: list[MolPlace],
    arrows: list[Arrow],
    labels: list[Label],
    width: int,
    height: int,
    style: RouteStyle | None = None,
    emphasis: dict[str, list[EmphasisSpec]] | None = None,
    bracket_operations: list[BracketOperation] | None = None,
) -> str:
    style = style or RouteStyle()
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f"""<style>
text {{ font-family: {style.route_font_family}; font-weight: {style.route_font_weight}; fill: #000; stroke: #000; stroke-width: {style.text_stroke_width:.2f}; paint-order: stroke fill; }}
.cond {{ font-size: {style.condition_font_size:.1f}px; }}
.repeat-paren, .repeat-n {{ font-family: {style.route_font_family}; font-weight: 400; fill: #000; stroke: none; }}
.yield {{ fill: #42517f; stroke: #42517f; font-weight: 700; }}
.num {{ font-size: {style.label_font_size:.1f}px; font-weight: 700; }}
.qc {{ fill: #9d1b1b; stroke: #9d1b1b; font-size: {style.qc_font_size:.1f}px; font-weight: 700; }}
.arrow {{ stroke: #000; stroke-width: {style.arrow_width:.2f}; fill: none; stroke-linecap: square; }}
</style>""",
        f'<defs><marker id="arrowhead" markerUnits="userSpaceOnUse" markerWidth="{style.arrowhead_width:.1f}" markerHeight="{style.arrowhead_height:.1f}" refX="{style.arrowhead_width - 0.3:.1f}" refY="{style.arrowhead_height / 2:.1f}" orient="auto"><polygon points="0 0, {style.arrowhead_width:.1f} {style.arrowhead_height / 2:.1f}, 0 {style.arrowhead_height:.1f}" fill="#000"/></marker></defs>',
    ]
    parts.extend(draw_arrow(arrow) for arrow in arrows)
    parts.extend(draw_bracket_operation(operation) for operation in (bracket_operations or []))
    parts.extend(draw_label(label) for label in labels)
    parts.extend(
        draw_molecule(candidates[place.key], place, style, (emphasis or {}).get(place.key))
        for place in places
    )
    parts.append("</svg>")
    return "\n".join(parts)


def route_svg_content_bbox(svg: str, padding: float = 0.0) -> tuple[float, float, float, float]:
    """Estimate the visible bbox of a complete route, including text/arrows."""
    body = inner_svg(svg)
    xs: list[float] = []
    ys: list[float] = []
    # Molecule paths and repeat-unit overlay primitives live in translated
    # groups. Apply each group's translation before taking the route bbox.
    group_spans: list[tuple[int, int]] = []
    for match in re.finditer(
        r'<g\b[^>]*transform="translate\((?P<x>-?[0-9.]+),(?P<y>-?[0-9.]+)\)"[^>]*>(?P<body>.*?)</g>',
        body,
        re.S,
    ):
        try:
            tx, ty = float(match.group("x")), float(match.group("y"))
            group_bbox = svg_content_bbox(match.group("body"), 0.0)
        except (ValueError, KeyError):
            continue
        xs.extend([group_bbox[0] + tx, group_bbox[2] + tx])
        ys.extend([group_bbox[1] + ty, group_bbox[3] + ty])
        group_spans.append(match.span())

    # Include any non-group paths (if a caller adds route-level geometry).
    remaining = body
    for start, end in reversed(group_spans):
        remaining = remaining[:start] + remaining[end:]
    if re.search(r"\sd=['\"]", remaining):
        path_bbox = svg_content_bbox(remaining, 0.0)
        xs.extend([path_bbox[0], path_bbox[2]])
        ys.extend([path_bbox[1], path_bbox[3]])
    # Arrows and other route lines.
    for tag in re.findall(r"<line\b[^>]*>", body):
        attrs = dict(re.findall(r"([a-zA-Z-]+)=['\"]([^'\"]+)['\"]", tag))
        try:
            x1, y1 = float(attrs["x1"]), float(attrs["y1"])
            x2, y2 = float(attrs["x2"]), float(attrs["y2"])
        except (KeyError, ValueError):
            continue
        xs.extend([x1, x2])
        ys.extend([y1, y2])
    # Route labels are plain SVG text. Approximate glyph extents conservatively
    # so labels and conditions are never clipped by the final crop.
    for match in re.finditer(r"<text\b(?P<attrs>[^>]*)>(?P<body>.*?)</text>", body, re.S):
        attrs = dict(re.findall(r"([a-zA-Z-]+)=['\"]([^'\"]+)['\"]", match.group("attrs")))
        try:
            x, y = float(attrs.get("x", "0")), float(attrs.get("y", "0"))
        except ValueError:
            continue
        text = html.unescape(re.sub(r"<[^>]+>", "", match.group("body")))
        if not text:
            continue
        try:
            font_size = float(attrs.get("font-size", "28"))
        except ValueError:
            font_size = 28.0
        width = max(font_size * 0.55 * len(text), font_size * 0.5)
        anchor = attrs.get("text-anchor", "start")
        if anchor == "middle":
            left, right = x - width / 2, x + width / 2
        elif anchor == "end":
            left, right = x - width, x
        else:
            left, right = x, x + width
        xs.extend([left, right])
        ys.extend([y - font_size * 1.15, y + font_size * 0.3])
    if not xs or not ys:
        raise ValueError("Could not calculate route SVG content bbox")
    return min(xs) - padding, min(ys) - padding, max(xs) + padding, max(ys) + padding


def tighten_route_svg(svg: str, padding: float = 32.0) -> tuple[str, tuple[int, int, int, int]]:
    """Crop a route to its visible content without changing its scale."""
    left, top, right, bottom = route_svg_content_bbox(svg, padding)
    left, top = max(0.0, left), max(0.0, top)
    width = max(1, int(round(right - left)))
    height = max(1, int(round(bottom - top)))
    root = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="{left:.2f} {top:.2f} {width} {height}">'
    return root + inner_svg(svg) + "</svg>", (int(round(left)), int(round(top)), width, height)


def write_svg(path: str | Path, svg: str) -> Path:
    output = Path(path)
    output.write_text(svg, encoding="utf-8")
    return output


def _browser_candidates() -> list[tuple[str, str]]:
    """Return installed browser candidates for optional headless export."""
    candidates: list[tuple[str, str]] = []
    explicit_value = os.environ.get("CHEMKIT_BROWSER")
    explicit = shutil.which(explicit_value) if explicit_value else None
    if explicit:
        kind = "firefox" if Path(explicit).name.lower() == "firefox" else "chromium"
        candidates.append((explicit, kind))

    chromium_names = (
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "microsoft-edge",
        "msedge",
        "brave",
    )
    for name in chromium_names:
        executable = shutil.which(name)
        if executable:
            candidates.append((executable, "chromium"))

    firefox = shutil.which("firefox")
    if firefox:
        candidates.append((firefox, "firefox"))

    if sys.platform == "darwin":
        for candidate in (
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
            Path("/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"),
            Path("/Applications/Firefox.app/Contents/MacOS/firefox"),
        ):
            if candidate.exists():
                kind = "firefox" if candidate.name == "firefox" else "chromium"
                candidates.append((str(candidate), kind))
    return candidates


def open_svg_in_default_browser(svg_path: str | Path) -> bool:
    """Open an SVG with Safari/Chrome/Firefox/Edge or the registered browser."""
    path = Path(svg_path).expanduser().resolve()
    if not path.exists():
        return False
    return bool(webbrowser.open(path.as_uri(), new=2))


def screenshot_svg(svg_path: str | Path, png_path: str | Path, width: int, height: int) -> bool:
    """Optionally rasterize SVG with any available Chromium-family browser.

    Preview does not depend on this function: an SVG can always be opened in
    the system's default browser. PNG export is a convenience and returns
    ``False`` when no compatible headless browser is installed.
    """
    candidates = _browser_candidates()
    if not candidates:
        return False
    executable, kind = candidates[0]
    svg_uri = Path(svg_path).expanduser().resolve().as_uri()
    output = Path(png_path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if kind == "firefox":
        command = [
            executable,
            "--headless",
            f"--screenshot={output}",
            f"--window-size={width},{height}",
            svg_uri,
        ]
    else:
        command = [
            executable,
            "--headless=new",
            "--disable-gpu",
            f"--screenshot={output}",
            f"--window-size={width},{height}",
            svg_uri,
        ]
    subprocess.run(command, check=True)
    return output.exists()
