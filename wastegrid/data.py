import pandas as pd

SAMPLE_SOURCES = [
    {"id": "household",  "baseline_kg": 2000, "waste_type": "wet", "modifier": 1.0},
    {"id": "office",     "baseline_kg": 800,  "waste_type": "dry", "modifier": 1.0},
    {"id": "restaurant", "baseline_kg": 1500, "waste_type": "wet", "modifier": 1.2},
    {"id": "college",    "baseline_kg": 600,  "waste_type": "dry", "modifier": 1.0},
    {"id": "event",      "baseline_kg": 0,    "waste_type": "wet", "modifier": 1.0},
]

FACILITIES = [
    {"id": "A", "accepts": "wet", "capacity_kg": 3000, "current_load_kg": 0, "distance_km": 5},
    {"id": "B", "accepts": "wet", "capacity_kg": 1500, "current_load_kg": 0, "distance_km": 8},
    {"id": "C", "accepts": "dry", "capacity_kg": 2500, "current_load_kg": 0, "distance_km": 6},
]

EVENT_SPIKE_KG = 4000


def load_sources_from_csv(uploaded_file):
    """Parse an uploaded CSV into the internal source format."""
    df = pd.read_csv(uploaded_file)
    sources = []
    for _, row in df.iterrows():
        sources.append({
            "id": str(row["source"]).strip(),
            "baseline_kg": float(row["baseline_kg"]),
            "waste_type": str(row["waste_type"]).strip().lower(),
            "modifier": 1.0,
        })
    return sources


def apply_event_state(sources, event_active):
    """If an event is active, inject the spike into the event source."""
    out = []
    for s in sources:
        s = dict(s)
        if s["id"] == "event" and event_active:
            s["baseline_kg"] = EVENT_SPIKE_KG
        out.append(s)
    return out


def totals(sources):
    """Compute wet, dry, and total waste from the source list."""
    wet = sum(s["baseline_kg"] * s["modifier"] for s in sources if s["waste_type"] == "wet")
    dry = sum(s["baseline_kg"] * s["modifier"] for s in sources if s["waste_type"] == "dry")
    return wet, dry, wet + dry