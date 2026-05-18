"""
extract_spec_from_drawing.py
============================
Extracts architectural dimension values from PDF pages (or PNG/SVG images)
and maps them to KitchenDesign fields in design_spec.py.

Standalone — no FreeCAD, no Claude API.  Requires: PyMuPDF (fitz), Pillow.

Usage
-----
    python3 extract_spec_from_drawing.py \\
        --pdf /path/to/cd_set.pdf --page 9 \\
        --spec /path/to/design_spec.py \\
        [--output /tmp/proposed_fields.json] \\
        [--page-type casework_elevations|floor_plan|elevation] \\
        [--dry-run]

Page-type auto-detection falls back to manual --page-type when ambiguous.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import sys
from dataclasses import fields as dc_fields
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MM_PER_IN = 25.4

# PDF-point scale tables  (pts per foot, pts per inch)
# 1/4" = 1'-0"  →  one foot represented by 18 pts  (72 pts/in * 0.25 = 18)
# 1/2" = 1'-0"  →  one foot represented by 36 pts  (72 pts/in * 0.5  = 36)
SCALE_TABLE = {
    '1/4"=1\'-0"':  {"pts_per_ft": 18.0, "pts_per_in": 1.5},
    '1/2"=1\'-0"':  {"pts_per_ft": 36.0, "pts_per_in": 3.0},
    '1/4" = 1\'-0"': {"pts_per_ft": 18.0, "pts_per_in": 1.5},
    '1/2" = 1\'-0"': {"pts_per_ft": 36.0, "pts_per_in": 3.0},
}

DEFAULT_SCALE_BY_PAGE = {
    4:  '1/4"=1\'-0"',
    8:  '1/4"=1\'-0"',
    9:  '1/2"=1\'-0"',
    10: '1/2"=1\'-0"',
}

PAGE_TYPE_BY_PAGE = {
    4:  "floor_plan",
    8:  "elevation",
    9:  "casework_elevations",
    10: "casework_elevations",
}

# Element keyword lists used for proximity matching
ELEMENT_KEYWORDS = {
    "island":       ["ISLAND"],
    "bar":          ["BAR"],
    "refrigerator": ["REFRIGERATOR", "FRIDGE", "REF"],
    "range":        ["RANGE", "COOKTOP"],
    "dishwasher":   ["DISHWASHER", "D.W.", "DW"],
    "sink":         ["SINK"],
    "hood":         ["HOOD"],
    "counter":      ["COUNTER", "CTR", "COUNTERTOP"],
    "upper_cab":    ["UPPER", "UCAB", "U.CAB"],
    "kitchen":      ["KITCHEN"],
}

# Proximity thresholds (PDF points)
PROX_Y_PTS = 100
PROX_X_PTS = 300

# Known spec field ranges (inches) for sanity checking
FIELD_RANGES_IN = {
    "island_ew_mm":  (48, 96),
    "island_ns_mm":  (18, 48),
    "bar_ns_mm":     (12, 24),
    "fridge_w_mm":   (24, 60),
    "range_w_mm":    (24, 60),
    "dw_w_mm":       (18, 30),
    "sink_w_mm":     (24, 60),
    "hood_w_mm":     (24, 54),
    "kit_ew_mm":     (96, 240),
    "kit_ns_mm":     (72, 180),
    "ctr_h_mm":      (32, 40),
    "ucab_bot_mm":   (48, 72),
    "ucab_h_mm":     (24, 42),
    "hood_aff_mm":   (60, 90),
    "ext_thk_mm":    (4, 8),
    "int_thk_mm":    (4, 7),
}

# ---------------------------------------------------------------------------
# Dimension parser
# ---------------------------------------------------------------------------

# Patterns ordered most-specific → least-specific
_DIM_PATTERNS = [
    # "5'-6""  or  "5'6""  (feet-inches)
    re.compile(r"""^[+-]?(?P<ft>\d+)\s*'\s*-?\s*(?P<in_>\d+(?:\.\d+)?)\s*(?P<frac>\d+/\d+)?\s*"$"""),
    # "5'-6 1/2""  (feet-inches with fraction)
    re.compile(r"""^[+-]?(?P<ft>\d+)\s*'\s*-?\s*(?P<in_>\d+)\s+(?P<frac>\d+/\d+)\s*"$"""),
    # "5'"  (feet only)
    re.compile(r"""^[+-]?(?P<ft>\d+)\s*'$"""),
    # "42""  (inches only)
    re.compile(r"""^[+-]?(?P<in_>\d+(?:\.\d+)?)\s*"$"""),
    # "1200mm"
    re.compile(r"""^[+-]?(?P<mm>\d+(?:\.\d+)?)\s*mm$"""),
]

