---
name: chemkit
description: Use ChemKit 1.1 when drawing publication-style chemical structures or reaction schemes with RDKit/SVG/PDF/PNG output, especially when matching ACS/JACS/ChemDraw-like proportions without using the ChemDraw application.
---

# ChemKit 1.1

ChemKit 1.1 is the stable RDKit-first chemical drawing workflow. It complements the ChemDraw skill:

- Use ChemDraw when the required output is editable `.cdxml` or must be produced inside the local ChemDraw app.
- Use ChemKit when the required output is RDKit-generated SVG/PDF/PNG or when testing a reusable automated drawing/layout engine.

The 1.1 renderer is the default and supersedes the earlier prototype layout
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

When the source is a screenshot or paper figure, the Agent first interprets
the chemistry from a deliberately prepared crop and then redraws it in the
user's own style. ChemKit does not call an automatic image-recognition engine
as part of the skill workflow, and it does not pixel-copy another figure's
layout unless the user explicitly asks for a temporary diagnostic replica.

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
  clearances, instead of using hand-tuned x-coordinates. Derive the arrow
  length from the widest condition line (with a small side margin), then
  allocate the molecule gap from that length so long reagent blocks never
  overhang a short arrow.
- **Use a logical infinite canvas for routes.** Lay out structures, arrows,
  conditions, plus signs, repeat markers, and captions at the fixed ChemKit
  scale on a generous working canvas. After rendering, compute the union bbox
  of every visible primitive and tighten the SVG/PNG to that bbox plus a fixed
  margin. Pass the cropped width/height to raster export as well; do not
  screenshot the original working canvas, or the PNG will retain unnecessary
  white space. Crop/translate only; never rescale the chemistry to fit a
  preset canvas. Fixed page sizes such as 16:9 are opt-in export modes.
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
- **Variable methylene chains** such as `(CH2)n` are not a single text atom.
  Draw a short skeletal zigzag motif with ordinary single bonds at both ends.
  During crop analysis, identify the exact carbon vertex that represents the
  repeat unit and record its atom index. Put parentheses around that one
  carbon vertex only; place a separate upright (non-italic) `n` at the lower
  right of the right parenthesis. Never replace it with a bare `(CH2)n` label
  or parentheses around the whole linker.
- **Emphasis is an annotation layer, not a chemistry edit.** Keep the SMILES
  unchanged and resolve requests such as “highlight the thioester in 2” to
  explicit atom/bond indices with `scripts/chemkit_emphasis.py`. Use semantic
  selectors (`functional_group`, `smarts`, or explicit indices), a scoped
  molecule key, and a style (`bond`, `atom`, or `group`). Default emphasis is
  a dark accent color and a 2× bond-width multiplier; preserve the rest of the
  ChemDraw-like black-and-white drawing. If a selector matches more than one
  location, ask the user to choose or explicitly request `match: all`—never
  silently guess. Store the resolved indices and style in the route JSON.
  Bond emphasis must recolor and widen the original bond path in place; do not
  draw a second colored line over the original black bond. Every visible atom
  glyph at either endpoint of an emphasized bond must inherit the same accent
  color automatically; a colored bond may never terminate at a black O, N,
  abbreviation, or other visible endpoint label.
- **Preserve the source conformation, not only ring connectivity.** When a
  screenshot depicts a pyranose or other saturated ring in a chair, boat, or
  envelope projection, record that projection and reproduce it with explicit
  2D coordinates. A flat regular polygon is not an acceptable substitute for
  a source-observed chair. For coupled sugars, preserve the conformation of
  every ring independently and validate axial/equatorial substituent directions
  together with wedge/dash marks.
- **Validate named cage scaffolds as graphs before styling.** For BCP
  (bicyclo[1.1.1]pentane), require exactly two bridgeheads and three distinct
  one-carbon bridges: each bridge carbon connects to both bridgeheads, with no
  direct bridgehead bond and no terminal methyl. When the source uses the
  conventional projection with one bridge carbon above and two below, preserve
  that projection instead of allowing an automatic square-like depiction.
