#!/usr/bin/env python3
"""
constraint_simulator.py — Pre-edit safety check for design:modify

Reads design_spec.py and prints all 4 aisle clearances plus work triangle
perimeter. Use this before any spec edit to confirm the current state and
to validate that a proposed change stays within feasible bounds.

Usage:
    python3 constraint_simulator.py
    python3 constraint_simulator.py --propose bar_y_offset_mm=1092.2

All formulas use explicit / 25.4 for mm-to-inch conversion.

Ground-truth anchors (verified 2026-05-10 against extract_clearances.py):
    south_aisle_in = 30.0"  (bar_y_offset_mm=762.0)
    north_aisle_in = 55.0"  (bar_y_offset_mm=762.0)
    east_aisle_in  = 46.5"  (island centered EW)
    west_aisle_in  = 46.5"  (island centered EW)
"""
import sys
import argparse

# Allow running from any cwd — add project dir to path
PROJECT_DIR = '/home/tstapler/Documents/711-N60th-Plans'
sys.path.insert(0, PROJECT_DIR)

from design_spec import SPEC


def compute_aisles(bar_y_offset_mm: float, spec=None) -> dict:
    """
    Compute all four aisle clearances for a given bar_y_offset_mm.

    All intermediate values are in mm. Final values are in inches (/ 25.4).

    Args:
        bar_y_offset_mm: proposed or current bar_y_offset_mm value (mm)
        spec: SPEC object to read other fields from (defaults to global SPEC)

    Returns:
        dict with keys:
            south_aisle_in, north_aisle_in, east_aisle_in, west_aisle_in,
            BAR_Y_mm, ISLAND_Y_mm, ISLAND_TOP_Y_mm, ISLAND_X_mm,
            KI_S_mm, KI_N_mm, KI_W_mm, KI_E_mm
    """
    if spec is None:
        spec = SPEC

    # Kitchen interior corners (mm)
    KI_W = spec.kit_w_out_mm + spec.ext_thk_mm
    KI_S = spec.kit_s_out_mm + spec.ext_thk_mm
    KI_N = KI_S + spec.kit_ns_mm
    KI_E = KI_W + spec.kit_ew_mm

    # Island east-west position: centered in kitchen (mirrors kitchen_permit_docs.py)
    ISLAND_X = KI_W + (spec.kit_ew_mm - spec.island_ew_mm) / 2.0

    # Island north-south position (Y increases southward in SVG = northward in plan)
    BAR_Y        = KI_S + bar_y_offset_mm
    ISLAND_Y     = BAR_Y + spec.bar_ns_mm        # island body south face
    ISLAND_TOP_Y = ISLAND_Y + spec.island_ns_mm  # island body north face

    # Aisle clearances (inches = mm / 25.4)
    # south_aisle: bar south face to south interior wall
    south_aisle_in = (BAR_Y - KI_S) / 25.4
    # = bar_y_offset_mm / 25.4  (simplified, since BAR_Y - KI_S == bar_y_offset_mm)

    # north_aisle: island north face to north interior wall
    # CRITICAL: measured from ISLAND_TOP_Y (north face of island body), not BAR_TOP
    north_aisle_in = (KI_N - ISLAND_TOP_Y) / 25.4

    # east_aisle: island east face to east interior wall
    east_aisle_in = (KI_E - (ISLAND_X + spec.island_ew_mm)) / 25.4

    # west_aisle: island west face to west interior wall
    west_aisle_in = (ISLAND_X - KI_W) / 25.4

    return {
        'south_aisle_in': south_aisle_in,
        'north_aisle_in': north_aisle_in,
        'east_aisle_in':  east_aisle_in,
        'west_aisle_in':  west_aisle_in,
        'BAR_Y_mm':        BAR_Y,
        'ISLAND_Y_mm':     ISLAND_Y,
        'ISLAND_TOP_Y_mm': ISLAND_TOP_Y,
        'ISLAND_X_mm':     ISLAND_X,
        'KI_S_mm':         KI_S,
        'KI_N_mm':         KI_N,
        'KI_W_mm':         KI_W,
        'KI_E_mm':         KI_E,
    }


