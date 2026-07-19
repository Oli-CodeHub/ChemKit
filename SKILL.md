---
name: chemkit
description: Use when drawing publication-style chemical structures or reaction schemes with RDKit/SVG/PDF/PNG output, especially when matching ACS/JACS/ChemDraw-like proportions without using the ChemDraw application.
---

# ChemKit

ChemKit is for RDKit-first chemical drawing. It complements the ChemDraw skill:

- Use ChemDraw when the required output is editable `.cdxml` or must be produced inside the local ChemDraw app.
- Use ChemKit when the required output is RDKit-generated SVG/PDF/PNG or when testing a reusable automated drawing/layout engine.

## Core Goal

Generate publication-style chemical structures and reaction schemes that visually resemble the user's ChemDraw ACS1996 examples:

- Consistent structure scale across reactants and products
- Compact black-and-white structures
- Small, centered reaction arrows
- Reaction conditions centered on the arrow
- Bold, readable atom labels and captions
- Generous spacing and no overlaps

When the source is a screenshot or paper figure, ChemKit first extracts
chemical information and then redraws it in the user's own style. It
does not pixel-copy another figure's layout unless the user explicitly
asks for a temporary diagnostic layout replica.

## User-Confirmed Style Targets (June 2026)

The defaults below have been validated against the user's own ChemDraw
output. Treat them as the starting point for every new route; only
deviate with a reason.

- **Bold atom labels are larger than surrounding route text**. Use
  RDKit `fixedFontSize` 16 as the default and 18 for sparse/simple
  routes where heteroatom labels need more visual weight. Condition
  text and structure labels default to 14 px.
- **Arial Black** for atom labels and for SVG `<text>`. Set RDKit
  `MolDrawOptions.fontFile` to
  `/System/Library/Fonts/Supplemental/Arial Black.ttf` when available.
  Pair SVG route text with `font-weight: 900; stroke: #000;
  stroke-width: 0.35; paint-order: stroke fill;` so the bold weight
  survives in sips / Quick Look / Preview.app.
- **Structure labels share a single horizontal baseline**, anchored to
  the bottom of the tallest structure in the route. Do not place each
  label relative to its own structure's bottom.
- **Subscript digits in chemical formulas** (`Et₃N`, `NiCl₂`,
  `Et₄NBr`) are entered as Unicode subscript characters (`\u2082`,
  `\u2083`, `\u2084`), both in SMILES and in condition strings. Avoid
  `<tspan>` for subscripts.
- **Multi-line condition blocks** use one independent `<text>` per
  line. Do not nest `<tspan dy>` inside a single `<text>`.
- **R-group placeholders** are dummy atoms in SMILES with
  `atom.SetProp("_displayLabel", "R")` set before drawing. RDKit
  renders atom labels as `<path>` glyphs, not `<text>`, so do not
  try to post-process the SVG to swap `*` → `R`.
- For compact one-row paper schemes, prefer
  `chemdraw_compact_style()` from `scripts/chemkit_route_renderer.py`:
  larger fixed atom labels, fixed bond length around 20 px, thinner SVG
  text stroke, tighter molecule padding, and condition text above/below
  the arrow as a single visual block.

See `references/rdkit-acs-style.md`, `references/reaction-layout-rules.md`,
and `references/phase-notes.md` for the full rationale and edge cases.

## Local OCSR Plugins

The screenshot/PDF recognition stack is managed inside
`plugins/manifest.json`. Source snapshots live in `plugins/sources/`;
raw recognizer outputs belong in `plugins/outputs/`.

Use `scripts/install_ocsr_plugins.sh` to fetch or refresh the local
open-source plugin sources. Use `scripts/check_ocsr_plugins.py` to
inspect whether the expected plugin folders are present.

## Workflow

1. Parse the chemistry into explicit SMILES/InChI before drawing.
2. For screenshot/PDF/DOI figure input, follow the OCSR pipeline:
   ReactionDataExtractor2 for whole-scheme segmentation, MolScribe for
   molecule crops, DECIMER as cross-check/fallback, and RxnScribe as an
   end-to-end reaction parsing fallback.
3. Treat raw OCSR atom/bond output as structure data, not as final
   drawing coordinates. If SMILES/MOL is missing or invalid but atoms
   and bonds exist, convert the graph to an RDKit `RWMol` and let RDKit
   redraw it as a diagnostic candidate.
4. Use RDKit for molecule parsing, sanitization, 2D coordinates, and SVG drawing.
5. Use `scripts/chemkit_route_renderer.py` for new route-level
   placement whenever possible; do not start new route scripts by
   copying legacy one-off drawing code.
6. Render SVG first for inspection. Export PDF/PNG only after the SVG layout is acceptable.
7. Validate:
   - Every molecule parses.
   - No molecule entered the final publication drawing from `<invalid>`
     OCSR output unless it has been rebuilt as an RDKit molecule and
     manually/chemically checked.
   - Any unsanitized RDKit molecule is marked for correction and cannot
     be treated as final.
   - Structure scales are visually consistent.
   - Arrow and condition text are centered and do not overlap structures.
   - Atom labels are bold and larger than or comparable to condition text.
   - The output resembles the user's ChemDraw examples.
   - Any low-confidence OCSR result has been confirmed with the user.

## References

- Read `references/rdkit-acs-style.md` before setting RDKit drawing parameters.
- Read `references/reaction-layout-rules.md` before placing structures, arrows, plus signs, condition text, or notes.
- Read `references/ocsr-pipeline.md` before using screenshots, paper figures, PDFs, or DOI figures as chemical sources.
- Read `references/phase-notes.md` when continuing iterative improvements to the RDKit reaction layout engine.
- Treat scripts listed in `scripts/LEGACY.md` as historical experiments,
  not as templates for new work.
- `web/` contains the lightweight Reaction Builder front-end prototype:
  natural-language input, inferred structure cards, editable condition
  fields, QC hints, and SVG preview. It is wired to the local Flask
  backend in `server.py`; `/api/status` reports whether the optional
  OpenAI parser is active or the fallback rule parser is being used.
