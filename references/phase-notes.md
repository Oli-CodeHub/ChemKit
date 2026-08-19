# Phase Notes

## 2026-08-19: Fixed-Scale ACS Rendering and Dual-Fragment Couplings

The FAT amide-coupling comparison exposed two reusable failures. First,
RDKit shrank the wider product when molecules were drawn into different
small placement boxes: reactant effective bonds were 36.0 px while the
product was 33.1 px despite identical 1.5-unit coordinates. Second, matching
only the aryl MCS preserved FAT-2a orientation but rotated the conserved
cyclobutane-carbonyl fragment from FAT-1a.

The reusable correction is now:

- draw all molecules on one shared large temporary canvas at fixed scale;
- crop actual SVG content and translate only;
- record effective rendered bond length and keep route variation near 1-2%;
- use the compact ACS profile: Arial Bold, 25.5 px fixed bond length
  (about 38.25 px effective bond), 2.05 px bond width, 26 px atom labels,
  25 px condition text, 25 px structure labels, 18% multiple-bond spacing,
  and 0.03 label padding;
- size typography against the effective rendered bond rather than the raw
  RDKit setting; the compact optical targets are about 0.68 atom-font,
  0.65 condition-font, and 0.65 structure-label per effective bond;
- render arrow markers with `markerUnits="userSpaceOnUse"` so the specified
  arrowhead dimensions remain true pixels when shaft width changes;
- calculate plus signs and reaction arrows from final molecule bboxes:
  plus signs use the midpoint of the visible reactant gap, while arrows use
  symmetric left/right clearances in the reactant-product gap;
- anchor the shared 25 px structure-label baseline 35 px below the lowest
  molecule bbox edge; derive canvas height from that baseline plus padding;
- for couplings, construct the product from both reactant coordinate
  fragments so each conserved scaffold retains its displayed orientation.

## 2026-06-25: RDKit Reaction Scheme Layout

Current goal: use RDKit to produce ACS/ChemDraw-like reaction scheme
SVGs without relying on ChemDraw.

### Visual style — user-confirmed defaults

The user's ChemDraw 2026-06-25 screenshot established a clear set of
preferences. These are now the defaults in `references/rdkit-acs-style.md`
and `references/reaction-layout-rules.md`:

- Atom labels and condition text and structure labels are all the same
  size (14 px). Hierarchy comes from weight + position, not font size.
- Atom label font is **Arial Black**, not Arial Bold. Arial Bold reads
  thin next to the bold condition text.
- `bondLineWidth` 1.6, `fixedBondLength` 17, `fixedFontSize` 14,
  `multipleBondOffset` 0.16.
- All structure labels (S1/S2/S3) share a single horizontal baseline
  anchored to the tallest structure's bottom edge. Do not anchor each
  label to its own structure.
- Subscript digits in chemical formulas (Et₃N, NiCl₂, Et₄NBr) are typed
  as Unicode subscript characters (`\u2082`, `\u2083`, `\u2084`) — both
  inside SMILES and in condition text strings. Do not use `<tspan
  baseline-shift>` or `<tspan dy>` for subscripts.
- Multi-line condition blocks use one independent `<text>` element per
  line. Do not use `<tspan dy>` inside a single `<text>`.
- SVG `<text>` for conditions and labels uses
  `font-family: "Arial Black", "Arial Bold", Arial, Helvetica, sans-serif`,
  `font-weight: 900`, plus a `stroke: #000; stroke-width: 0.35;
  paint-order: stroke fill;` so the bold appearance survives in sips /
  Quick Look / Preview.app, which ignore web font weights.
- R-group placeholders are dummy atoms in SMILES with
  `atom.SetProp("_displayLabel", "R")` set before drawing. Do not try
  to text-replace `*` → `R` in the SVG output — RDKit draws atom labels
  as `<path>` glyphs, not as `<text>`.

### Lessons from earlier iterations

- Do not start from a small fixed molecule canvas. Draw each molecule
  on a large temporary canvas, calculate the actual SVG content
  bounding box, then crop/layout from that bbox.