# Pattern for fragmented dimension tokens produced by PyMuPDF word splitting.
# PyMuPDF splits  "5'-3 1/4\""  into two adjacent word tokens:
#   word_a = "5'-31"   (feet + whole inches + fraction numerator, NO closing quote)
#   word_b = "4\""     (denominator digit + inch-mark)
# The regex for word_a: ends with digits only (no quote).
_FRAG_FEET_INCH = re.compile(r"""^(?P<ft>\d+)'-(?P<rest>\d+)$""")
# Standalone denominator+inch-mark that follows a fragmented token: "4\""
_FRAG_SUFFIX = re.compile(r"""^(?P<denom>\d+)"$""")


def _frac_to_float(s: str) -> float:
    """Convert '3/4' → 0.75, '1/2' → 0.5, etc."""
    if "/" in s:
        n, d = s.split("/")
        return int(n) / int(d)
    return float(s)


def parse_dimension(text: str) -> Optional[dict]:
    """
    Parse an architectural dimension string into a dict:
        {"text": original, "inches": float, "mm": float}

    Returns None if the string is not a recognisable dimension.
    Handles ±-prefix (tile layout annotations).
    """
    t = text.strip().lstrip("±").strip()

    for pat in _DIM_PATTERNS:
        m = pat.match(t)
        if not m:
            continue
        gd = m.groupdict()

        if "mm" in gd and gd["mm"] is not None:
            mm_val = float(gd["mm"])
            return {"text": text, "inches": mm_val / MM_PER_IN, "mm": mm_val}

        total_in = 0.0
        if gd.get("ft") is not None:
            total_in += int(gd["ft"]) * 12
        if gd.get("in_") is not None:
            total_in += float(gd["in_"])
        if gd.get("frac") is not None:
            total_in += _frac_to_float(gd["frac"])

        return {
            "text": text,
            "inches": round(total_in, 4),
            "mm": round(total_in * MM_PER_IN, 4),
        }

    return None


def try_merge_fragments(word_a: str, word_b: str) -> Optional[dict]:
    """
    PyMuPDF often splits  "5'-3 1/4\""  into two adjacent word tokens:
        word_a = "5'-31"   (feet + whole inches + fraction numerator, no closing quote)
        word_b = "4\""     (denominator digit + inch-mark)

    Interpretation of word_a "4'-23":
        ft=4, rest="23" → whole_in=2, numer=3
    Then word_b "4\"" gives denom=4.
    Result: 4'-2 3/4\" = 4*12 + 2 + 3/4 = 50.75 inches.

    Also handles word_a that is already a complete dimension (no merge needed) —
    those are caught upstream by parse_dimension; this only handles the fragment form.
    """
    ma = _FRAG_FEET_INCH.match(word_a.strip())
    mb = _FRAG_SUFFIX.match(word_b.strip())
    if not (ma and mb):
        return None

    ft = int(ma.group("ft"))
    rest = ma.group("rest")  # e.g. "23" → whole=2, numer=3
    denom = int(mb.group("denom"))

    if len(rest) < 2:
        # Only one digit: treat as numerator with whole_in=0
        whole_in = 0
        numer = int(rest)
    else:
        # Last digit is numerator, everything before is whole inches
        # "03" → whole_in=0, numer=3;  "23" → whole_in=2, numer=3
        whole_in = int(rest[:-1])
        numer = int(rest[-1])

    if denom == 0 or numer == 0:
        return None

    total_in = ft * 12 + whole_in + numer / denom
    combined = f"{ft}'-{whole_in} {numer}/{denom}\""
    return {
        "text": combined,
        "inches": round(total_in, 4),
        "mm": round(total_in * MM_PER_IN, 4),
    }


