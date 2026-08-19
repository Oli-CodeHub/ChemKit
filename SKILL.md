---
name: chemkit
description: Use ChemKit 1.0 when drawing publication-style chemical structures or reaction schemes with RDKit/SVG/PDF/PNG output, especially when matching ACS/JACS/ChemDraw-like proportions without using the ChemDraw application.
---

# ChemKit 1.0

ChemKit 1.0 is the stable RDKit-first chemical drawing workflow. It complements the ChemDraw skill:

- Use ChemDraw when the required output is editable `.cdxml` or must be produced inside the local ChemDraw app.
- Use ChemKit when the required output is RDKit-generated SVG/PDF/PNG or when testing a reusable automated drawing/layout engine.

The 1.0 renderer is the default and supersedes the earlier prototype layout
rules. New route work should use `scripts/chemkit_route_renderer.py` and the
compact profile documented below.

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

## User-Confirmed Style Targets (August 2026)

The defaults below have been validated against the user's own ChemDraw
output. Treat them as the starting point for every new route; only
deviate with a reason.

- **ChemDraw/ACS proportions come before absolute pixel sizes**. Calibrate
  typography against the final rendered bond, not the RDKit
  `fixedBondLength` setting. The compact profile uses an effective bond
  near 38.25 px (25.5 × the usual 1.5-coordinate bond), 2.05 px bonds,
  26 px atom labels, 25 px condition text, 25 px structure labels, and
  18% multiple-bond spacing.
- **Arial Bold** is the compact-profile atom and route font. Set RDKit
  `MolDrawOptions.fontFile` to
  `/System/Library/Fonts/Supplemental/Arial Bold.ttf` when available;
  use weight 700 route text without an artificial outline.
- **Never let a molecule's placement box rescale it.** Draw every
  molecule on the same large temporary canvas at fixed scale, crop from
  its actual SVG bbox, and translate only. Effective unlabelled bond
  lengths across a route should agree within about 1-2%.
- **Structure labels share a single horizontal baseline**, anchored to
  the bottom of the tallest structure in the route. In the compact
  profile, put the baseline 35 px below that visible edge so 25 px labels
  retain clear white space. Do not place each label relative to its own
  structure's bottom.
- **Place route operators from visible molecule bboxes.** A plus sign is
  centered in the actual horizontal gap between two reactants. Center the
  arrow in the gap between the final reactant and product, with symmetric
  clearances, instead of using hand-tuned x-coordinates.
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
  26 px Arial Bold atom labels, fixed bond length around 25.5 px, 2.05 px
  bonds, 25 px condition text, 25 px structure labels, no artificial text
  outline, and conditions above/below the arrow as a single visual block.
  Place those conditions with
  `condition_labels_for_arrow()`; it anchors the nearest upper baseline
  20 px above the arrow in the compact profile so multi-line blocks do
  not float too high.
- For coupling products assembled from two visible reactant fragments,
  preserve both fragment orientations. Copy each reactant fragment's 2D
  coordinates into the product and join them at the new bond instead of
  matching only one MCS and globally rotating the product.

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