- **Copy source abbreviations literally and keep them condensed.** If the
  source writes `CCl3`, `OBn`, `BnO`, `DPMO`, or `OCH3` as one label, use one
  display-label pseudoatom and do not expand it into explicit Cl atoms, phenyl
  rings, or extra bonds. Preserve source-specific `OBn` versus `BnO` ordering.
  Conversely, if the source explicitly draws `Ph-CH2-O`, retain that explicit
  fragment; do not collapse it merely because an abbreviation exists.
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
- **Parse route semantics before drawing.** Convert a figure into an explicit
  node/edge manifest before choosing coordinates. Record which structures are
  a mixture, which condition belongs to which edge, and whether a row break
  is a continuation of the same route. A condition shown above a bracket from
  II-2 to II-3 is an operation on that edge, not an unrelated side reaction.
- **Represent wrapped routes as horizontal continuations.** When a paper
  scheme starts a new row at the left, keep the chemical edge from the prior
  row but draw the continuation arrow horizontally from the left margin. Do
  not replace a wrapped continuation with a vertical arrow merely because the
  product above happens to be vertically aligned.
- **Lock stereochemistry before layout transforms.** For every source wedge or
  hashed bond, map the mark to an atom/bond index and record the intended
  relative configuration before writing `@`/`@@` SMILES. SMILES chirality is
  traversal-order dependent, so never guess `@` from screen direction. Set the
  final 2D coordinates first, regenerate wedge/dash directions with RDKit, and
  never mirror a finished depiction without re-wedging and rechecking every
  stereo center. If a stereo mark is ambiguous, preserve it as an uncertainty
  instead of silently selecting a diastereomer.
- **Render direct H wedges explicitly when the source does.** RDKit may encode
  an implicit chiral H by wedging an adjacent ring bond. If the screenshot
  shows a short hashed bond terminating at the `H` label, record that H atom
  direction in the molecule's stereo annotation and use the renderer's
  `stereo_h_overlay`; do not force a neighboring ring bond to be dashed.
- **Use bracketed operations for ChemDraw condition boxes.** DMP-style
  conditions with a top horizontal rule and a downward arrow should use the
  reusable `BracketOperation` primitive, with the condition label centered over
  the bracket and the arrow target attached to the intended product.
- **Use a semantic preflight for speed.** For screenshot routes, complete one
  compact manifest pass (nodes, edges, conditions, row breaks, stereo marks)
  before rendering. Then run structure transcription, layout, and style as
  separate passes. Validate local structure/route crops before regenerating a
  full canvas; do not spend iterations tuning typography while the reaction
  graph or arrow ownership is still uncertain.

See `references/rdkit-acs-style.md` and
`references/reaction-layout-rules.md` for the full rationale and edge cases.

## Installation and invocation

ChemKit is an Agent skill. Install it from a checked-out copy with the platform
wrapper (`./install.sh` on macOS/Linux or
`./install.ps1` on Windows), or run `python scripts/install_chemkit.py` when a
Python interpreter is already available. The installer copies the skill into
the active Codex skills directory, creates an isolated virtual environment,
and installs the RDKit/Pillow dependencies without changing the user's global
Python packages.

The installer accepts `--target` for non-default Agent runtimes and honors
`CODEX_HOME` or `CODEX_SKILLS_DIR` when those variables are supplied. A
runtime is still required: if the host has neither Python nor `uv`, the
installer reports the missing bootstrap prerequisite instead of silently
installing into an unknown location.

Use the CLI as the stable Agent-facing boundary:

```text
./bin/chemkit check
./bin/chemkit run scripts/draw_route_fat_amide_coupling.py
./bin/chemkit preview examples/20260819-fat-amide-coupling.svg
```