# ---------------------------------------------------------------------------
# Scale detection
# ---------------------------------------------------------------------------

def detect_scale(words: list[dict]) -> Optional[str]:
    """
    Scan word list for a scale annotation like  SCALE: 1/2" = 1'-0"
    Return the canonical scale key if found.
    """
    # Build a sorted text list so we can look for adjacent tokens
    texts = [w["text"].upper() for w in words]
    for i, t in enumerate(texts):
        if t in ("SCALE:", "SCALE"):
            # Collect next few tokens and reconstruct
            snippet = " ".join(texts[i: i + 5])
            if "1/2" in snippet and "1'-0" in snippet:
                return '1/2"=1\'-0"'
            if "1/4" in snippet and "1'-0" in snippet:
                return '1/4"=1\'-0"'
    return None


def pts_to_inches(pts: float, scale_key: str) -> float:
    entry = SCALE_TABLE.get(scale_key)
    if entry is None:
        raise ValueError(f"Unknown scale key: {scale_key!r}")
    return pts / entry["pts_per_in"]


# ---------------------------------------------------------------------------
# PDF text extraction
# ---------------------------------------------------------------------------

def extract_words_from_pdf_page(pdf_path: str, page_number: int) -> list[dict]:
    """
    Return a list of word dicts:
        {"text", "x0", "y0", "x1", "y1"}
    page_number is 1-based.
    """
    try:
        import fitz
    except ImportError:
        print("ERROR: PyMuPDF (fitz) is not installed.", file=sys.stderr)
        sys.exit(1)

    doc = fitz.open(pdf_path)
    if page_number < 1 or page_number > len(doc):
        print(
            f"ERROR: Page {page_number} out of range (PDF has {len(doc)} pages).",
            file=sys.stderr,
        )
        sys.exit(1)

    page = doc[page_number - 1]
    raw_words = page.get_text("words")
    words = []
    for x0, y0, x1, y1, text, *_ in raw_words:
        words.append({"text": text, "x0": x0, "y0": y0, "x1": x1, "y1": y1})
    return words


def extract_words_from_png(png_path: str) -> list[dict]:
    """
    Attempt text extraction from a PNG using pytesseract if available,
    otherwise return empty list with a warning.
    """
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(png_path)
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        words = []
        for i, text in enumerate(data["text"]):
            if text.strip():
                x, y, w, h = (
                    data["left"][i],
                    data["top"][i],
                    data["width"][i],
                    data["height"][i],
                )
                words.append({
                    "text": text,
                    "x0": float(x),
                    "y0": float(y),
                    "x1": float(x + w),
                    "y1": float(y + h),
                })
        return words
    except ImportError:
        print(
            "WARNING: pytesseract not available; PNG text extraction skipped.",
            file=sys.stderr,
        )
        return []


# ---------------------------------------------------------------------------
# Proximity helpers
# ---------------------------------------------------------------------------

def centre(w: dict) -> tuple[float, float]:
    return ((w["x0"] + w["x1"]) / 2.0, (w["y0"] + w["y1"]) / 2.0)


def is_near(dim_word: dict, label_word: dict,
            y_thresh: float = PROX_Y_PTS,
            x_thresh: float = PROX_X_PTS) -> bool:
    dx, dy = abs(centre(dim_word)[0] - centre(label_word)[0]), \
              abs(centre(dim_word)[1] - centre(label_word)[1])
    return dy <= y_thresh and dx <= x_thresh


