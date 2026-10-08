def optimize(facilities, wet_total, dry_total):
    """
    Greedy allocation: match each waste stream to the nearest compatible
    facility with available capacity.

    Returns:
        allocations: dict {facility_id: kg_allocated}
        overflow:    dict {waste_type: kg_unprocessed}
    """
    allocations = {f["id"]: 0 for f in facilities}
    overflow = {}

    for wtype, total in [("wet", wet_total), ("dry", dry_total)]:
        compat = sorted(
            [f for f in facilities if f["accepts"] == wtype],
            key=lambda f: f["distance_km"],
        )
        remaining = total
        for f in compat:
            available = f["capacity_kg"] - f["current_load_kg"]
            if available <= 0:
                continue
            alloc = min(remaining, available)
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
    """What a naive fixed allocation would overflow."""
    return max(0, total_waste - total_capacity)


def reduction_pct(fixed_overflow, optimized_overflow):
    """Percent reduction of optimized vs fixed. 0 if nothing to reduce."""
    if fixed_overflow <= 0:
        return 0.0
    return (fixed_overflow - optimized_overflow) / fixed_overflow * 100