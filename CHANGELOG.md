# Changelog

## 1.0 — 2026-08-20

ChemKit 1.0 formally replaces the earlier prototype workflow.

### Highlights

- Fixed effective-bond-scale rendering for consistent molecule proportions.
- ChemDraw/ACS-like atom, condition, structure-label, arrow, and line-width
  hierarchy.
- Route-level placement based on visible molecule boundaries, including plus
  signs, arrows, conditions, and shared structure-label baselines.
- Dual-fragment orientation preservation for coupling products.
- Stronger stereochemical wedges and improved SVG/PNG readability.
- Reusable FAT route examples, Taxol/10-DAB high-intensity testing, and
  regression coverage for fixed-scale rendering.
- 16:9 and 9:16 promotional graphics, including a ChemDraw vs ChemKit
  comparison.

### Migration

New routes should use `scripts/chemkit_route_renderer.py` and
`chemdraw_compact_style()`. Older one-off scripts remain under the legacy
section and should be ported to the 1.0 renderer before reuse.
