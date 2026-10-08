from scipy.optimize import linprog
import numpy as np


def optimize(facilities, wet_total, dry_total, use_lp=True):
    """
    Allocate waste streams to compatible facilities.
    Uses linear programming if scipy is available, otherwise greedy fallback.
    Returns: (allocations dict, overflow dict)
    """
    if use_lp:
        try:
            return _optimize_lp(facilities, wet_total, dry_total)
        except Exception:
            return _optimize_greedy(facilities, wet_total, dry_total)
    return _optimize_greedy(facilities, wet_total, dry_total)


def _optimize_lp(facilities, wet_total, dry_total):
    """LP: minimize (unprocessed waste + 0.1 * transport_km * kg_allocated)."""
    streams = [("wet", wet_total), ("dry", dry_total)]
    # Variables: x[f_idx] for each (facility, stream) pair. Plus overflow per stream.
    pairs = []  # (facility_index, stream)
    for fi, f in enumerate(facilities):
        for stream, total in streams:
            if f["accepts"] == stream:
                pairs.append((fi, stream))

    n_alloc = len(pairs)
    n_overflow = len(streams)
    n_vars = n_alloc + n_overflow

    # Objective: overflow penalty (1000x) + distance cost
    c = np.zeros(n_vars)
    for i, (fi, _) in enumerate(pairs):
        c[i] = facilities[fi]["distance_km"] * 0.1
    for k in range(n_overflow):
        c[n_alloc + k] = 1000  # heavy penalty for overflow

    # Constraints:
    # 1. For each stream: sum of allocations to compatible facilities + overflow = total
    A_eq = []
    b_eq = []
    for k, (stream, total) in enumerate(streams):
        row = np.zeros(n_vars)
        for i, (_, s) in enumerate(pairs):
            if s == stream:
                row[i] = 1
        row[n_alloc + k] = 1
        A_eq.append(row)
        b_eq.append(total)

    # 2. Facility capacity: sum of allocations to facility <= capacity
    A_ub = []
    b_ub = []
    for fi, f in enumerate(facilities):
        row = np.zeros(n_vars)
        for i, (fac_idx, _) in enumerate(pairs):
            if fac_idx == fi:
                row[i] = 1
        A_ub.append(row)
        b_ub.append(f["capacity_kg"] - f["current_load_kg"])

    bounds = [(0, None)] * n_vars

    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")

    if not res.success:
        return _optimize_greedy(facilities, wet_total, dry_total)

    allocations = {f["id"]: 0 for f in facilities}
    for i, (fi, _) in enumerate(pairs):
        allocations[facilities[fi]["id"]] += res.x[i]

    overflow = {}
    for k, (stream, _) in enumerate(streams):
        ovf = res.x[n_alloc + k]
        if ovf > 0.1:
            overflow[stream] = ovf

    return allocations, overflow


def _optimize_greedy(facilities, wet_total, dry_total):
    allocations = {f["id"]: 0 for f in facilities}
    overflow = {}
    for wtype, total in [("wet", wet_total), ("dry", dry_total)]:
        compat = sorted([f for f in facilities if f["accepts"] == wtype],
                        key=lambda f: f["distance_km"])
        remaining = total
        for f in compat:
            avail = f["capacity_kg"] - f["current_load_kg"]
            if avail <= 0:
                continue
            alloc = min(remaining, avail)
            allocations[f["id"]] += alloc
            remaining -= alloc
            if remaining <= 0:
                break
        if remaining > 0:
            overflow[wtype] = remaining
    return allocations, overflow


def total_overflow(overflow):
    return sum(overflow.values())


def fixed_allocation_overflow(total_waste, total_capacity):
    return max(0, total_waste - total_capacity)


def reduction_pct(fixed_overflow, optimized_overflow):
    if fixed_overflow <= 0:
        return 0.0
    return (fixed_overflow - optimized_overflow) / fixed_overflow * 100