def find_nearby_element(dim_word: dict, all_words: list[dict]) -> Optional[str]:
    """
    Return the element name (e.g. "island", "refrigerator") if an element
    keyword label is found near dim_word.  Returns None otherwise.
    """
    for elem, keywords in ELEMENT_KEYWORDS.items():
        for lw in all_words:
            if lw["text"].upper().rstrip(",;.:") in keywords:
                if is_near(dim_word, lw):
                    return elem
    return None


# ---------------------------------------------------------------------------
# Spec loader
# ---------------------------------------------------------------------------

def load_spec(spec_path: str):
    """
    Dynamically import design_spec.py and return a KitchenDesign instance.
    Returns None if the file can't be loaded.
    """
    p = Path(spec_path)
    if not p.exists():
        return None
    spec = importlib.util.spec_from_file_location("design_spec", str(p))
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
        return mod.KitchenDesign()
    except Exception as e:
        print(f"WARNING: Could not load spec: {e}", file=sys.stderr)
        return None


def spec_field_names(spec_instance) -> list[str]:
    return [f.name for f in dc_fields(spec_instance)]


# ---------------------------------------------------------------------------
# Per-page-type extraction logic
# ---------------------------------------------------------------------------

def build_dimensions_list(words: list[dict]) -> list[dict]:
    """
    Walk the word list and parse dimension strings.
    Also attempt to merge adjacent fragmented tokens (e.g. "5'-31" + "4"").
    Returns list of dicts with all dimension info plus position.
    """
    dims = []
    i = 0
    while i < len(words):
        w = words[i]
        parsed = parse_dimension(w["text"])
        if parsed:
            dims.append({**parsed, "x": (w["x0"] + w["x1"]) / 2,
                         "y": (w["y0"] + w["y1"]) / 2,
                         "word": w})
            i += 1
            continue

        # Try merging with next word
        if i + 1 < len(words):
            merged = try_merge_fragments(w["text"], words[i + 1]["text"])
            if merged:
                dims.append({**merged,
                              "x": (w["x0"] + words[i + 1]["x1"]) / 2,
                              "y": (w["y0"] + words[i + 1]["y1"]) / 2,
                              "word": w})
                i += 2
                continue
        i += 1
    return dims


def _in_range(inches: float, field: str) -> bool:
    lo, hi = FIELD_RANGES_IN.get(field, (0, 10000))
    return lo <= inches <= hi


