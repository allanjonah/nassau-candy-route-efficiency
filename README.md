# Nassau Candy — Route Efficiency Dashboard

## Setup
```bash
pip install -r requirements.txt
streamlit run app.py
```

Keep all the CSV/JSON files in this folder next to `app.py` — the app loads them directly (no database needed).

## Files
- `app.py` — the dashboard (4 modules: Route Efficiency Overview, Geographic Shipping Map, Ship Mode Comparison, Route Drill-Down)
- `cleaned_orders.csv` — full cleaned, feature-engineered order-level dataset
- `route_aggregation.csv`, `top10_routes.csv`, `bottom10_routes.csv` — route-level rollups
- `shipmode_performance.csv`, `region_bottlenecks.csv`, `state_bottlenecks.csv` — performance breakdowns
- `summary_kpis.json` — headline KPIs

## Filters available in the app
- Order date range
- Region / State selector
- Ship mode filter
- Lead-time delay threshold (percentile slider, 50th-95th)

## Deploying (optional)
Push this folder to a GitHub repo and deploy free via [Streamlit Community Cloud](https://share.streamlit.io) — point it at `app.py`.