def compute_work_triangle(spec=None) -> float:
    """
    Compute work triangle perimeter (ft) from sink, range, and fridge positions.

    The work triangle connects: sink (north wall), range (island center), fridge (NE).
    Returns perimeter in feet. Compliance target: <= 26 ft (NKBA G4).

    Note: positions are approximations derived from SPEC dimensional fields.
    For authoritative measurement use extract_clearances.py Layer 1 output.
    """
    if spec is None:
        spec = SPEC

    KI_W = spec.kit_w_out_mm + spec.ext_thk_mm
    KI_S = spec.kit_s_out_mm + spec.ext_thk_mm
    KI_N = KI_S + spec.kit_ns_mm
    KI_E = KI_W + spec.kit_ew_mm

    ISLAND_X = KI_W + (spec.kit_ew_mm - spec.island_ew_mm) / 2.0
    BAR_Y = KI_S + spec.bar_y_offset_mm
    ISLAND_Y = BAR_Y + spec.bar_ns_mm

    # Sink: centered on north wall (approximate — exact position is in kitchen_permit_docs.py)
    sink_x_mm = KI_W + spec.kit_ew_mm / 2.0
    sink_y_mm = KI_N - spec.sink_d_mm / 2.0  # depth from north wall

    # Range: centered on island (island center)
    range_x_mm = ISLAND_X + spec.island_ew_mm / 2.0
    range_y_mm = ISLAND_Y + spec.island_ns_mm / 2.0

    # Fridge: northeast quadrant (approximate — east wall, near north)
    fridge_x_mm = KI_E - spec.fridge_w_mm / 2.0
    fridge_y_mm = KI_N - spec.fridge_d_mm / 2.0

    def dist_mm(p1, p2):
        return ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2) ** 0.5

    sink  = (sink_x_mm,  sink_y_mm)
    range_ = (range_x_mm, range_y_mm)
    fridge = (fridge_x_mm, fridge_y_mm)

    perimeter_mm = dist_mm(sink, range_) + dist_mm(range_, fridge) + dist_mm(fridge, sink)
    perimeter_ft = perimeter_mm / 25.4 / 12.0
    return perimeter_ft


def check_against_targets(aisles: dict, spec=None) -> list:
    """
    Compare aisle clearances against SPEC.compliance_targets.

    Returns list of dicts with keys: id, measured_in, required_in, result.
    """
    if spec is None:
        spec = SPEC

    t = spec.compliance_targets
    results = []

    checks = [
        ('island_south_aisle', 'south_aisle_in', t['min_south_aisle_in']),
        ('island_north_aisle', 'north_aisle_in', t['min_north_aisle_in']),
        ('island_east_aisle',  'east_aisle_in',  t['min_east_aisle_in']),
        ('island_west_aisle',  'west_aisle_in',  t['min_west_aisle_in']),
    ]

    for check_id, key, required in checks:
        measured = aisles[key]
        result = 'PASS' if round(measured, 4) >= required else 'FAIL'
        results.append({
            'id': check_id,
            'measured_in': round(measured, 2),
            'required_in': required,
            'result': result,
        })

    return results


def compute_feasible_range(spec=None) -> dict:
    """
    Compute the feasible range for bar_y_offset_mm that satisfies:
    - south aisle >= min_south_aisle_in
    - north aisle >= min_north_aisle_in

    Returns dict with min_mm, max_mm, preferred_mm.
    """
    if spec is None:
        spec = SPEC

    KI_S = spec.kit_s_out_mm + spec.ext_thk_mm
    KI_N = KI_S + spec.kit_ns_mm

    t = spec.compliance_targets

    # Minimum bar_y_offset_mm to satisfy south aisle minimum
    min_mm = t['min_south_aisle_in'] * 25.4  # 42 * 25.4 = 1066.8

    # Preferred bar_y_offset_mm for preferred south aisle
    pref_south_in = t.get('preferred_south_aisle_in', t['min_south_aisle_in'])
    pref_mm = pref_south_in * 25.4

    # Maximum bar_y_offset_mm before north aisle drops below minimum
    # KI_N - (KI_S + bar_y + bar_ns + island_ns) >= min_north_aisle_in * 25.4
    # bar_y <= KI_N - KI_S - bar_ns - island_ns - min_north_aisle_in * 25.4
    max_mm = (KI_N - KI_S
              - spec.bar_ns_mm
              - spec.island_ns_mm
              - t['min_north_aisle_in'] * 25.4)

    # Target: preferred if feasible, else maximum feasible
    if pref_mm <= max_mm:
        target_mm = pref_mm
    elif min_mm <= max_mm:
        target_mm = max_mm
    else:
        target_mm = None  # no feasible value — human intervention required

    return {
        'min_mm': round(min_mm, 1),
        'max_mm': round(max_mm, 1),
        'preferred_mm': round(pref_mm, 1),
        'target_mm': round(target_mm, 1) if target_mm is not None else None,
        'feasible': target_mm is not None,
    }


def print_simulation_table(current: dict, proposed: dict, targets: list,
                           proposed_targets: list, bar_y_current: float,
                           bar_y_proposed: float) -> None:
    """Print a formatted simulation table to stdout."""
    print()
    print(f"Constraint Simulation — bar_y_offset_mm: {bar_y_current} → {bar_y_proposed} mm")
    print()
    print(f"{'Aisle':<16} {'Current':>10} {'Proposed':>10} {'Required':>10} {'Status':>8}")
    print("-" * 58)

    aisle_labels = {
        'island_south_aisle': 'South aisle',
        'island_north_aisle': 'North aisle',
        'island_east_aisle':  'East aisle',
        'island_west_aisle':  'West aisle',
    }

    current_map  = {r['id']: r for r in targets}
    proposed_map = {r['id']: r for r in proposed_targets}

    for check_id, label in aisle_labels.items():
        c = current_map.get(check_id, {})
        p = proposed_map.get(check_id, {})
        c_val = f"{c.get('measured_in', 0):.1f}\""
        p_val = f"{p.get('measured_in', 0):.1f}\""
        req   = f"≥ {c.get('required_in', '?')}\""
        status = p.get('result', '?')
        symbol = '✅' if status == 'PASS' else '❌'
        print(f"{label:<16} {c_val:>10} {p_val:>10} {req:>10} {symbol} {status:>6}")

    print()


