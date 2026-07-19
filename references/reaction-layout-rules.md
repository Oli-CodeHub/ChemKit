# Reaction Layout Rules

Use these rules for RDKit/SVG reaction schemes. Numbers are
user-confirmed defaults from the June 2026 iteration; tweak only with
a reason.

## Structure Placement

- Put all reactants and products on one **visual baseline** (RDKit draws
  each molecule on its own temp canvas; the script then translates them
  to a shared `BASELINE_Y`).
- Keep structure heights comparable; if a structure is unusually tall
  (e.g. a tosylate), do not shrink the others to match — let the canvas
  grow.
- Align visual centers, not raw SVG canvas centers.
- Place plus signs centered between reactants.
- Leave clear whitespace between structures, plus signs, arrow, and
  condition text.

## Matched Backbone Orientation

- In a single reaction step, products should inherit the starting
  material's backbone orientation whenever the core scaffold is
  conserved. The drawing should communicate "same molecule, local
  functional group change" instead of making the reader mentally rotate
  or mirror the product.
- Use the starting material as the reference depiction, find the
  conserved substructure with MCS or atom maps, then call
  `rdDepictor.GenerateDepictionMatching2DStructure(product, reference,
  refPatt=core)` before drawing the product.
- After constrained depiction, verify that matched core atoms have
  identical or near-identical coordinates. For unchanged scaffold
  reactions, max matched-core coordinate delta should be approximately
  zero before route-level translation.
- If MCS can choose the wrong symmetric site, do not rely on automatic
  matching. Use reaction atom maps, manually specified atom indices, or
  a named reaction-site template so the oxidized/substituted position is
  the intended one.
- Preserve stereochemistry and wedge/dash conventions when applying
  constrained depictions. If the reference molecule carries a defined
  stereocenter, the corresponding product stereocenter must remain
  assigned and visually consistent.

## Structure Labels (S1 / S2 / S3)

- All structure labels in a route **share a single horizontal baseline**,
  anchored to the bottom of the **tallest** structure plus a fixed
  padding (e.g. `+22 px`). Do not place each label relative to its own
  structure's bottom edge — short structures will get labels that float
  above short ones, breaking the row.
- Label x = horizontal center of the structure (the structure's bbox
  center, not the raw canvas center).
- Label `text-anchor` = `middle`.

## Arrow

- Use a small reaction arrow, visually lighter than the structures.
- Arrow line width should be around `1.2-1.5 px` when bond line width is
  around `1.6-1.8 px`.
- Arrowhead should be modest; it should not dominate the scheme.
- Put the arrow horizontally on the reaction baseline.
- Size the arrow from the reaction condition text, not as a fixed
  constant. The arrow should extend beyond the widest condition line on
  both the left and right sides.
- As a starting rule, estimate the widest condition line, then set
  arrow length to at least that width plus 35-50 px of total overhang.

## Condition Text

- Conditions are centered on the arrow center.
- Reagent/catalyst/base lines go above the arrow.
- Solvent/temperature/time lines go below the arrow.
- Use `text-anchor="middle"` so multiline condition text is
  geometrically centered.
- Keep condition text close to the arrow. The nearest condition line
  should feel attached to the arrow, not floating far away.
- A good starting geometry is: top condition block second line about
  12-18 px above the arrow; bottom condition block first line about
  18-24 px below the arrow.
- For the compact ChemDraw-like profile, treat conditions and arrow as
  one visual block: top line about 20-26 px above the arrow baseline,
  bottom line about 18-24 px below it, and arrow length wider than the
  longest condition line by at least 45-70 px total.

## Font Sizes (user-confirmed)

The current user-confirmed default is: **atom labels should be visibly
larger and bolder than the route text**. The earlier single 14 px tier
was superseded after the perillyl acetate test because heteroatom labels
looked too small and thin.

| Element             | Size   | Weight                          |
|---------------------|--------|---------------------------------|
| Atom label (RDKit)  | 16 px default; 18 px for sparse/simple routes | Arial Black glyph, fixed min/max size |
| Condition text      | 14 px  | Arial Black + 0.35 px stroke    |
| Structure label     | 14 px  | Arial Black + 0.35 px stroke    |
| Dashed wedge segment | ≥70% of normal bond width | strengthened after RDKit SVG output |

For very dense overview routes, smaller text and bond strokes may be
used only as a deliberate density exception. Do not let RDKit silently
shrink atom labels; pin `fixedFontSize`, `minFontSize`, and
`maxFontSize` to the same value.

## Style Profiles

- `RouteStyle()`: general ACS-like default.
- `chemdraw_compact_style()`: use for single-row paper schemes that
  should resemble hand-spaced ChemDraw screenshots. It uses larger
  atom labels, a fixed RDKit bond length around 20 px, tighter molecule
  padding, thinner SVG text stroke, and a compact condition block.

## Notes

- Notes such as `Both are commercially available` should sit under the
  reactants, not under the whole route.
- Use bold text; italic only if explicitly requested or matching a
  source.

## QA Checklist

- No structure overlaps arrow or conditions.
- Left, middle, and right structures have comparable bond lengths.
- Product is not visually smaller than starting material.
- Arrow and condition text form a centered unit.
- All structure labels (S1/S2/S3/...) sit on the same horizontal line.
- Route fits in the visible canvas without crowding (sips / Quick Look
  will silently clip if `RIGHT_PAD` is too small — leave ≥ 60 px).
