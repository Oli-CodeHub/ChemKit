# ChemKit

ChemKit is a Codex skill and RDKit-based drawing toolkit for generating
publication-style chemical reaction schemes.

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

## Current Status

ChemKit is an early personal research workflow, not a polished package.
It is useful as:

- a Codex skill for chemistry drawing tasks;
- a reference implementation for RDKit route layout rules;
- a starting point for natural-language-to-reaction drawing workflows;
- a small showcase of how agent workflows can encode domain-specific taste.

OCSR/image recognition experiments are documented, but not enabled as the
default public workflow.

## Quick Start

Install Python dependencies in an isolated environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Generate an example scheme:

```bash
python scripts/draw_route_citronellal_terminal_methyl_oxidation.py
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
rule parser.

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

## License

ChemKit is shared for learning, personal research, and non-commercial
academic use. Commercial redistribution, resale, SaaS packaging, training
course packaging, or removal of attribution requires prior written permission.

See `LICENSE` for details.

## Attribution

If ChemKit helps your own workflow, please keep attribution to the original
project and author in redistributed materials.