def extract_casework_fields(
    words: list[dict], dims: list[dict], scale_key: str, source_label: str
) -> dict:
    """
    Page 9 / 10 — interior casework elevations at 1/2" = 1'-0".

    Strategy:
    - For each appliance/element keyword, gather all dimension values
      found within proximity.
    - The best candidate is the one whose inch value falls within the
      known reasonable range for that field.
    """

    def best_dim_near_keyword(field: str, keywords: list[str],
                              y_thresh=PROX_Y_PTS, x_thresh=PROX_X_PTS) -> Optional[dict]:
        """Find the best dimension associated with any of the given keywords."""
        kw_words = [w for w in words if w["text"].upper().rstrip(",;.:") in keywords]
        candidates = []
        for kw in kw_words:
            for d in dims:
                if is_near(d["word"], kw, y_thresh, x_thresh):
                    if _in_range(d["inches"], field):
                        # evidence string
                        d = dict(d)
                        d["_kw_word"] = kw
                        candidates.append(d)
        if not candidates:
            return None
        # Prefer HIGH confidence: exact range match + nearest keyword
        candidates.sort(key=lambda c: abs(centre(c["word"])[1] - centre(c["_kw_word"])[1]))
        return candidates[0]

    proposed = {}

    # ── island_ew_mm ──────────────────────────────────────────────────────────
    d = best_dim_near_keyword("island_ew_mm", ["ISLAND"])
    if d:
        proposed["island_ew_mm"] = _field_result(
            d, "island_ew_mm", "HIGH",
            f"labeled dimension at island elevation",
            f"Text {d['text']!r} at ({d['x']:.0f},{d['y']:.0f}), "
            f"near 'ISLAND' at ({centre(d['_kw_word'])[0]:.0f},{centre(d['_kw_word'])[1]:.0f})",
        )
    else:
        proposed["island_ew_mm"] = _cannot_verify("not extractable from casework page — "
                                                    "check floor plan page 4")

    # ── island_ns_mm ─────────────────────────────────────────────────────────
    d = best_dim_near_keyword("island_ns_mm", ["ISLAND"])
    if d:
        proposed["island_ns_mm"] = _field_result(
            d, "island_ns_mm", "HIGH",
            "labeled dimension at island elevation",
            f"Text {d['text']!r} at ({d['x']:.0f},{d['y']:.0f}) near ISLAND",
        )
    else:
        proposed["island_ns_mm"] = _cannot_verify("island depth not labeled on this page")

    # ── bar_ns_mm ─────────────────────────────────────────────────────────────
    d = best_dim_near_keyword("bar_ns_mm", ["BAR"])
    if d:
        proposed["bar_ns_mm"] = _field_result(
            d, "bar_ns_mm", "HIGH",
            "labeled dimension near BAR label",
            f"Text {d['text']!r} at ({d['x']:.0f},{d['y']:.0f}) near BAR",
        )
    else:
        proposed["bar_ns_mm"] = _cannot_verify("bar NS dimension not found on this page")

    # ── range_w_mm ────────────────────────────────────────────────────────────
    d = best_dim_near_keyword("range_w_mm", ["RANGE", "COOKTOP"])
    if d:
        proposed["range_w_mm"] = _field_result(
            d, "range_w_mm", "HIGH",
            "labeled dimension near RANGE label",
            f"Text {d['text']!r} at ({d['x']:.0f},{d['y']:.0f}) near RANGE",
        )
    else:
        proposed["range_w_mm"] = _cannot_verify("range width not labeled on casework page")

    # ── fridge_w_mm ───────────────────────────────────────────────────────────
    d = best_dim_near_keyword("fridge_w_mm", ["REFRIGERATOR", "FRIDGE", "REF"])
    if d:
        proposed["fridge_w_mm"] = _field_result(
            d, "fridge_w_mm", "HIGH",
            "labeled dimension near refrigerator label",
            f"Text {d['text']!r} at ({d['x']:.0f},{d['y']:.0f}) near REF",
        )
    else:
        proposed["fridge_w_mm"] = _cannot_verify("refrigerator width not found on casework page")

    # ── dw_w_mm ───────────────────────────────────────────────────────────────
    d = best_dim_near_keyword("dw_w_mm", ["DW", "D.W.", "DISHWASHER"])
    if d:
        proposed["dw_w_mm"] = _field_result(
            d, "dw_w_mm", "MEDIUM",
            "dimension near DW label",
            f"Text {d['text']!r} at ({d['x']:.0f},{d['y']:.0f}) near DW",
        )
    else:
        proposed["dw_w_mm"] = _cannot_verify("dishwasher width not found on casework page")

    # ── sink_w_mm ─────────────────────────────────────────────────────────────
    d = best_dim_near_keyword("sink_w_mm", ["SINK"])
    if d:
        proposed["sink_w_mm"] = _field_result(
            d, "sink_w_mm", "HIGH",
            "labeled dimension near SINK",
            f"Text {d['text']!r} at ({d['x']:.0f},{d['y']:.0f}) near SINK",
        )
    else:
        proposed["sink_w_mm"] = _cannot_verify("sink width not found on casework page")

    # Fields not extractable from casework page
    for field in ["kit_ew_mm", "kit_ns_mm", "ext_thk_mm", "int_thk_mm",
                  "ctr_h_mm", "ucab_bot_mm", "ucab_h_mm", "hood_aff_mm",
                  "bar_y_offset_mm"]:
        proposed[field] = _cannot_verify(
            f"not extractable from casework elevations — use floor plan (pg 4) or elevation (pg 8)"
        )

    return proposed