- Do not flip or rotate structures by default. Orientation transforms
  need explicit chemical/layout reasons.
- Keep all structures at a shared RDKit drawing scale: same fixed bond
  length, atom font size, bond width, multiple-bond offset, and
  palette.
- Do not shrink the product just because it is wider. Let the final
  route canvas grow when needed.
- The reaction arrow should be sized from condition text. It should be
  longer than the widest condition line, with left and right overhang.
- Condition text should be centered on the arrow and closer to it than
  in the early tests.
- Final SVG canvas should be derived from the placed route bbox plus
  padding, not manually guessed up front. sips / Quick Look silently
  clip content outside the viewBox if `RIGHT_PAD` is too small; leave
  ≥ 60 px on the right.

## 2026-06-25: Screenshot Route Replica

Test case: dense Taxol total-synthesis route screenshot with compounds
1-15 and Taxol.

### What worked

- Separate the task into two layers:
  1. route topology/layout replica: rows, columns, arrow directions,
     conditions, yields, labels, and relative density;
  2. molecule-true rendering: exact intermediates from SMILES, InChI,
     CDXML, MOL/SDF, DOI, or a reliable source.
- Screenshot-only input is acceptable for the layout layer, but not for
  faithful complex natural-product intermediates. Do not claim exact
  stereochemistry or protecting-group placement from a low-resolution
  screenshot alone.
- For layout replicas, use small placeholder molecule glyphs while the
  reaction canvas, arrow directions, condition blocks, yields, and
  numbering are being tuned.
- Dense literature overview routes often need a lighter text stack than
  the single-route ACS defaults: Arial/Helvetica bold at about 10 px and
  bond strokes near 1.1 px can better match the original page density
  than the 14 px Arial Black single-route default.
- Browser rendering via Playwright is the most reliable quick visual QA
  for SVG route layouts. `sips` may render SVGs with black backgrounds or
  severe clipping, and Quick Look thumbnails can introduce square-canvas
  artifacts.

### Current artifact

- Script: `scripts/draw_taxol_route_layout.py`
- SVG: `examples/20260625-taxol-route-layout-replica.svg`
- Browser preview: `examples/20260625-taxol-route-layout-replica.browser.png`

### Next improvement

Replace placeholder molecule glyphs with true RDKit or CDXML-derived
structures once the exact structures for intermediates 1-15 and Taxol
are provided or located from a reliable source.

## 2026-06-25: OCSR Tool Selection

User confirmed the direction: use open-source tools to read chemistry
from screenshots, then redraw in ChemKit's own style rather than copying
the source figure's visual composition.

### Selected default stack

- MolScribe: primary single-molecule OCSR.
- ReactionDataExtractor2: primary whole-scheme segmentation and reaction
  parsing.
- DECIMER Image Transformer: second-opinion/fallback OCSR.
- RxnScribe: end-to-end reaction diagram parsing fallback.

### Operating principle

Screenshot figures are chemical information sources, not style
templates. Preserve reaction logic and structures after validation, but
use ChemKit's molecule scale, arrow rules, condition placement, fonts,
line weights, and route spacing.

### Local plugin install

Added a ChemKit-local plugin registry under `plugins/`:

- `plugins/manifest.json`
- `plugins/sources/MolScribe`
- `plugins/sources/reactiondataextractor2`
- `plugins/sources/DECIMER-Image_Transformer`
- `plugins/sources/RxnScribe`
- `scripts/install_ocsr_plugins.sh`
- `scripts/check_ocsr_plugins.py`

GitHub `git clone` was unreliable on the current network, so the
installer defaults to GitHub codeload zip snapshots and keeps
`--prefer-git` as an optional path.

### Python environment status

Historical note from June 2026: an isolated venv was created at
`plugins/.venv-ocsr`. This runtime may not exist in the current
workspace; check before relying on OCSR.

Installed and import-checked:

- DECIMER package 2.8.0 (package installed; model weights not fully
  downloaded because import attempted a 285 MB download at very low
  network speed)
