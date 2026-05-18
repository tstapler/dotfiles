#!/usr/bin/env python3
"""
Layer 1 compliance checker for FreeCAD kitchen floor plan drawings.
Parses SVG or DXF geometry and checks IRC/NKBA kitchen requirements.
No Claude vision -- all measurements are programmatic and authoritative.
"""

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional


RULES = {
    "island_to_counter_clearance_primary": {"min_in": 42, "label": "Island-to-counter aisle (primary)", "ref": "NKBA G12"},
    "island_to_range_clearance": {"min_in": 48, "label": "Island-to-range aisle", "ref": "NKBA G12"},
    "work_triangle_max_ft": {"max_ft": 26, "label": "Work triangle perimeter", "ref": "NKBA G4"},
    "refrigerator_landing_handle_side": {"min_in": 15, "label": "Refrigerator landing (handle side)", "ref": "NKBA G8"},
    "range_landing_each_side": {"min_in": 12, "label": "Range landing (each side)", "ref": "NKBA G9"},
    "sink_landing_primary": {"min_in": 24, "label": "Sink landing (primary side)", "ref": "NKBA G7"},
    "sink_landing_secondary": {"min_in": 18, "label": "Sink landing (secondary side)", "ref": "NKBA G7"},
}


def extract_svg_labels(svg_path: Path) -> list:
    ns = "{http://www.w3.org/2000/svg}"
    try:
        tree = ET.parse(svg_path)
        return [
            el.text.strip()
            for el in tree.iter(f"{ns}text")
            if el.text and el.text.strip()
        ]
    except Exception as e:
        return [f"ERROR extracting SVG labels: {e}"]


def parse_dimension_inches(text: str) -> Optional[float]:
    text = text.strip()
    # Normalize smart quotes to ASCII
    text = text.replace('‘', "'").replace('’', "'")
    text = text.replace('“', '"').replace('”', '"')

    # Feet-inches: 3'-6" or 3'6"
    m = re.match(r"(\d+)'[\-\s]?(\d+)\"?$", text)
    if m:
        return int(m.group(1)) * 12 + int(m.group(2))

    # Feet only: 3' or 3.5'
    m = re.match(r"([\d.]+)'$", text)
    if m:
        return float(m.group(1)) * 12

    # Inches only: 42" or 42
    m = re.match(r"([\d.]+)\"?$", text)
    if m:
        return float(m.group(1))

    return None


def check_svg_labels_against_rules(svg_path: Path) -> dict:
    labels = extract_svg_labels(svg_path)
    numeric = [(label, parse_dimension_inches(label)) for label in labels]
    numeric = [(lbl, val) for lbl, val in numeric if val is not None]

    aisle_candidates = [
        {"label": lbl, "value_in": val, "result": "CANNOT_AUTO_ASSIGN",
         "note": "In aisle clearance range. Manual rule assignment required."}
        for lbl, val in numeric if 30 <= val <= 72
    ]

    return {
        "method": "svg_label_extraction",
        "all_labels": labels,
        "numeric_labels": [{"label": lbl, "value_in": val} for lbl, val in numeric],
        "aisle_clearance_candidates": aisle_candidates,
        "warnings": [
            "SVG label extraction cannot reliably map labels to specific compliance rules.",
            "Use DXF geometry extraction for authoritative compliance.",
            "All CANNOT_AUTO_ASSIGN items require human verification."
        ],
        "overall": "PARTIAL"
    }


def check_dxf(dxf_path: Path) -> dict:
    try:
        import ezdxf
    except ImportError:
        return {
            "method": "dxf_geometry",
            "error": "ezdxf not installed. Run: ~/.claude/skills/pdf-proof/.venv/bin/pip install ezdxf",
            "checks": [],
            "overall": "ERROR"
        }

    try:
        doc = ezdxf.readfile(str(dxf_path))
        msp = doc.modelspace()
    except Exception as e:
        return {"method": "dxf_geometry", "error": str(e), "checks": [], "overall": "ERROR"}

    entity_types = {}
    layers = set()
    for entity in msp:
        t = entity.dxftype()
        entity_types[t] = entity_types.get(t, 0) + 1
        try:
            layers.add(entity.dxf.layer)
        except Exception:
            pass

    checks = [
        {
            "rule": "dxf_entity_inventory",
            "result": "INFO",
            "entity_types": entity_types,
            "layers": sorted(layers),
            "note": "Add geometry extraction per layer once layer naming is confirmed."
        }
    ]

    return {
        "method": "dxf_geometry",
        "entity_inventory": entity_types,
        "layers_found": sorted(layers),
        "checks": checks,
        "overall": "PARTIAL",
        "warnings": [
            "Geometry extraction rules not yet configured for this DXF.",
            "Layer names discovered above -- add extraction logic in check_compliance.py."
        ]
    }


def main():
    parser = argparse.ArgumentParser(description="Layer 1 kitchen compliance checker")
    parser.add_argument("--svg", type=Path)
    parser.add_argument("--dxf", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if not args.svg and not args.dxf:
        print("ERROR: Provide --svg or --dxf", file=sys.stderr)
        sys.exit(1)

    if args.dxf and args.dxf.exists():
        result = check_dxf(args.dxf)
        if args.svg and args.svg.exists():
            result["svg_labels"] = check_svg_labels_against_rules(args.svg)
    elif args.svg and args.svg.exists():
        result = check_svg_labels_against_rules(args.svg)
    else:
        result = {"error": "No valid input file found", "overall": "ERROR"}

    output = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(output)
        print(f"Written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
