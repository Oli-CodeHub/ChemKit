# RDKit ACS/ChemDraw-Like Style

Use these settings as the user-confirmed defaults (validated against the
user's own ChemDraw ACS1996 examples in the June 2026 iteration). These
are **starting points that have already been visually QA'd**; small
adjustments may still be needed per-route.

## RDKit Drawing Defaults

- Black-and-white atom palette.
- Use **Arial Bold** for the compact ChemDraw/ACS profile via RDKit
  `MolDrawOptions.fontFile`:
  `/System/Library/Fonts/Supplemental/Arial Bold.ttf`.
- `bondLineWidth`: start around `2.05`.
- `fixedBondLength`: start around `25.5`.
- `fixedFontSize`: start around `26`.
- `minFontSize` / `maxFontSize`: pin to the same value as
  `fixedFontSize` so RDKit does not silently shrink atom labels.
- `multipleBondOffset`: start around `0.18`.
- `padding`: start around `0.01`.
- `additionalAtomLabelPadding`: start around `0.03`. Check the visible
  terminal-bond length after rendering; bonds leading to `CN`, `NH₂`,
  `OH`, and similar labels should normally retain about 80-90% of an
  unlabelled ring bond's visible length.
- `singleColourWedgeBonds`: `True`.
- `scaleBondWidth`: `False` (so line widths stay readable when the canvas is scaled).
- RDKit dashed wedge bonds are emitted as multiple short line segments
  at about half the normal bond width. For ChemKit paper schemes,
  post-process dashed wedge segments so they are no thinner than about
  70% of the normal bond width; otherwise stereochemical bonds look too
  pale next to bold atom labels and 1.6 px bonds.
- Current reusable renderer defaults live in
  `scripts/chemkit_route_renderer.py`. New route scripts should use
  `RouteStyle` there rather than reimplementing RDKit drawing settings.
- For screenshot-like compact ChemDraw schemes, use
  `chemdraw_compact_style()` as the starting profile. It uses fixed
  bond length around 25.5 px, 26 px Arial Bold atom labels, 2.05 px bonds,
  25 px condition text, 25 px structure labels, 18% multiple-bond spacing,
  and no artificial text outline.

## Fixed Effective Scale

`fixedBondLength` is not sufficient when each molecule is drawn inside a
different small canvas: RDKit may shrink a wider product to fit. Draw all
molecules on the same large temporary canvas, compute the actual path/glyph
bbox, and place the cropped content without scaling. Use
`draw_mol_svg_at_fixed_scale()` for reusable route work.

Record or inspect `data-effective-bond-length` in the final SVG. Across one
route, unlabelled bond lengths should agree within about 1-2%. Do not compare
only coordinate-space bond lengths; the rendered SVG is the quality gate.

Typography is also calibrated against this **effective** bond length. RDKit's
usual 1.5-coordinate bond means `fixedBondLength=25.5` renders near 38.25 px;
the font sizes are not multiplied by 1.5. For a ChemDraw-like compact route,
start near these optical ratios: atom font/effective bond `0.68`, condition
font/effective bond `0.65`, structure label/effective bond `0.65`, and bond
stroke/effective bond `0.054`. This prevents structures from looking correct
while every text tier remains undersized.

Only consider a 1.05-1.08 visual expansion for three- or four-membered rings
after fixed-scale rendering has been verified. Do not use ring compensation
to hide whole-molecule auto-scaling.

When a reaction-specific ring template is used, validate its geometry as well
as its bond lengths. A cyclobutane template should have four equal sides and
approximately 90° internal angles; an equal-sided 60°/120° rhombus is not an
acceptable substitute. Reuse the exact same ring coordinates in reactant and
product when that ring is conserved.

## Atom Label Subscripts

RDKit draws atom labels as glyph paths, not as `<text>`, so Unicode
subscript characters (`\u2080` through `\u2089`) are **already rendered
correctly** inside molecules. No special handling needed there.

When the same formula appears in a **condition** line (`Et\u2083N`,
`NiCl\u2082(dppe)`), use the Unicode subscript character directly in the
string, **not** a `<tspan baseline-shift="sub">` workaround. Quick Look,
Preview.app, and `sips` all render Unicode subscripts correctly; they do
**not** honour `<tspan dy>` or `baseline-shift`. This single rule is what
keeps sips/Quick Look previews readable.

## R Groups

For a generic substituent placeholder, use a dummy atom in SMILES and
override its display label before drawing:

```python
mol = Chem.MolFromSmiles("[*]C(=C)CO")
for atom in mol.GetAtoms():
    if atom.GetAtomicNum() == 0 and atom.GetSymbol() == "*":
        atom.SetProp("_displayLabel", "R")
```

The atom will draw as `R` instead of `*`. Do not try to post-process the
SVG to replace `*` with `R` — RDKit renders atom labels as `<path>` glyph
outlines, not as `<text>`, so a regex replacement never matches.

## SVG `<text>` for Conditions and Labels

Conditions and structure labels (S1/S2/S3) are written as SVG `<text>`
elements, not RDKit paths. The compact profile uses:

```css
text {
  font-family: "Arial Bold", Arial, Helvetica, sans-serif;
  font-weight: 700;
  fill: #000;
  stroke-width: 0;
}
```

Do not add an outline merely to compensate for a renderer fallback; it
makes route text blockier than ChemDraw atom labels.

## Multi-line Condition Blocks

Do **not** use a single `<text>` with multiple `<tspan dy="14">` children.
`sips` and Quick Look ignore the `dy` and print all lines on one row.

Instead, emit one independent `<text>` element per line:

```python
for idx, line in enumerate(lines):
    yy = y + idx * line_step
    parts.append(f'<text class="cond" x="{x}" y="{yy}" text-anchor="middle">{line}</text>')
```

Browser-grade renderers handle either form; this form is the one that
also works in sips/Quick Look.

## Important Limitation

RDKit's depiction engine is not ChemDraw's depiction engine. Matching
ChemDraw requires route-level layout and sometimes molecule orientation
transforms. Parameter tuning alone is not enough.

## Scale Rule

All structures in a reaction scheme must be rendered at a consistent bond
length and atom-label size. Do not scale a product smaller just because
it has more atoms. If a molecule is too wide, increase horizontal
spacing or canvas width before shrinking the structure.

## Orientation Rule

RDKit's automatic orientation may not match ChemDraw. If the result is
chemically correct but visually awkward, rotate or flip the molecule
group at the SVG/layout level. Preserve stereochemistry when doing this.
