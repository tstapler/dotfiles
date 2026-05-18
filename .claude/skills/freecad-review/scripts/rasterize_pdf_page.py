#!/usr/bin/env python3
"""
Extract a specific page from a PDF as a high-resolution PNG.
Designed for comparing CD set drawings against BIM SVG output.

Usage:
  python3 rasterize_pdf_page.py --pdf path/to/cd_set.pdf --page 9 --out /tmp/cd_page9.png
  python3 rasterize_pdf_page.py --pdf ... --page 9 --out /tmp/cd_p9_crop.png \
      --crop 100 200 1400 900   # x0 y0 x1 y1 in PDF points (origin top-left)
  python3 rasterize_pdf_page.py --pdf ... --page 9 --width 2000  # match BIM SVG rasterization

Scale context (711 N60th CD set):
  Page 4  (Level 1 floor plan):     1/4" = 1'-0"  -> 1 ft = 18 pts
  Page 8  (kitchen int elevations): 1/4" = 1'-0"  -> 1 ft = 18 pts
  Page 9  (casework elevations):    1/2" = 1'-0"  -> 1 ft = 36 pts
  Page 10 (casework elevations):    1/2" = 1'-0"  -> 1 ft = 36 pts

BIM SVG elevations (kitchen_elev_*.svg) are at 1/2" = 1'-0" scale.
So:
  Page 9/10 vs BIM elevations: same drawing scale, crop and compare directly.
  Page 8 vs BIM elevations:    CD is half the scale; multiply CD raster width x2 before comparing.
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import fitz
except ImportError:
    print("ERROR: PyMuPDF not installed. Run: ~/.claude/skills/pdf-proof/.venv/bin/pip install PyMuPDF", file=sys.stderr)
    sys.exit(1)


SCALE_TABLE = {
    "1/4": 18.0,
    "1/2": 36.0,
    "1": 72.0,
}

CD_SET_SCALES = {
    4: ("1/4", 18.0, "Level 1 Floor Plan"),
    8: ("1/4", 18.0, "Kitchen Interior Elevations"),
    9: ("1/2", 36.0, "Kitchen Casework Elevations"),
    10: ("1/2", 36.0, "Kitchen Casework Elevations"),
}


def rasterize_page(pdf_path: Path, page_num: int, out_path: Path,
                   crop=None, target_width=None, dpi=150):
    doc = fitz.open(str(pdf_path))
    total = len(doc)
    if not 1 <= page_num <= total:
        print(f"ERROR: Page {page_num} out of range (1-{total})", file=sys.stderr)
        sys.exit(1)

    page = doc[page_num - 1]
    rect = page.rect  # full page in PDF points

    if crop:
        x0, y0, x1, y1 = crop
        clip = fitz.Rect(x0, y0, x1, y1)
    else:
        clip = rect

    scale = dpi / 72.0
    if target_width:
        scale = target_width / clip.width

    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
    pix.save(str(out_path))

    info = {
        "pdf": str(pdf_path),
        "page": page_num,
        "page_size_pts": [rect.width, rect.height],
        "clip_pts": [clip.x0, clip.y0, clip.x1, clip.y1],
        "output_px": [pix.width, pix.height],
        "scale_factor": scale,
    }

    if page_num in CD_SET_SCALES:
        scale_str, pts_per_ft, label = CD_SET_SCALES[page_num]
        px_per_ft = pts_per_ft * scale
        info["drawing_scale"] = f'{scale_str}" = 1\'-0"'
        info["drawing_label"] = label
        info["px_per_ft"] = round(px_per_ft, 1)
        info["bim_match_note"] = (
            "Same scale as BIM SVGs — direct comparison valid"
            if scale_str == "1/2"
            else f"CD is at {scale_str}\" scale; BIM is at 1/2\" scale — multiply CD pixel dimensions x{round(0.5 / float(scale_str.split('/')[0]) * float(scale_str.split('/')[1])):.0f} before pixel-diff"
        )

    return info


def main():
    parser = argparse.ArgumentParser(description="Extract PDF page as PNG for CD set comparison")
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--page", type=int, required=True, help="1-based page number")
    parser.add_argument("--out", type=Path, required=True, help="Output PNG path")
    parser.add_argument("--crop", type=float, nargs=4, metavar=("X0", "Y0", "X1", "Y1"),
                        help="Crop region in PDF points (origin top-left)")
    parser.add_argument("--width", type=int, help="Target output width in pixels (default: use --dpi)")
    parser.add_argument("--dpi", type=int, default=150, help="Output DPI if --width not set (default 150)")
    parser.add_argument("--info", action="store_true", help="Print page info and exit without rasterizing")
    args = parser.parse_args()

    if args.info:
        doc = fitz.open(str(args.pdf))
        for i, page in enumerate(doc):
            label = CD_SET_SCALES.get(i + 1, ("?", 0, "Unknown"))
            print(f"Page {i+1:2d}: {page.rect.width:.0f}x{page.rect.height:.0f} pts  {label[2]}")
        return

    info = rasterize_page(
        args.pdf, args.page, args.out,
        crop=args.crop, target_width=args.width, dpi=args.dpi
    )
    print(json.dumps(info, indent=2))
    print(f"\nWritten: {args.out}")


if __name__ == "__main__":
    main()
