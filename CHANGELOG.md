# Changelog

## 1.1 — 2026-08-24

ChemKit 1.1 expands the stable renderer with improved route transcription,
layout controls, and reusable Agent workflows.

### Highlights

- Improved reaction-condition centering and spacing across multi-step routes.
- Refined structure orientation and functional-group label placement for more
  conventional ChemDraw-like output.
- Added Agent-assisted screenshot transcription guidance and QC examples.
- Added reusable CLI/model/emphasis components and broader regression tests.
- Added new publication-style route examples and cross-platform installation
  improvements.

## 1.0 — 2026-08-20

ChemKit 1.0 formally replaces the earlier prototype workflow.

### Highlights

- Fixed effective-bond-scale rendering for consistent molecule proportions.
- ChemDraw/ACS-like atom, condition, structure-label, arrow, and line-width
  hierarchy.
- Route-level placement based on visible molecule boundaries, including plus
  signs, arrows, conditions, and shared structure-label baselines.
- Logical-infinite-canvas route layout with automatic content-bbox tightening:
  final SVG/PNG crops whitespace without rescaling structures.
- Optional semantic emphasis layer for coloring or thickening selected atoms,
  bonds, functional groups, and route intermediates with auditable indices.
- Dual-fragment orientation preservation for coupling products.
- Stronger stereochemical wedges and improved SVG/PNG readability.
- Reusable FAT route examples, Taxol/10-DAB high-intensity testing, and
  regression coverage for fixed-scale rendering.
- 16:9 and 9:16 promotional graphics, including a ChemDraw vs ChemKit
  comparison.
- Agent-first packaging: cross-platform one-command installers, an isolated
  runtime, a deterministic CLI, repository-relative paths, and browser-
  agnostic SVG preview. The unused local web prototype was removed.

### Migration

New routes should use `scripts/chemkit_route_renderer.py` and
`chemdraw_compact_style()`. Older one-off scripts remain under the legacy
section and should be ported to the 1.0 renderer before reuse.
