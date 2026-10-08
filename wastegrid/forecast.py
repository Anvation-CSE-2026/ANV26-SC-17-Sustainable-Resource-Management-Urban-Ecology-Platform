DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Day-of-week multipliers per source
DOW_MODIFIERS = {
    "household":  [1.0, 1.0, 1.0, 1.0, 1.0, 1.15, 1.2],
    "office":     [1.1, 1.1, 1.1, 1.1, 1.0, 0.3, 0.2],
    "restaurant": [0.9, 0.9, 1.0, 1.0, 1.3, 1.5, 1.4],
    "college":    [1.1, 1.1, 1.1, 1.1, 1.0, 0.4, 0.3],
    "event":      [0.8, 0.8, 0.9, 1.0, 1.3, 1.6, 1.5],
}


def forecast_week(sources, total_capacity):
    """Return list of {day, predicted_kg, capacity_kg, overflow_kg}."""
    rows = []
    for i, day in enumerate(DAY_NAMES):
        total = 0
        for s in sources:
            base = s["baseline_kg"] * s.get("modifier", 1.0)
            dow = DOW_MODIFIERS.get(s["id"], [1.0] * 7)[i]
            total += base * dow
        overflow = max(0, total - total_capacity)
        rows.append({
            "Day": day,
            "Predicted (T)": round(total / 1000, 2),
            "Capacity (T)": round(total_capacity / 1000, 2),
            "Overflow (T)": round(overflow / 1000, 2),
        })
    return rows