# ChemKit 1.1

ChemKit 1.1 is a Codex/Agent skill and RDKit-based drawing toolkit for
generating publication-style chemical reaction schemes with ChemDraw/ACS-like
visual proportions. It is designed to be invoked directly by an Agent through
deterministic scripts and a small command-line interface.

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

## Version 1.1

ChemKit 1.1 builds on the stable reusable route-rendering workflow. It is
designed for:

- publication-style reaction schemes generated from RDKit structures;
- ChemDraw-like route layout with fixed effective bond scale;
- consistent atom labels, condition text, structure labels, arrows, and route spacing;
- screenshot-derived structure redraws through Agent visual analysis with explicit QC;
- reusable SVG/PNG examples and route-generation scripts.

The 1.1 renderer is the default workflow. Screenshot input is handled by
isolated crops interpreted by the Agent; automatic OCSR engines are not part
of the skill's default path.

## One-command installation

From a downloaded or cloned ChemKit directory:

```bash
# macOS/Linux
./install.sh

# Windows PowerShell
./install.ps1
```

The installer places the skill in the active Agent skills directory, creates
an isolated `.venv`, and installs the ChemKit runtime dependencies. It supports
`--target`/`-Target` for a custom skills directory and honors
`CODEX_HOME`/`CODEX_SKILLS_DIR`. If the host has no Python (or `uv`), the
installer stops with a clear bootstrap message; no installer can create an
Agent runtime without at least one executable bootstrap tool.

For an existing Python installation, the equivalent command is:

```bash
python scripts/install_chemkit.py
```

## Quick Start

Check the isolated environment:

```bash
./bin/chemkit check
```

Generate an example scheme with the 1.1 renderer:

```bash
./bin/chemkit run scripts/draw_route_fat_amide_coupling.py
```

Outputs are written to `examples/`.

For screenshot-to-structure redraws, send individually cropped structures to
the Agent and then run the ChemKit route script. The recommended crop rules
are documented in `references/agent-screenshot-strategy.md`.

```bash
./bin/chemkit run scripts/draw_agent_analyzed_structure_grid.py
```

The final SVG contains ChemKit-rendered structures rather than the source
pixels. Dense or ambiguous crops still require human confirmation before
publication. The former OCSR scripts remain only as experimental diagnostics.

## CLI: what it is and why it exists

CLI means **command-line interface**: a small, deterministic command that an
Agent can call without opening a GUI or depending on a particular browser.
ChemKit's CLI is intentionally narrow:

```bash
./bin/chemkit check
./bin/chemkit run scripts/draw_route_fat_amide_coupling.py
./bin/chemkit preview examples/20260819-fat-amide-coupling.svg
```

It is useful because it gives Agent workflows a stable entry point for
environment checks, route-script execution, and opening generated files. It
does not replace the ChemKit skill instructions; it removes the need for an
Agent to guess Python paths or the user's checkout directory. The CLI is
therefore recommended, but direct calls to the scripts remain supported.

`preview` uses the operating system's default application. On macOS it can
open Safari, Chrome, Firefox, or another installed browser; on Windows and
Linux it uses the registered default browser/viewer. Chrome is not a
requirement. Headless PNG conversion is optional and only used when a
compatible browser executable is available.

## Emphasis layer

An Agent can turn requests such as “highlight the thioester in step 2 in red”
into semantic selectors with `scripts/chemkit_emphasis.py`. The resolver maps
functional-group or SMARTS selectors to explicit atom/bond indices, rejects
ambiguous matches unless the user chooses one, and passes the result to the
route renderer without changing the chemistry. See
`scripts/draw_emphasis_demo.py` for a complete route example.

## Project Layout

```text
SKILL.md                         Codex skill entrypoint
scripts/                         RDKit renderers, emphasis resolver, CLI, route, and promo scripts
references/                      ChemKit drawing rules and accumulated notes
examples/                        Generated SVG/PNG examples
bin/                              Installed CLI wrappers
install.sh / install.ps1         Cross-platform skill installers
agents/                          Experimental agent metadata
```

## Release

The current release is **ChemKit 1.1**. See [CHANGELOG.md](CHANGELOG.md) for
the release summary and migration notes from the original prototype.

## License

ChemKit is shared for learning, personal research, and non-commercial
academic use. Commercial redistribution, resale, SaaS packaging, training
course packaging, or removal of attribution requires prior written permission.

See `LICENSE` for details.

## Attribution

If ChemKit helps your own workflow, please keep attribution to the original
project and author in redistributed materials.
