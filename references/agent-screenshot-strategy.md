# Agent screenshot strategy

ChemKit's image workflow is Agent visual interpretation followed by explicit
RDKit/ChemKit drawing. Automatic image-recognition engines are outside this
skill; the Agent must produce or confirm the explicit structure representation.

## Why individual crops work

A full reaction figure mixes several visual tasks: structure recognition,
arrow/condition detection, caption reading, and layout reconstruction. These
tasks compete for attention and make a recognizer confuse a clipped bond or a
nearby condition with part of a molecule. An isolated crop reduces the task to
connectivity and labels, which the Agent can inspect directly and compare
across related intermediates.

## Crop checklist

Before sending a crop, verify:

- one molecule only;
- all bond endpoints and stereochemical marks are visible;
- all atom labels and chemical abbreviations belonging to the molecule remain;
- no arrow, condition, yield, number, plus sign, watermark, or adjacent
  molecule remains;
- 10–20% white margin surrounds the structure;
- original-resolution PNG (or lossless equivalent), with no JPEG artifacts;
- a very dense structure also has a tighter detail crop, while the full crop
  remains the connectivity authority.

Use route-order names such as `01-start.png`, `02-intermediate.png`, and
`03-product.png`. If a crop contains a variable unit such as `(CH2)n`, leave
the marker visible; do not replace it with an arbitrary number of atoms. In
the ChemKit redraw, represent the linker with real short zigzag single bonds,
identify the exact carbon vertex enclosed by the source notation, put
parentheses around that single carbon only, and place an upright (non-italic)
`n` at the lower-right of the right parenthesis. Do not put parentheses around
the whole linker.

Record the displayed ring conformation as part of the structure transcription.
If a pyranose is shown in a chair, the crop interpretation must include the
chair projection and the axial/equatorial direction of every visible
substituent; a flat hexagon with the same connectivity does not pass visual QA.

Treat condensed labels as source data. `CCl3`, `OBn`, `BnO`, `DPMO`, and
`OCH3` remain one display-label pseudoatom when written that way in the crop.
Do not expand them into explicit bonds or atoms. If a neighboring fragment is
drawn explicitly (for example `Ph-CH2-O`), keep that fragment explicit and
condense only the labels that are condensed in the source.

For reaction schemes, make a route-semantics pass before drawing: record every
directed edge, the condition block attached to it, mixture symbols, and row
breaks. A bracketed condition arrow between two structures takes precedence
over simple vertical alignment. For each stereocenter, record the source
solid/hashed mark against an atom index; do not infer `@`/`@@` from visual
left/right direction alone.

## Recommended Agent handoff

```text
These are isolated structure crops in route order. For each crop:
1. identify the scaffold and every attachment point;
2. transcribe atom labels, abbreviations, charges, and stereo marks;
3. write a SMILES or explicit graph for ChemKit;
4. list anything ambiguous instead of guessing.
After the per-structure check, draw all structures on one ChemKit canvas with
consistent bond scale and the requested orientation.

Use a logical infinite canvas while laying out the route. Once all structures,
arrows, conditions, plus signs, repeat markers, and captions are present,
compute their combined visible bounding box and crop to it with a fixed white
margin. The final crop must translate/viewBox the artwork without changing its
scale; fixed page ratios are optional export constraints, not the default
layout canvas.
```

For efficiency, do not render a full route while its semantics are unresolved.
Finish the node/edge/condition/row-break manifest first, validate local
structure crops, and only then render the full canvas. Keep chemistry parsing,
route layout, and typography as separate passes so a wrong arrow relationship
does not trigger repeated style-only redraws.

## Two-pass validation

The Agent should first return a compact table of interpretations. Then it
should draw the canvas. Compare the canvas against the crops for:

1. ring sizes and heteroatom positions;
2. attachment point and carbonyl direction;
3. variable-chain and abbreviation labels;
4. orientation of shared scaffolds;
5. wedge/dash and charge marks.

After the final 2D orientation is selected, regenerate RDKit wedge/dash bonds
and compare a close-up of each stereocenter. Do not mirror a finished molecule
as a layout shortcut; a reflection can invert apparent relative
stereochemistry unless wedge directions are recomputed and rechecked.

If any item is unclear, request only a tighter crop of that structure and
rerender that entry. Do not rerun a whole-route image recognizer or silently
copy pixels from the reference.

## Handling uncertainty

Use explicit labels for `R`, `Boc`, `Bz`, `OAc`, and similar groups. Treat a
variable methylene chain as a layout-aware repeat unit: record the selected
carbon atom index, draw the surrounding real zigzag, put parentheses around
that carbon only, and add an upright `n` at the lower-right. Keep a JSON record
of the Agent interpretation and any user corrections next to the SVG.
Keep a JSON record of the Agent interpretation and any user corrections next
to the SVG. A structure can be visually redrawn while still being marked
“needs confirmation”; it must not be called publication-ready until the
uncertain connectivity is confirmed.
