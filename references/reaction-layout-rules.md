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
- Place plus signs at the midpoint of the **visible gap** between reactant
  bboxes, not at the midpoint of their center coordinates. Wider molecules
  otherwise make a mathematically centered plus look visually off-center.
- Leave clear whitespace between structures, plus signs, arrow, and
  condition text.

## Route Semantics and Wrapped Rows

- Before placing anything, write a route manifest containing nodes, directed
  edges, condition ownership, mixture markers, and row breaks. Do not infer an
  edge from the eventual x/y alignment alone.
- A bracketed condition spanning two structures belongs to the directed edge
  indicated by the bracket arrow. For example, a DMP bracket spanning II-2 and
  II-3 means II-2 → II-3; it is not a free-standing side arrow from II-3.
- A new row that begins with an arrow at the left is a horizontal continuation
  of the previous route. Keep the chemical edge in the manifest and draw the
  continuation arrow left-to-right; do not substitute a vertical arrow simply
  because the previous product is above the next intermediate.
- Keep mixture symbols separate from reaction edges. A `+` between II-2 and
  II-3 can describe the output mixture of the preceding step while a later
  bracket operation selectively converts one member of that mixture.

## Stereochemistry from Screenshots

- Treat each solid wedge and hashed wedge as an explicit observation. Build an
  atom/bond mapping table before writing a chiral SMILES. `@` and `@@` depend on
  SMILES neighbour traversal order and cannot be selected from the apparent
  screen direction alone.
- Determine final 2D coordinates before generating wedge/dash bond directions.
  If coordinates are rotated or mirrored, call RDKit's wedge assignment again
  and inspect every stereo center. Never post-process a finished depiction by
  mirroring it without re-wedging.
- Validate both connectivity and the complete wedge/dash pattern in a tight
  crop. For fused rings, one inverted wedge can change the relative
  stereoisomer even when the ring orientation and atom labels look correct.
- If the source draws an explicit short hashed bond to an H label, keep the
  neighboring ring bond ordinary and use a semantic H-stereo overlay. Never
  approximate a direct H wedge by making an arbitrary ring bond dashed.
- If the source resolution does not establish a stereo mark, record the center
  as uncertain and do not call the output publication-ready.

## Conformations and Cage Scaffolds

- Preserve a source-observed chair, boat, or envelope projection with explicit
  2D coordinates. Do not replace a chair pyranose with a flat regular hexagon;
  validate axial/equatorial substituent directions together with wedges.
- Validate named cage scaffolds from their atom graph before selecting a 2D
  projection. A BCP (bicyclo[1.1.1]pentane) contains two bridgeheads and three
  distinct one-carbon bridges, so each of the three bridge carbons bonds to
  both bridgeheads. It has no direct bridgehead bond and no terminal methyl.
- For the conventional BCP view used in compact paper schemes, place one bridge
  carbon above the bridgeheads and two below, then verify all six bridge bonds.
  Reuse the exact cage coordinates in reactant and product.

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
- For a coupling product containing two recognizable reactant fragments,
  one MCS match is insufficient. Preserve both sides: copy the first
  reactant fragment coordinates, replace its leaving-group position with
  the new linking atom, translate the second reactant fragment so its
  reacting atom occupies that position, and then form the new bond.
  This should make the product look like the two displayed reactants were
  joined directly, without rotating either conserved fragment.

## Effective Bond Scale

- Placement boxes are layout hints, not molecule canvases. Never draw a
  wider product into a larger or smaller per-molecule box and let RDKit
  fit it independently.
- Draw every molecule on the same large temporary canvas at the same
  fixed bond length, crop its actual SVG bbox, and translate the cropped
  group into the route.
- Measure the final SVG, not only RDKit conformer coordinates. Effective
  unlabelled bond lengths across a route should agree within about 1-2%.
- If a small ring still looks undersized after scale equality is proven,
  test a restrained 1.05-1.08 ring template expansion. Do not apply this
  correction before eliminating whole-molecule auto-scaling.

