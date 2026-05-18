#!/usr/bin/env python3
"""
Extract kitchen element positions and clearances from SVG geometry.
Uses colored rect positions (appliances) + known scale to compute clearances.
No Claude vision required -- fully programmatic.
"""

import json, sys, argparse
import xml.etree.ElementTree as ET
from pathlib import Path

# SVG coordinate constants (711 N60th kitchen, verified 2026-05-10)
SVG_PER_INCH = 3.306        # SVG units per real inch
KIT_SVG_X0   = 297.1        # interior west wall (SVG x)
KIT_SVG_Y0   = 166.0        # interior north wall (SVG y, top)
KIT_W_IN     = 159.0        # kitchen interior EW width (inches)
KIT_H_IN     = 125.0        # kitchen interior NS depth (inches)

# Appliance fill colors in the SVG (from kitchen_permit_docs.py palette)
COLOR_MAP = {
    "#004488": "sink",
    "#006600": "fridge",
    "#aa3300": "range",
    "#0055aa": "island_or_bar",
    "#445500": "dishwasher",
    "#663300": "cabinet_or_counter",
}

def svg_to_kitchen_inches(svg_x, svg_y):
    """Convert SVG canvas coordinates to kitchen interior inches (origin = NW corner)."""
    x_in = (svg_x - KIT_SVG_X0) / SVG_PER_INCH
    y_in = (svg_y - KIT_SVG_Y0) / SVG_PER_INCH   # y=0 is north wall, positive=south
    return round(x_in, 1), round(y_in, 1)

def parse_elements(svg_path: Path) -> list:
    ns = "{http://www.w3.org/2000/svg}"
    tree = ET.parse(svg_path)
    root = tree.getroot()

    elements = []
    for el in root.iter(f"{ns}rect"):
        try:
            x = float(el.get("x", 0))
            y = float(el.get("y", 0))
            w = float(el.get("width", 0))
            h = float(el.get("height", 0))
            fill = el.get("fill", "").lower()
        except (ValueError, TypeError):
            continue

        if fill not in COLOR_MAP or w < 20 or h < 20:
            continue

        name = COLOR_MAP[fill]
        left_in, top_in = svg_to_kitchen_inches(x, y)
        right_in = left_in + w / SVG_PER_INCH
        bottom_in = top_in + h / SVG_PER_INCH

        elements.append({
            "name": name,
            "fill": fill,
            "left_in":   round(left_in, 1),
            "right_in":  round(right_in, 1),
            "top_in":    round(top_in, 1),     # 0 = north wall
            "bottom_in": round(bottom_in, 1),   # positive = toward south
            "width_in":  round(w / SVG_PER_INCH, 1),
            "depth_in":  round(h / SVG_PER_INCH, 1),
        })
    return elements

def compute_clearances(elements: list) -> dict:
    # Identify key elements by name
    by_name = {}
    for el in elements:
        by_name.setdefault(el["name"], []).append(el)

    # Distinguish island body from bar seating (island_or_bar)
    # Island body is the larger rect; bar is shallower (smaller depth)
    island_body = None
    bar_seating = None
    for el in by_name.get("island_or_bar", []):
        if island_body is None or el["depth_in"] > island_body["depth_in"]:
            island_body = el
    for el in by_name.get("island_or_bar", []):
        if el is not island_body:
            bar_seating = el

    results = {"elements": elements, "clearances": [], "flags": []}

    if island_body:
        west_aisle = island_body["left_in"]
        east_aisle = KIT_W_IN - island_body["right_in"]
        results["clearances"].append({
            "label": "West aisle (interior wall to island)",
            "value_in": west_aisle,
            "required_in": 42,
            "ref": "NKBA G12",
            "result": "PASS" if west_aisle >= 42 else "FAIL"
        })
        results["clearances"].append({
            "label": "East aisle (island to east counter/wall)",
            "value_in": east_aisle,
            "required_in": 42,
            "ref": "NKBA G12",
            "result": "PASS" if east_aisle >= 42 else "FAIL",
            "note": "DW alcove may reduce usable east aisle -- verify in person"
        })

    if bar_seating:
        south_aisle = KIT_H_IN - bar_seating["bottom_in"]
        results["clearances"].append({
            "label": "South aisle (bar seating south face to south wall)",
            "value_in": round(south_aisle, 1),
            "required_in": 42,
            "ref": "NKBA G12",
            "result": "PASS" if south_aisle >= 42 else "FAIL",
            "note": f"Bar seating south face is {round(bar_seating['bottom_in'],1)}\" from north wall; kitchen is {KIT_H_IN}\" deep"
        })
        if south_aisle < 42:
            results["flags"].append(
                f"SOUTH AISLE = {round(south_aisle,1)}\": BELOW NKBA 42\" minimum. "
                f"Bar seating south face at {round(bar_seating['bottom_in'],1)}\" from north, "
                f"south wall at {KIT_H_IN}\". Gap = {round(south_aisle,1)}\". "
                f"May be acceptable if this is a secondary circulation path -- confirm with designer."
            )

    if island_body:
        north_aisle = island_body["top_in"]
        results["clearances"].append({
            "label": "North aisle (north wall to island north face)",
            "value_in": round(north_aisle, 1),
            "required_in": 42,
            "ref": "NKBA G12",
            "result": "PASS" if north_aisle >= 42 else "FAIL",
            "note": "North counter area (sink+fridge) behind island"
        })

    results["overall"] = "FAIL" if any(c["result"] == "FAIL" for c in results["clearances"]) else "PARTIAL"
    return results

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--svg", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    elements = parse_elements(args.svg)
    result = compute_clearances(elements)

    out = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(out)
        print(f"Written to {args.output}")
    else:
        print(out)

if __name__ == "__main__":
    main()
