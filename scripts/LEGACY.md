# Legacy ChemKit Scripts

These scripts are historical experiments or route-specific prototypes.
They are useful as records of what was tried, but they should not be
used as templates for new ChemKit work.

## Current Standard

New route scripts should use:

- `chemkit_route_renderer.py` for RDKit molecule SVG rendering and route
  placement.
- `chemkit_ocsr.py` for MolScribe-style OCSR graph to RDKit conversion
  and QC.
- `ocsr_qc_report.py` before treating screenshot-derived structures as
  final.

## Legacy / Historical Experiments

The following scripts contain one-off RDKit/SVG settings, manual route
layout logic, or diagnostic tracing code:

- `draw_reaction3_heck_rdkit.py`
- `draw_route_3steps_propargyl.py`
- `draw_route_citronellal_nepetalactone.py`
- `draw_route_pyran_spiro.py`
- `draw_route_taxol_danishefsky_1994.py`
- `draw_route_taxol_danishefsky_1994_full.py`
- `draw_route_taxol_nicolaou_1994.py`
- `draw_taxol_route_from_molscribe.py`
- `draw_taxol_route_from_molscribe_v2.py`
- `draw_taxol_route_from_molscribe_v3_clean.py`
- `draw_taxol_route_from_reference_crops.py`
- `draw_taxol_route_layout.py`

If a legacy route is reused, port it to the current renderer first rather
than copying its local font, bond, arrow, or canvas settings.