## Structure Labels (S1 / S2 / S3)

- All structure labels in a route **share a single horizontal baseline**,
  anchored to the bottom of the **tallest** structure plus a fixed
  baseline padding. With 25 px compact-profile labels, use about `+35 px`
  from the lowest molecule bbox edge to the label baseline. Do not place
  each label relative to its own
  structure's bottom edge — short structures will get labels that float
  above short ones, breaking the row.
- Label x = horizontal center of the structure (the structure's bbox
  center, not the raw canvas center).
- Label `text-anchor` = `middle`.

## Arrow

- Use a small reaction arrow with visual weight close to, but not heavier
  than, the structures. In the compact profile, use a `2.1 px` shaft with
  an `18 × 11 px` arrowhead alongside `2.05 px` bonds. Set SVG marker units
  to `userSpaceOnUse`; otherwise the default stroke-width units multiply the
  nominal arrowhead dimensions when the shaft is thickened.
- Arrowhead should remain compact; it should not dominate the scheme.
- Put the arrow horizontally on the reaction baseline.
- Center the arrow shaft in the visible horizontal gap between the last
  reactant bbox and product bbox. The whitespace from reactant to arrow
  start and from arrow end to product should be equal, subject to the
  arrowhead's small optical correction.
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
- Position a multi-line block from the line nearest the arrow, not from
  the block's first/top line. Adding a reagent line should extend the
  block upward without moving its nearest line away from the arrow.
- For 14 px condition text, use SVG text baselines as the deterministic
  geometry: the last line above the arrow sits about 18 px above the
  arrow baseline, with a 16 px line step. The first line below sits
  about 32 px below the arrow baseline; its visible glyphs then begin
  roughly 18-20 px below the line.
- For the compact ChemDraw-like profile, treat conditions and arrow as
  one visual block. Use `condition_labels_for_arrow()` so the nearest
  upper line stays anchored 20 px above the arrow baseline. Do not use a
  fixed y-coordinate for the block's top line; that is what makes
  two-line conditions appear too high. Keep the arrow wider than the
  longest condition line by at least 45-70 px total.

## Font Sizes (user-confirmed)

The current user-confirmed default is: **atom labels should be visibly
larger and bolder than the route text**. The earlier single 14 px tier
was superseded after the perillyl acetate test because heteroatom labels
looked too small and thin.

| Element             | Size   | Weight                          |
|---------------------|--------|---------------------------------|
| Atom label (RDKit)  | 26 px compact profile | Arial Bold glyph, fixed min/max size |
| Condition text      | 25 px compact profile | Arial Bold, no artificial outline |
| Structure label     | 25 px compact profile | Arial Bold, no artificial outline |
| Dashed wedge segment | ≥70% of normal bond width | strengthened after RDKit SVG output |

For very dense overview routes, smaller text and bond strokes may be
used only as a deliberate density exception. Do not let RDKit silently
shrink atom labels; pin `fixedFontSize`, `minFontSize`, and
`maxFontSize` to the same value.

## Style Profiles

- `RouteStyle()`: general ACS-like default.
- `chemdraw_compact_style()`: use for single-row paper schemes that
  should resemble hand-spaced ChemDraw screenshots. It uses 26 px Arial
  Bold atom labels, a fixed RDKit bond length around 25.5 px, 2.05 px
  bonds, 25 px condition text, 25 px structure labels, 18% multiple-bond
  spacing, no text outline, and a compact condition block. These sizes are
  calibrated against the approximately 38.25 px effective rendered bond,
  not against the raw `fixedBondLength` value.

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
- Plus signs are centered between the visible edges of adjacent reactants;
  reaction arrows have balanced left/right clearances.
- Route fits in the visible canvas without crowding (sips / Quick Look
  will silently clip if `RIGHT_PAD` is too small — leave ≥ 60 px).
