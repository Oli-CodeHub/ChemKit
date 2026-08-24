# Emphasis rules

ChemKit emphasis is a visual annotation layer. It must never alter the
underlying SMILES, atom connectivity, stereochemistry, or route layout.

## Agent-facing request format

Users should be able to say:

```text
把第 2 步产物中的硫代酯键用红色加粗。
把 3w 和 2 中的同一官能团都突出显示。
把这个分子的吲哚环改成蓝色。
```

The Agent converts the request into a structured list and resolves it before
drawing:

```json
{
  "molecules": ["2"],
  "selector": {"type": "functional_group", "value": "thioester"},
  "mode": "bond",
  "color": "#C62828",
  "bond_width_multiplier": 2.0
}
```

Use `molecule` or `molecules` to scope a route request. Supported selectors
include `functional_group`, `smarts`, and explicit `atom_indices` or
`bond_indices`. Built-in semantic groups are defined in
`scripts/chemkit_emphasis.py` and can be extended without changing the
renderer.

## Matching and ambiguity

Resolve semantic selectors to explicit atom and bond indices before calling
the renderer. If a selector matches multiple locations, require a `match`
index or use `match: "all"`; do not silently select the first match. Return a
short confirmation to the user before a publication-oriented render:

```text
目标：分子 2 的硫代酯
匹配：1 处，键索引 [7, 8]
样式：红色，键宽 2.0×
```

Record the original request and the resolved indices in the JSON manifest so
the output can be reproduced and audited.

## Visual defaults

- `bond`: recolor and thicken the original selected bond paths in place; never
  draw a second colored line over the original black bond;
- every visible atom glyph at either endpoint of a selected bond inherits the
  bond color automatically, including `O`, `N`, halogens, and condensed
  display labels; never allow a colored bond to terminate at a black endpoint;
- `atom`: color the selected atom highlights;
- `group`: color both selected atoms and internal bonds;
- default accent: `#C62828`;
- default bond-width multiplier: `2.0`;
- preserve all non-selected bonds, labels, arrows, and conditions in the
  normal ChemKit black-and-white style;
- do not add a legend unless the user requests one.

Emphasis is optional and disabled by default. If the target is unclear from a
screenshot, request a tighter crop or a user confirmation rather than
guessing.