`check` validates the isolated runtime, `run` executes a repository-relative
route script, and `preview` opens SVG/PDF/PNG using the operating system's
default browser/viewer. CLI paths are resolved relative to the installed
skill or the current skill checkout, so an Agent does not need to know the
author's local filesystem path.

## Screenshot strategy for Agent analysis

For image-only input, use the Agent's visual reasoning as the recognition
layer. The quality of the screenshot is more important than installing an
image-recognition model. Ask for, or make, one crop per structure and follow
these rules:

1. Include the complete structure, including every bond endpoint, wedge/dash,
   heteroatom, abbreviation, and variable-chain marker. Keep roughly 10–20%
   white margin around it.
2. Exclude arrows, reaction conditions, yields, step numbers, neighboring
   structures, plus signs, watermarks, and captions. A label that belongs to
   the molecule (for example `Boc`, `F`, `OH`, or `(CH2)n`) must remain inside
   the crop.
3. Use the original-resolution PNG or a lossless crop. Do not use a resized
   chat thumbnail, JPEG, or a crop that clips a bond at an edge.
4. For a very wide or dense molecule, provide a second close-up of the dense
   region, but keep one full-molecule crop as the authoritative connectivity
   reference. Do not split a molecule into disconnected fragments unless the
   attachment relationship is unambiguous.
5. Name crops in route order (`01-start`, `02-intermediate`, …) and send them
   together when possible. This lets the Agent compare shared scaffolds and
   preserve orientation across intermediates.
6. Treat symbolic repeat units, R groups, salts, and abbreviations as explicit
   labels. Never infer a chain length or expand an abbreviation silently.

The Agent should produce a short per-crop interpretation before drawing:
structure identity/graph, uncertain bonds or labels, and the chosen SMILES or
explicit graph representation. ChemKit then renders that representation with
`scripts/chemkit_route_renderer.py`. If a bond, attachment point, or stereo
mark is unclear, ask for a tighter crop or confirmation instead of guessing.

See `references/agent-screenshot-strategy.md` for the detailed checklist and
recommended prompt format.

## Workflow

1. For text/SMILES input, parse the chemistry into explicit structures before
   drawing.
2. For screenshot/PDF/figure input, apply the screenshot strategy above. The
   Agent interprets each isolated crop and records an explicit structure
   representation plus uncertainties.
3. Use RDKit for molecule parsing, sanitization, 2D coordinates, and SVG drawing.
4. If the user asks to highlight, color, or emphasize a structure or group,
   resolve the request with `resolve_emphasis()` or
   `resolve_route_emphasis()` before rendering; include the resolved report in
   the JSON manifest.
5. Use `scripts/chemkit_route_renderer.py` for new route-level
   placement whenever possible; do not start new route scripts by
   copying legacy one-off drawing code.
6. Render SVG first for inspection. Export PDF/PNG only after the SVG layout is acceptable.
7. Validate:
   - Every molecule parses.
   - Every uncertain attachment, abbreviation, repeat unit, and stereo mark
     is either confirmed or visibly marked for review.
   - Any unsanitized RDKit molecule is marked for correction and cannot be
     treated as final.
   - Structure scales are visually consistent.
   - Arrow and condition text are centered and do not overlap structures.
   - Atom labels are bold and larger than or comparable to condition text.
   - Emphasis targets resolve to the intended atoms/bonds, use an accessible
     accent color, and do not obscure labels or stereochemistry.
   - The output resembles the user's ChemDraw examples.

## References

- Read `references/rdkit-acs-style.md` before setting RDKit drawing parameters.
- Read `references/reaction-layout-rules.md` before placing structures, arrows, plus signs, condition text, or notes.
- Read `references/agent-screenshot-strategy.md` before using screenshots,
  paper figures, PDFs, or DOI figures as chemical sources.
- Read `references/emphasis-rules.md` when a user asks to color, bold, or
  otherwise emphasize a structure, functional group, or route intermediate.
