# ChemKit 1.0

ChemKit 1.0 is a Codex skill and RDKit-based drawing toolkit for generating
publication-style chemical reaction schemes with ChemDraw/ACS-like visual
proportions.

The project started from a practical pain point: ChemDraw is excellent,
but manual scheme layout is slow; RDKit is programmable, but raw output
often does not look like a polished ACS/JACS figure. ChemKit turns repeated
chemical drawing preferences into reusable rendering rules.

## What It Does

- Draws RDKit-generated SVG/PNG reaction schemes.
- Uses ChemDraw/ACS-like compact styling.
- Keeps molecule scale, bond width, atom-label size, and captions consistent.
- Centers reaction conditions on arrows.
- Extends arrows according to condition text length.
- Preserves shared scaffold orientation across starting materials and products.
- Strengthens dashed wedge stereochemical bonds so they remain readable in PNG exports.
- Provides examples and scripts for reusable scheme generation.

## Version 1.0

ChemKit 1.0 is the first stable release of the reusable route-rendering
workflow. It is designed for:

- publication-style reaction schemes generated from RDKit structures;
- ChemDraw-like route layout with fixed effective bond scale;
- consistent atom labels, condition text, structure labels, arrows, and route spacing;
- screenshot-derived structure redraws with explicit QC and confidence checks;
- reusable SVG/PNG examples and route-generation scripts.

The 1.0 renderer is the default workflow. OCSR/image-recognition experiments
remain documented as optional tooling and are not required for ordinary route
generation.

## Quick Start

Install Python dependencies in an isolated environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Generate an example scheme with the 1.0 renderer:

```bash
python scripts/draw_route_fat_amide_coupling.py
```

Outputs are written to `examples/`.

## Local Web Prototype

ChemKit includes a lightweight local web prototype:

```bash
python server.py
```

Then open:

```text
http://127.0.0.1:8765/
```

The web backend can optionally use an OpenAI-backed parser when
`OPENAI_API_KEY` is set. Without it, ChemKit falls back to a small local
rule parser. The web prototype uses the same ChemKit 1.0 route-rendering
rules.

## Project Layout

```text
SKILL.md                         Codex skill entrypoint
scripts/                         RDKit renderers and example route scripts
references/                      ChemKit drawing rules and accumulated notes
examples/                        Generated SVG/PNG examples
web/                             Lightweight reaction builder prototype
social/                          Xiaohongshu promo-card generator and assets
agents/                          Experimental agent metadata
```

## Release

The current release is **ChemKit 1.0**. See [CHANGELOG.md](CHANGELOG.md) for
the release summary and migration notes from the original prototype.

## License

ChemKit is shared for learning, personal research, and non-commercial
academic use. Commercial redistribution, resale, SaaS packaging, training
course packaging, or removal of attribution requires prior written permission.

See `LICENSE` for details.

## Attribution

If ChemKit helps your own workflow, please keep attribution to the original
project and author in redistributed materials.
