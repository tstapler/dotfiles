#!/usr/bin/env python3
"""
Add a calibrated 2-foot reference grid to a kitchen floor plan PNG.
Grid is anchored to kitchen interior corners extracted from SVG geometry.

Usage:
  python3 add_grid.py --svg /path/to/drawing.svg --png /path/to/2000px.png --out /tmp/gridded.png
"""

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Kitchen geometry constants (from SVG analysis of 711 N60th kitchen)
# These are in SVG units (1100 wide canvas)
SVG_CANVAS_W = 1100.0
SVG_CANVAS_H = 850.0

# Scale from SVG units to real inches (verified from fridge: 158.7 SVG = 48")
SVG_PER_INCH = 158.7 / 48.0   # = 3.306

# Kitchen interior corners in SVG units (verified from fridge + DXF)
KIT_SVG_X0 = 297.1   # interior west wall
KIT_SVG_X1 = 822.8   # interior east wall
KIT_SVG_Y0 = 166.0   # interior north wall (SVG Y increases downward)
KIT_SVG_Y1 = 579.1   # interior south wall

# Kitchen interior size in inches (verified from labels)
KIT_W_IN = 159.0   # EW width  (13'-3")
KIT_H_IN = 125.0   # NS depth  (10'-5")

# Grid cell size
GRID_IN = 24.0   # 2-foot grid cells


def auto_detect_kitchen(svg_path: Path):
    """Try to auto-detect kitchen interior from SVG rect/line extents."""
    ns = "{http://www.w3.org/2000/svg}"
    tree = ET.parse(svg_path)
    root = tree.getroot()

    # Collect all colored rects (appliances) to re-derive kitchen bounds
    rects = []
    for el in root.iter(f"{ns}rect"):
        try:
            x = float(el.get("x", 0))
            y = float(el.get("y", 0))
            w = float(el.get("width", 0))
            h = float(el.get("height", 0))
            fill = el.get("fill", "")
            if fill not in ("white", "#f0f0f8", "none", "") and w > 20 and h > 20:
                rects.append((x, y, x+w, y+h, fill))
        except (ValueError, TypeError):
            pass

    if not rects:
        return None

    # The kitchen interior roughly spans appliance positions
    min_x = min(r[0] for r in rects)
    max_x = max(r[2] for r in rects)
    min_y = min(r[1] for r in rects)
    max_y = max(r[3] for r in rects)

    return (min_x - 20, min_y - 20, max_x + 20, max_y + 20)


def svg_to_png_coords(svg_x, svg_y, png_w, png_h):
    """Convert SVG canvas coordinates to PNG pixel coordinates."""
    scale_x = png_w / SVG_CANVAS_W
    scale_y = png_h / SVG_CANVAS_H
    return svg_x * scale_x, svg_y * scale_y


