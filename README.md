# ♻️ WasteGrid

**Predict. Detect. Reallocate.**
Dynamic Reallocation of Urban Waste-Processing Capacity.

## What it does

WasteGrid predicts changing waste generation, detects capacity shortfalls before they happen, and dynamically reallocates waste across compatible processing facilities.

Unlike collection-route optimization, WasteGrid addresses the **downstream allocation problem**: where the waste stream goes when facility capacity and waste-type compatibility are constrained.

## Live Demo

🔗 [wastegrid.streamlit.app](https://wastegrid.streamlit.app) *(update after deploy)*

## Features

- Multi-source waste prediction (household, office, restaurant, college, event)
- Waste classification: wet / dry / recyclable
- Constrained optimization across facilities
- Dynamic reallocation on demand spikes
- Fixed vs WasteGrid baseline comparison
- CSV upload for custom data
- Light / dark theme

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py