#!/usr/bin/env python3
"""Generate a ChemKit QC report from MolScribe-style prediction JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from chemkit_ocsr import candidates_from_predictions, load_predictions, write_qc_report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("predictions", type=Path, help="MolScribe-style predictions JSON")
    parser.add_argument("--output", type=Path, help="QC report JSON path")
    args = parser.parse_args()

    candidates = candidates_from_predictions(load_predictions(args.predictions))
    output = args.output or args.predictions.with_name(args.predictions.stem + "-qc-report.json")
    report = write_qc_report(output, candidates)

    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"unsanitized: {', '.join(report['unsanitized_structures']) or 'none'}")
    print(f"low confidence: {', '.join(report['low_confidence_structures']) or 'none'}")
    print(f"unresolved labels: {json.dumps(report['unresolved_labels'], ensure_ascii=False)}")
    print(output)


if __name__ == "__main__":
    main()