def main():
    parser = argparse.ArgumentParser(
        description='Simulate aisle clearances before a design_spec.py edit.')
    parser.add_argument('--propose', metavar='FIELD=VALUE',
                        help='Proposed change, e.g. bar_y_offset_mm=1092.2')
    parser.add_argument('--project-dir', default=PROJECT_DIR,
                        help='Path to project directory containing design_spec.py')
    args = parser.parse_args()

    # Ensure we can import SPEC from the right directory
    if args.project_dir != PROJECT_DIR:
        sys.path.insert(0, args.project_dir)
        import importlib
        ds = importlib.import_module('design_spec')
        spec = ds.SPEC
    else:
        spec = SPEC

    print(f"Reading design_spec.py from: {args.project_dir}")
    print(f"  bar_y_offset_mm = {spec.bar_y_offset_mm}")
    print(f"  kit_ns_mm       = {spec.kit_ns_mm}")
    print(f"  bar_ns_mm       = {spec.bar_ns_mm}")
    print(f"  island_ns_mm    = {spec.island_ns_mm}")

    # Current state
    current_aisles = compute_aisles(spec.bar_y_offset_mm, spec)
    current_checks = check_against_targets(current_aisles, spec)
    work_triangle_ft = compute_work_triangle(spec)

    print()
    print("=" * 58)
    print("CURRENT STATE")
    print("=" * 58)
    print(f"{'Aisle':<20} {'Measured':>10} {'Required':>10} {'Status':>8}")
    print("-" * 50)
    for chk in current_checks:
        sym = '✅' if chk['result'] == 'PASS' else '❌'
        print(f"{chk['id']:<20} {chk['measured_in']:>9.1f}\" {chk['required_in']:>9}\"  {sym} {chk['result']}")

    wt_req = spec.compliance_targets.get('max_work_triangle_ft', 26)
    wt_sym = '✅' if work_triangle_ft <= wt_req else '❌'
    wt_res = 'PASS' if work_triangle_ft <= wt_req else 'FAIL'
    print(f"{'work_triangle':<20} {work_triangle_ft:>9.1f} ft {wt_req:>8} ft  {wt_sym} {wt_res}")
    print()

    # Feasible range for bar_y_offset_mm
    feasible = compute_feasible_range(spec)
    print("Feasible range for bar_y_offset_mm:")
    print(f"  min (south aisle = 42\"): {feasible['min_mm']} mm")
    print(f"  max (north aisle = 42\"): {feasible['max_mm']} mm")
    print(f"  preferred target:         {feasible['target_mm']} mm")
    if not feasible['feasible']:
        print("  !! NO FEASIBLE VALUE — human intervention required !!")
    print()

    # Proposed change
    if args.propose:
        field, value_str = args.propose.split('=', 1)
        field = field.strip()
        value = float(value_str.strip())

        if field != 'bar_y_offset_mm':
            print(f"NOTE: constraint simulation only handles bar_y_offset_mm changes.")
            print(f"For field '{field}', run extract_clearances.py after editing to verify.")
            return

        proposed_aisles  = compute_aisles(value, spec)
        proposed_checks  = check_against_targets(proposed_aisles, spec)

        print("=" * 58)
        print(f"PROPOSED CHANGE: bar_y_offset_mm = {spec.bar_y_offset_mm} → {value}")
        print("=" * 58)

        print_simulation_table(
            current_aisles, proposed_aisles,
            current_checks, proposed_checks,
            spec.bar_y_offset_mm, value
        )

        # Feasibility verdict
        any_fail_in_proposed = any(c['result'] == 'FAIL' for c in proposed_checks)
        any_regression = any(
            p['result'] == 'FAIL' and c['result'] == 'PASS'
            for c, p in zip(current_checks, proposed_checks)
        )

        if any_regression:
            print("❌ REJECTED: proposed change introduces a new FAIL.")
            print("   Aisles that would regress:")
            for c, p in zip(current_checks, proposed_checks):
                if p['result'] == 'FAIL' and c['result'] == 'PASS':
                    print(f"   - {c['id']}: {c['measured_in']:.1f}\" → {p['measured_in']:.1f}\" (below {c['required_in']}\")")
            print()
            print("   Do NOT apply this change. Adjust to within feasible range:")
            print(f"   bar_y_offset_mm must be between {feasible['min_mm']} and {feasible['max_mm']} mm")
            sys.exit(1)
        elif any_fail_in_proposed:
            print("❌ REJECTED: proposed change does not resolve the existing FAIL.")
            sys.exit(1)
        else:
            print("✅ FEASIBLE: all aisles pass with proposed value.")
            print(f"   Proceed with: bar_y_offset_mm = {value} mm")
            sys.exit(0)
    else:
        print("(Pass --propose FIELD=VALUE to simulate a proposed change)")


if __name__ == '__main__':
    main()
