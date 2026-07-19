# RDKit ACS/ChemDraw-Like Style

Use these settings as the user-confirmed defaults (validated against the
user's own ChemDraw ACS1996 examples in the June 2026 iteration). These
are **starting points that have already been visually QA'd**; small
adjustments may still be needed per-route.

## RDKit Drawing Defaults

- Black-and-white atom palette.
- Use **Arial Black** when available via RDKit `MolDrawOptions.fontFile`:
  `/System/Library/Fonts/Supplemental/Arial Black.ttf`. Arial Bold reads
  too thin next to the bold structure label; Arial Black matches
  ChemDraw's perceived weight.
- `bondLineWidth`: start around `1.6`.
- `fixedBondLength`: start around `17`.
- `fixedFontSize`: start around `16`; use `18` for sparse/simple routes
  where atom labels need more visual weight. The user explicitly
  rejected the smaller 11–12 px range — atom labels in route figures
  should be visually as large as or larger than the surrounding
  condition text.
- `minFontSize` / `maxFontSize`: pin to the same value as
  `fixedFontSize` so RDKit does not silently shrink atom labels.
- `multipleBondOffset`: start around `0.16`.
- `padding`: start around `0.02`.
- `additionalAtomLabelPadding`: start around `0.02`.
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
  bond length around 20 px, 18 px atom labels, tighter molecule padding,
  and a lighter SVG text stroke so labels stay bold without becoming
  blocky.

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
elements, not RDKit paths. To make them visually match the bold atom
labels in every renderer (including sips / Quick Look / Preview.app,
which ignore web font weights), apply both:

```css
text {
  font-family: "Arial Black", "Arial Bold", Arial, Helvetica, sans-serif;
  font-weight: 900;
  fill: #000;
  stroke: #000;
  stroke-width: 0.35;
  paint-order: stroke fill;
}
```

The `stroke` + `paint-order` trick fattens the glyph even when the
renderer falls back to a non-black system font.

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