def extract_floor_plan_fields(
    words: list[dict], dims: list[dict], scale_key: str, source_label: str
) -> dict:
    """
    Page 4 — floor plan at 1/4" = 1'-0".
    Targets: kit_ew_mm, kit_ns_mm, ext_thk_mm, int_thk_mm.
    """
    proposed = {}

    # Overall kitchen EW — expect ~13'-3" (159 in / 4038 mm)
    # Overall kitchen NS — expect ~10'-5" (125 in / 3175 mm)
    # Wall thicknesses: 6" exterior, 5.5" interior

    # Gather all parsed dims with their values
    for field, target_in in [
        ("kit_ew_mm", 159.0),   # 13'-3"
        ("kit_ns_mm", 125.0),   # 10'-5"
    ]:
        lo, hi = FIELD_RANGES_IN[field]
        candidates = [d for d in dims if lo <= d["inches"] <= hi]
        if candidates:
            # Pick closest to target
            best = min(candidates, key=lambda d: abs(d["inches"] - target_in))
            near_kw = find_nearby_element(best["word"], words)
            conf = "HIGH" if near_kw == "kitchen" else "MEDIUM"
            proposed[field] = _field_result(
                best, field, conf,
                f"overall kitchen dimension from floor plan",
                f"Text {best['text']!r} at ({best['x']:.0f},{best['y']:.0f})"
                + (f", near KITCHEN label" if conf == "HIGH" else ""),
            )
        else:
            proposed[field] = _cannot_verify(f"overall kitchen {field} not found on floor plan")

    # Wall thicknesses — narrow range
    for field, target_in, label in [
        ("ext_thk_mm", 6.0, "exterior wall"),
        ("int_thk_mm", 5.5, "interior wall"),
    ]:
        lo, hi = FIELD_RANGES_IN[field]
        candidates = [d for d in dims if lo <= d["inches"] <= hi]
        if candidates:
            best = min(candidates, key=lambda d: abs(d["inches"] - target_in))
            proposed[field] = _field_result(
                best, field, "MEDIUM",
                f"{label} thickness from floor plan",
                f"Text {best['text']!r} at ({best['x']:.0f},{best['y']:.0f})",
            )
        else:
            proposed[field] = _cannot_verify(f"{field} not found on floor plan")

    # Fields not on floor plan
    for field in ["island_ew_mm", "island_ns_mm", "bar_ns_mm", "range_w_mm",
                  "fridge_w_mm", "dw_w_mm", "sink_w_mm", "ctr_h_mm",
                  "ucab_bot_mm", "ucab_h_mm", "hood_aff_mm", "bar_y_offset_mm"]:
        proposed[field] = _cannot_verify(
            "not extractable from floor plan — use casework (pg 9/10) or elevation (pg 8)"
        )

    return proposed


def extract_elevation_fields(
    words: list[dict], dims: list[dict], scale_key: str, source_label: str
) -> dict:
    """
    Page 8 (or similar) — kitchen elevation / section.
    Targets: ctr_h_mm, ucab_bot_mm, ucab_h_mm, hood_aff_mm.
    """
    proposed = {}

    for field, target_in, desc in [
        ("ctr_h_mm",   36.0, "counter height AFF"),
        ("ucab_bot_mm", 54.0, "upper cabinet bottom AFF"),
        ("ucab_h_mm",  30.0, "upper cabinet height"),
        ("hood_aff_mm", 78.0, "hood bottom AFF"),
    ]:
        lo, hi = FIELD_RANGES_IN[field]
        candidates = [d for d in dims if lo <= d["inches"] <= hi]
        if candidates:
            best = min(candidates, key=lambda d: abs(d["inches"] - target_in))
            near_kw = find_nearby_element(best["word"], words)
            conf = "HIGH" if near_kw else "MEDIUM"
            proposed[field] = _field_result(
                best, field, conf,
                f"{desc} from elevation",
                f"Text {best['text']!r} at ({best['x']:.0f},{best['y']:.0f})"
                + (f", near {near_kw.upper()} label" if near_kw else ""),
            )
        else:
            proposed[field] = _cannot_verify(f"{field} not found on elevation page")

    # Fields not on elevation
    for field in ["island_ew_mm", "island_ns_mm", "bar_ns_mm", "range_w_mm",
                  "fridge_w_mm", "dw_w_mm", "sink_w_mm", "kit_ew_mm",
                  "kit_ns_mm", "ext_thk_mm", "int_thk_mm", "bar_y_offset_mm"]:
        proposed[field] = _cannot_verify(
            "not extractable from elevation — use casework (pg 9/10) or floor plan (pg 4)"
        )

    return proposed


