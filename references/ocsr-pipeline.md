# OCSR and Reaction Parsing Pipeline

Use this pipeline when the input is a screenshot, paper figure, PDF crop,
DOI figure, or any other image-only source. The goal is not to copy the
source figure's visual layout. The goal is to extract chemical
information, validate it, and redraw it in the user's ChemKit style.

## Tool Choice

| Role | Default tool | Why |
|------|--------------|-----|
| Single molecule OCSR | MolScribe | Image-to-graph model that predicts atoms, bonds, and geometry, which is better aligned with later RDKit validation than image-to-SMILES alone. |
| Whole reaction scheme parsing | ReactionDataExtractor2 | Explicitly targets reaction scheme extraction, including reaction arrows, conditions, diagrams, labels, and whole-scheme recovery. |
| Cross-check / fallback OCSR | DECIMER Image Transformer | Deep-learning image-to-SMILES model; useful as a second opinion when MolScribe confidence is low or output seems chemically suspicious. |
| End-to-end reaction parsing fallback | RxnScribe | Sequence-generation reaction diagram parser; useful when ReactionDataExtractor2 fails or when an end-to-end parse is faster than manual crop orchestration. |

## Default Workflow

1. Treat the source image as an information source, not a visual
   template.
2. Use the current runnable parser stack first. On this Mac, that means
   MolScribe/RxnScribe/DECIMER from `plugins/.venv-ocsr`, with RDKit
   validation and manual crop orchestration when needed.
3. Use ReactionDataExtractor2 for whole-scheme segmentation only after
   its native runtime is confirmed working in a separate environment.
4. Use MolScribe on each molecule crop to produce a graph/SMILES/MOL-like
   representation.
5. Use DECIMER on the same crop when:
   - the structure is complex or stereochemically dense;
   - MolScribe fails to parse cleanly;
   - the MolScribe result looks chemically unlikely;
   - the source image is low resolution, skewed, or noisy.
6. Use RDKit to parse, sanitize, depict, and compare recognized
   structures. Record failures instead of silently repairing chemistry.
7. Apply the OCSR quality gate below. A recognizer graph is not a
   publication structure until it survives chemical validation.
8. Ask the user to confirm any low-confidence structure before drawing
   the final route.
9. Redraw the final route using ChemKit layout and style rules. Do not
   preserve source-image coordinates unless the user explicitly asks for
   a layout replica.

## OCSR Quality Gate

Raw OCSR output is a diagnostic layer, not a final chemical drawing.
Never deliver a publication-style route from raw atom/bond predictions
alone.

Before final drawing, every molecule must satisfy at least one of these
conditions:

- RDKit parses and sanitizes the recognized SMILES/InChI/MOL without
  valence, charge, atom-label, or stereochemistry ambiguity.
- The structure comes from an editable chemical source supplied by the
  user, such as CDXML, MOL, SDF, ChemDraw copy/paste, or a confirmed
  SMILES/InChI.
- The structure has been manually checked against a reliable literature
  source or confirmed by the user.

If all recognized SMILES are `<invalid>`, or if dense natural-product
intermediates have low confidence, stop before final route generation.
Produce only a clearly labeled recognition diagnostic if useful, list
which structures failed, and ask for DOI/high-resolution source/manual
confirmation. Do not hand-draw from the raw graph and call it ChemKit
output.

## Invalid SMILES Fallback

When MolScribe returns `<invalid>` SMILES but still provides atoms and
bonds, the correct fallback is:

1. Convert the recognized atom/bond graph to an RDKit `RWMol`.
2. Map common abbreviations (`Me`, `AcO`, `OAc`, `OBn`, `TMSO`,
   `OTES`, `Bz`, `Ph`, etc.) to pseudoatoms with `_displayLabel`
   instead of trying to expand them by guesswork.
3. Run `UpdatePropertyCache(strict=False)` and then attempt
   `Chem.SanitizeMol`.
4. Always let RDKit compute 2D coordinates and draw the molecule. Do
   not use recognizer pixel coordinates as the final molecule geometry.
5. If sanitization fails, keep the RDKit drawing only as a diagnostic
   candidate, mark the compound for checking, and request a reliable
   structure source before finalizing.

This fallback is useful because RDKit depiction reveals bad recognition
graphs as chemically tangled, unsanitized, or visibly implausible
structures. That failure is signal, not something to hide with manual
SVG cleanup.

## Current Runtime Status

Check the local environment before running OCSR. The `plugins/` runtime
folder used during the June 2026 experiments may not be present in the
current workspace checkout.

- RDKit may be available from system Python and is enough for natural
  language / SMILES-driven route drawing.
- MolScribe, RxnScribe, DECIMER, and ReactionDataExtractor2 require the
  ChemKit plugin/runtime setup. Run `scripts/check_ocsr_plugins.py` and
  inspect `plugins/manifest.json` before assuming they are available.
- If `plugins/` is absent, screenshot recognition is not ready; use
  user-supplied SMILES/InChI/MOL/CDXML, a DOI/source with accessible
  structures, or reinstall the OCSR stack.
- ReactionDataExtractor2 was historically blocked on native macOS
  dependencies: Tesseract/Leptonica, PoTrace/libagg/`pypotrace`,
  detectron2, and model weights.

## Confirmation Triggers

Always ask before final drawing when any of these occur:

- The recognizer returns `<invalid>` SMILES/InChI/MOL.
- MolScribe and DECIMER disagree materially.
- RDKit sanitization fails or changes valence/charge assumptions.
- Stereo centers or wedge/dash bonds are ambiguous.
- A molecule contains abbreviated groups, R groups, polymers, salts, or
  counterions that the OCSR tool expands incorrectly.
- The source is a dense natural-product route where a single wrong
  substituent changes the meaning of the intermediate.
- Text OCR for reagents, catalysts, yields, or step numbers is uncertain.

## Output Records

For reusable learning, save these next to the generated route when
practical:

- original image path or DOI/source note;
- crop images for each molecule;
- raw MolScribe output;
- raw DECIMER output when used;
- RDKit parse/sanitize status;
- summary QC report from `scripts/ocsr_qc_report.py`;
- human correction notes;
- final ChemKit SVG/PNG/CDXML output.

## Reusable Scripts

- `scripts/chemkit_ocsr.py`: convert MolScribe-style atom/bond JSON into
  RDKit candidates, map abbreviations to `_displayLabel` pseudoatoms,
  sanitize molecules, and summarize QC.
- `scripts/chemkit_route_renderer.py`: render route-level SVGs from
  RDKit molecule candidates plus explicit molecule/arrow/text layout
  objects.
- `scripts/ocsr_qc_report.py`: command-line QC report for a prediction
  JSON before investing time in route layout.

## Style Boundary

ChemKit must not generate a pixel-level copy of another published
figure. Keep the chemistry and reaction logic, but redraw with the
user's own style:

- consistent molecule scale;
- ChemKit arrow sizing and condition centering;
- ChemKit font and line defaults;
- fresh spacing and route layout where appropriate;
- no attempt to match another author's exact coordinates, crop, or
  figure composition unless the user asks for a temporary diagnostic
  layout replica.