def add_grid(svg_path: Path, png_path: Path, out_path: Path,
             grid_in: float = GRID_IN,
             kit_x0: float = KIT_SVG_X0, kit_x1: float = KIT_SVG_X1,
             kit_y0: float = KIT_SVG_Y0, kit_y1: float = KIT_SVG_Y1):

    img = Image.open(png_path).convert("RGBA")
    png_w, png_h = img.size

    # Scale factors from SVG units to PNG pixels
    sx = png_w / SVG_CANVAS_W
    sy = png_h / SVG_CANVAS_H

    # Kitchen interior corners in PNG pixels
    px0 = kit_x0 * sx   # west
    px1 = kit_x1 * sx   # east
    py0 = kit_y0 * sy   # north (top in PNG)
    py1 = kit_y1 * sy   # south (bottom in PNG)

    # Pixels per 2-foot cell
    cell_px_x = grid_in * SVG_PER_INCH * sx
    cell_px_y = grid_in * SVG_PER_INCH * sy

    # Number of cells
    n_cols = int((kit_x1 - kit_x0) / (grid_in * SVG_PER_INCH)) + 1
    n_rows = int((kit_y1 - kit_y0) / (grid_in * SVG_PER_INCH)) + 1

    # Create overlay layer
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    grid_color = (60, 120, 200, 100)     # blue, semi-transparent
    label_bg = (255, 255, 255, 180)
    label_color = (30, 80, 180, 255)
    border_color = (200, 40, 40, 180)    # red border for kitchen extent

    # Draw kitchen interior border
    draw.rectangle([px0, py0, px1, py1], outline=border_color, width=3)

    # Draw vertical grid lines (columns, west=A to east)
    for col in range(n_cols + 1):
        px = px0 + col * cell_px_x
        if px > px1 + 2:
            break
        draw.line([(px, py0), (px, min(px, py1))], fill=grid_color, width=1)

    # Draw horizontal grid lines (rows, north=top)
    for row in range(n_rows + 1):
        py = py0 + row * cell_px_y
        if py > py1 + 2:
            break
        draw.line([(px0, py), (min(py, px1), py)], fill=grid_color, width=1)

    # Label each cell — columns A-Z (west to east), rows 1-N (north to south, 1=north)
    # Note: row 1 = north in this scheme (SVG convention, matches drawing view)
    # For spatial communication with Claude: A1=NW, G6=SE
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
        font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except Exception:
        font = ImageFont.load_default()
        font_sm = font

    col_letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    for row in range(n_rows):
        for col in range(n_cols):
            cx = px0 + col * cell_px_x + cell_px_x / 2
            cy = py0 + row * cell_px_y + cell_px_y / 2

            if cx > px1 or cy > py1:
                continue

            label = f"{col_letters[col]}{row+1}"

            # Measure text
            bbox = draw.textbbox((0, 0), label, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            lx = cx - tw / 2
            ly = cy - th / 2

            # Background pill
            pad = 3
            draw.rounded_rectangle(
                [lx - pad, ly - pad, lx + tw + pad, ly + th + pad],
                radius=4, fill=label_bg
            )
            draw.text((lx, ly), label, fill=label_color, font=font)

    # Add compass (N arrow region label)
    draw.text((px0 + 5, py0 + 5), "N", fill=(180, 40, 40, 220), font=font)
    draw.text((px0 + 5, py1 - 25), "S", fill=(180, 40, 40, 220), font=font)

    # Add scale note at bottom-right of kitchen area
    scale_note = f"Grid: 2 ft cells | Kitchen interior: {int(KIT_W_IN//12)}\'-{int(KIT_W_IN%12)}\" x {int(KIT_H_IN//12)}\'-{int(KIT_H_IN%12)}\""
    draw.text((px0, py1 + 5), scale_note, fill=(60, 60, 60, 200), font=font_sm)

    # Composite
    result = Image.alpha_composite(img, overlay)
    result = result.convert("RGB")
    result.save(out_path)
    print(f"Grid overlay written to {out_path}")
    print(f"Kitchen interior: ({px0:.0f},{py0:.0f}) to ({px1:.0f},{py1:.0f}) px")
    print(f"Grid: {n_cols} cols (A-{col_letters[n_cols-1]}) x {n_rows} rows, {cell_px_x:.0f}x{cell_px_y:.0f} px/cell")
    return {"cols": n_cols, "rows": n_rows, "cell_px": (cell_px_x, cell_px_y),
            "kitchen_px": (px0, py0, px1, py1)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--svg", type=Path, required=True, help="Source SVG (for auto-detection)")
    parser.add_argument("--png", type=Path, required=True, help="Rasterized PNG input")
    parser.add_argument("--out", type=Path, required=True, help="Output PNG with grid")
    parser.add_argument("--grid-ft", type=float, default=2.0, help="Grid cell size in feet (default 2)")
    args = parser.parse_args()

    add_grid(args.svg, args.png, args.out, grid_in=args.grid_ft * 12)


if __name__ == "__main__":
    main()