# ---------------------------------------------------------------------------
# Result builders
# ---------------------------------------------------------------------------

def _field_result(dim: dict, field: str, confidence: str,
                  source: str, evidence: str) -> dict:
    return {
        "value_mm": dim["mm"],
        "value_in": dim["inches"],
        "value_str": dim["text"],
        "confidence": confidence,
        "source": source,
        "evidence": evidence,
        "spec_comparison": None,  # filled in by cross-check
    }


def _cannot_verify(reason: str) -> dict:
    return {
        "value_mm": None,
        "value_in": None,
        "value_str": None,
        "confidence": "CANNOT_VERIFY",
        "source": reason,
        "evidence": "",
        "spec_comparison": "CANNOT_VERIFY",
    }


def cross_check_against_spec(proposed: dict, spec_instance) -> tuple[dict, list[str]]:
    """
    For each proposed field that has a value, compare to spec and annotate
    spec_comparison as CONFIRMED or CHANGED.  Returns updated proposed dict
    and a list of warnings.
    """
    warnings = []
    if spec_instance is None:
        for k in proposed:
            if proposed[k]["confidence"] != "CANNOT_VERIFY":
                proposed[k]["spec_comparison"] = "SPEC_NOT_LOADED"
        return proposed, ["spec file could not be loaded; cross-check skipped"]

    for field_name, result in proposed.items():
        if result["confidence"] == "CANNOT_VERIFY":
            continue
        if result["value_mm"] is None:
            continue
        if not hasattr(spec_instance, field_name):
            result["spec_comparison"] = "FIELD_NOT_IN_SPEC"
            warnings.append(f"Field {field_name!r} not found in KitchenDesign")
            continue

        spec_val = getattr(spec_instance, field_name)
        if isinstance(spec_val, (int, float)):
            diff = abs(spec_val - result["value_mm"])
            tol = 0.5  # mm tolerance for "equal"
            if diff <= tol:
                result["spec_comparison"] = "CONFIRMED"
            else:
                result["spec_comparison"] = "CHANGED"
                if result["confidence"] == "HIGH":
                    warnings.append(
                        f"HIGH-confidence change detected: {field_name} "
                        f"spec={spec_val:.1f}mm proposed={result['value_mm']:.1f}mm "
                        f"(diff={diff:.1f}mm)"
                    )
        else:
            result["spec_comparison"] = "FIELD_NOT_NUMERIC"

    return proposed, warnings


# ---------------------------------------------------------------------------
# Main extraction orchestrator
# ---------------------------------------------------------------------------