- MolScribe 1.1.1
- RxnScribe 1.0
- RDKit 2025.9.2
- torch 2.8.0
- tensorflow-macos / tensorflow 2.16.2
- transformers, easyocr, pytorch-lightning

Known caveats:

- DECIMER top-level import triggers model-weight download to
  `~/.data/DECIMER-V2`; run this separately when network is stable.
- RxnScribe declares `Pillow==9.5.0`, while DECIMER currently uses
  Pillow 11.3.0. Basic `import rxnscribe` works; if inference fails,
  split DECIMER and RxnScribe into separate venvs rather than downgrading
  the shared environment prematurely.
- ReactionDataExtractor2 is not fully installed yet. It requires native
  dependencies such as Tesseract/Potrace and detectron2, and is better
  handled in a conda/native-dependency track.

### ReactionDataExtractor2 install attempt on macOS arm64

User confirmed GitHub/conda downloads may use the local Clash proxy:

```bash
HTTPS_PROXY=http://127.0.0.1:7897
HTTP_PROXY=http://127.0.0.1:7897
ALL_PROXY=socks5://127.0.0.1:7897
```

Installed ChemKit-local helper runtimes:

- Miniforge: `plugins/tools/miniforge3`
- micromamba: `plugins/tools/micromamba-bin/bin/micromamba`

Observed behavior:

- The official RDE2 `environment.yaml` is old and heavy
  (`python=3.8`, `pytorch-cpu=1.10`, `torchvision=0.11`,
  `tesseract=4.1.1`). It started downloading very large packages and
  was interrupted because it was not a good default path.
- Miniforge's `mamba` stalled on channel/index work and exited with
  code 139 during local environment creation.
- `micromamba` successfully fetched and resolved conda-forge arm64
  indexes, but `potrace` and `libagg` are not direct conda-forge arm64
  package names. A reduced `python + tesseract + tesserocr +
  pkg-config` environment still stalled during the Tesseract transaction
  and was stopped manually after the env directory remained effectively
  empty.
- Direct pip install in `.venv-ocsr` failed for native packages:
  `tesserocr` could not find `leptonica/allheaders.h`; `pypotrace`
  could not find `pkg-config`/libagg.

Current decision:

- Keep RDE2 source in `plugins/sources/reactiondataextractor2`, but do
  not make it the default executable parser on this Mac yet.
- Default practical route for now: MolScribe for molecule crops,
  RxnScribe for reaction-level guesses, DECIMER as a second-opinion
  OCSR when model weights are available, then RDKit validation and
  ChemKit redraw.
- If RDE2 becomes necessary, continue in a separate native environment
  and expect to solve these pieces explicitly: Tesseract + Leptonica,
  PoTrace/libagg + `pypotrace`, detectron2 compatibility, and RDE2 model
  weights.

## 2026-06-26: MolScribe Taxol Route Test

User asked ChemKit to use OCSR instead of only cropping the reference
image. Downloaded the MolScribe checkpoint:

- `plugins/cache/molscribe/swin_base_char_aux_1m.pth`

The HuggingFace Xet path stalled, but `curl -L -C -` through the local
Clash proxy worked as a resumable download.

Tested MolScribe on the 16 cropped structures from the Taxol route
(`1-15` plus Taxol). Results:

- MolScribe ran successfully on CPU.
- All predicted SMILES were `<invalid>`, so none were ready for RDKit
  sanitize/redraw from SMILES.
- Raw atom/bond predictions were still available and can be drawn as a
  ChemKit SVG recognition layer.
- Early/simple structures (1-4, 15) looked more usable; dense
  natural-product intermediates (6-14 and Taxol) had low confidence and
  visible graph/label errors.

Artifacts:

- Raw predictions: `examples/20260626-taxol-molscribe-predictions.json`
- OCSR redraw script: `scripts/draw_taxol_route_from_molscribe.py`
- OCSR SVG: `examples/20260626-taxol-molscribe-redraw.svg`
- OCSR PNG: `examples/20260626-taxol-molscribe-redraw.png`

Rule learned:

- For dense total-synthesis screenshots, do not stop at cleaned crops,
  but also do not treat MolScribe output as final chemistry. A raw
  atom/bond drawing is only a diagnostic recognition layer.
- The 2026-06-26 Taxol MolScribe redraw was not publication-standard:
  every SMILES was `<invalid>`, several complex intermediates had low
  confidence, atom labels and abbreviations were misplaced, and the
  drawing bypassed RDKit sanitization. This must not be presented as a
  final ChemKit route.
- Final route generation requires validated molecules: RDKit-clean
  SMILES/InChI/MOL, editable CDXML/MOL/SDF, a reliable literature source,
  or explicit user confirmation. If this gate fails, ask for DOI,
  high-resolution source, or manual confirmation instead of drawing a
  polished but chemically unreliable figure.

Follow-up correction:

- The user clarified the intended OCSR workflow: use image recognition
  to recover chemical structures, then redraw the recognized structures
  with RDKit. Do not draw final molecule geometry by manually tracing
  recognizer atom coordinates in SVG.
- If MolScribe returns no SMILES/MOL but does return raw atoms/bonds,
  convert the graph to an RDKit `RWMol`, use pseudoatoms/display labels
  for abbreviations, run RDKit sanitization as a quality check, and let
  RDKit generate the depiction. This produces a true RDKit diagnostic
  redraw and exposes bad recognitions as chemically tangled or
  unsanitized structures.
- In the Taxol test, RDKit could draw all 16 raw graphs, but compounds
  7 and 9 failed sanitization with explicit-valence errors. They should
  be marked for manual correction before any final route is generated.

### Practical workflow from this test

1. For a screenshot route, first extract crops and run OCSR.
2. Prefer valid SMILES/MOL. If missing, convert raw atoms/bonds to RDKit
   `RWMol` and redraw with RDKit.
3. Use RDKit sanitization as the chemical quality gate, not just visual
   neatness.
4. Place RDKit-rendered molecules with ChemKit route layout rules:
   consistent scale, compact arrows, centered condition text, and no
   overlap.
5. Treat unsanitized or low-confidence structures as correction tasks.
   They cannot appear in a final publication-style route without a
   reliable source or user confirmation.

### Next action items

- Done: built reusable OCSR conversion module
  `scripts/chemkit_ocsr.py`. It converts MolScribe atom/bond JSON into
  RDKit `RWMol` candidates, maps common abbreviation labels, runs
  sanitization, records skipped bonds, and summarizes QC.
- Done: built reusable route renderer
  `scripts/chemkit_route_renderer.py`. It consumes RDKit molecule
  candidates plus route-level `MolPlace`/`Arrow`/`Label` layout objects,
  keeping molecule depiction separate from reaction layout.
- Done: improved abbreviation handling for natural-product schemes:
  `Me`, `AcO`, `OAc`, `OBn`, `OBz`, `TMSO`, `TESO`, `OTES`, `Bz`,
  `Ph`, `OMs`, `CHO`, `H`, and related OCSR variants. The Taxol test
  unresolved-label count went from 6 to 0.
- Done: added automated QC command `scripts/ocsr_qc_report.py`. It
  reports valid/invalid SMILES count, sanitized/unsanitized molecules,
  low-confidence structures, unresolved labels, skipped bonds, and
  per-molecule details.
- Done: refactored `scripts/draw_taxol_route_from_molscribe_rdkit.py`
  to use the reusable modules and regenerate:
  `examples/20260626-taxol-route-rdkit-from-ocsr-diagnostic.svg`,
  `.png`, and `-report.json`.
- Blocked by external source: the probable source is JACS 2021,
  DOI `10.1021/jacs.1c09637` (`Asymmetric Total Synthesis of Taxol`).
  The ACS supplementary PDF URL returned HTTP 403 / Cloudflare challenge
  in this environment, and the ACS China mirror timed out. Compounds 7
  and 9 remain unsanitized and need SI/CDXML/MOL/SDF, a higher
  resolution crop, or manual confirmation before final route generation.