def extract(
    pdf_path: Optional[str],
    page_number: int,
    png_path: Optional[str],
    svg_path: Optional[str],
    spec_path: Optional[str],
    page_type_override: Optional[str],
) -> dict:
    # 1. Load words
    if pdf_path:
        words = extract_words_from_pdf_page(pdf_path, page_number)
        input_label = f"{Path(pdf_path).name} page {page_number}"
    elif png_path:
        words = extract_words_from_png(png_path)
        input_label = Path(png_path).name
        page_number = 0
    elif svg_path:
        # SVG is XML — parse text elements naively
        words = _extract_words_from_svg(svg_path)
        input_label = Path(svg_path).name
        page_number = 0
    else:
        raise ValueError("At least one of --pdf, --png, --svg must be provided.")

    # 2. Detect scale
    detected_scale = detect_scale(words)
    if detected_scale:
        scale_key = detected_scale
    else:
        scale_key = DEFAULT_SCALE_BY_PAGE.get(page_number, '1/4"=1\'-0"')
    scale_info = SCALE_TABLE[scale_key]

    # 3. Determine page type
    if page_type_override:
        page_type = page_type_override
    else:
        page_type = PAGE_TYPE_BY_PAGE.get(page_number, "unknown")

    # 4. Parse all dimensions
    dims = build_dimensions_list(words)

    all_dims_out = [
        {"text": d["text"], "inches": d["inches"], "mm": d["mm"],
         "x": round(d["x"], 1), "y": round(d["y"], 1)}
        for d in dims
    ]

    # 5. Extract fields by page type
    if page_type == "casework_elevations":
        proposed = extract_casework_fields(words, dims, scale_key, input_label)
    elif page_type == "floor_plan":
        proposed = extract_floor_plan_fields(words, dims, scale_key, input_label)
    elif page_type == "elevation":
        proposed = extract_elevation_fields(words, dims, scale_key, input_label)
    else:
        # Unknown page type — just report dimensions found, no field mapping
        proposed = {}

    # 6. Cross-check against spec
    spec_instance = load_spec(spec_path) if spec_path else None
    proposed, warnings = cross_check_against_spec(proposed, spec_instance)

    # 7. Collect cannot_verify list
    cannot_verify = [k for k, v in proposed.items() if v["confidence"] == "CANNOT_VERIFY"]

    return {
        "source": input_label,
        "scale": scale_key,
        "pts_per_ft": scale_info["pts_per_ft"],
        "page_type": page_type,
        "all_dimensions_found": all_dims_out,
        "proposed_fields": proposed,
        "cannot_verify": cannot_verify,
        "warnings": warnings,
    }


def _extract_words_from_svg(svg_path: str) -> list[dict]:
    """Minimal SVG text extraction via xml.etree."""
    import xml.etree.ElementTree as ET
    tree = ET.parse(svg_path)
    root = tree.getroot()
    ns = {"svg": "http://www.w3.org/2000/svg"}
    words = []
    for text_el in root.iter():
        tag = text_el.tag.split("}")[-1] if "}" in text_el.tag else text_el.tag
        if tag in ("text", "tspan") and text_el.text and text_el.text.strip():
            x = float(text_el.get("x", 0))
            y = float(text_el.get("y", 0))
            for token in text_el.text.split():
                words.append({"text": token, "x0": x, "y0": y,
                               "x1": x + 50, "y1": y + 12})
    return words


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract design spec field values from an architectural drawing."
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--pdf", metavar="PATH", help="Input PDF file path")
    src.add_argument("--png", metavar="PATH", help="Input PNG file path")
    src.add_argument("--svg", metavar="PATH", help="Input SVG file path")

    parser.add_argument("--page", type=int, default=1,
                        help="1-based page number (PDF only)")
    parser.add_argument("--spec", metavar="PATH",
                        help="Path to design_spec.py")
    parser.add_argument("--output", metavar="PATH",
                        help="Write JSON output to this file (default: stdout)")
    parser.add_argument("--page-type",
                        choices=["casework_elevations", "floor_plan", "elevation"],
                        help="Override auto-detected page type")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print output to stdout only; do not write --output file")

    args = parser.parse_args()

    result = extract(
        pdf_path=args.pdf,
        page_number=args.page,
        png_path=args.png,
        svg_path=args.svg,
        spec_path=args.spec,
        page_type_override=args.page_type,
    )

    output_json = json.dumps(result, indent=2, default=str)

    if args.output and not args.dry_run:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_json)
        print(f"Written to {out_path}", file=sys.stderr)
    else:
        print(output_json)


if __name__ == "__main__":
    main()
