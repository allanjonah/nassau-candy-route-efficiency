"""
Nassau Candy Distributor — Factory-to-Customer Shipping Route Efficiency Dashboard
Run locally with:  streamlit run app.py
Requires the CSVs produced by the companion analysis notebook to sit next to this file:
    cleaned_orders.csv, route_aggregation.csv, top10_routes.csv, bottom10_routes.csv,
    shipmode_performance.csv, region_bottlenecks.csv, state_bottlenecks.csv, summary_kpis.json
"""

import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Nassau Candy | Route Efficiency", layout="wide", page_icon="🚚")

# ---------------------------------------------------------------------------
# DATA LOAD
# ---------------------------------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("cleaned_orders.csv", parse_dates=["Order Date", "Ship Date"])
    with open("summary_kpis.json") as f:
        summary = json.load(f)
    return df, summary

df, summary = load_data()

US_STATE_ABBR = {
    'Alabama':'AL','Alaska':'AK','Arizona':'AZ','Arkansas':'AR','California':'CA','Colorado':'CO',
    'Connecticut':'CT','Delaware':'DE','District of Columbia':'DC','Florida':'FL','Georgia':'GA',
    'Idaho':'ID','Illinois':'IL','Indiana':'IN','Iowa':'IA','Kansas':'KS','Kentucky':'KY',
    'Louisiana':'LA','Maine':'ME','Maryland':'MD','Massachusetts':'MA','Michigan':'MI',
    'Minnesota':'MN','Mississippi':'MS','Missouri':'MO','Montana':'MT','Nebraska':'NE',
    'Nevada':'NV','New Hampshire':'NH','New Jersey':'NJ','New Mexico':'NM','New York':'NY',
    'North Carolina':'NC','North Dakota':'ND','Ohio':'OH','Oklahoma':'OK','Oregon':'OR',
    'Pennsylvania':'PA','Rhode Island':'RI','South Carolina':'SC','South Dakota':'SD',
    'Tennessee':'TN','Texas':'TX','Utah':'UT','Vermont':'VT','Virginia':'VA','Washington':'WA',
    'West Virginia':'WV','Wisconsin':'WI','Wyoming':'WY',
}

# ---------------------------------------------------------------------------
# SIDEBAR — FILTERS  (Date range, Region/State, Ship Mode, Lead-time threshold)
# ---------------------------------------------------------------------------
st.sidebar.title("🍬 Nassau Candy")
st.sidebar.caption("Factory-to-Customer Shipping Route Efficiency")
st.sidebar.divider()
st.sidebar.header("Filters")

min_date, max_date = df["Order Date"].min().date(), df["Order Date"].max().date()
date_range = st.sidebar.date_input("Order date range", value=(min_date, max_date),
                                    min_value=min_date, max_value=max_date)

regions = sorted(df["Region"].unique().tolist())
sel_regions = st.sidebar.multiselect("Region", regions, default=regions)

states_in_region = sorted(df[df["Region"].isin(sel_regions)]["State/Province"].unique().tolist())
sel_states = st.sidebar.multiselect("State / Province", states_in_region, default=states_in_region)

ship_modes = sorted(df["Ship Mode"].unique().tolist())
sel_modes = st.sidebar.multiselect("Ship Mode", ship_modes, default=ship_modes)

st.sidebar.subheader("Delay threshold")
pct = st.sidebar.slider(
    "Flag shipments slower than this percentile as 'delayed'",
    min_value=50, max_value=95, value=75, step=5,
    help="Because raw lead-time days are inflated by a dataset-wide date logging "
         "issue (see notebook / report), delay is defined relative to the dataset's "
         "own distribution rather than a fixed day count."
)

st.sidebar.divider()
with st.sidebar.expander("⚠️ Data quality note"):
    st.write(
        "Every record's `Ship Date` falls 2-5 years after its `Order Date` — a "
        "systemic logging issue in the source data, not a handful of bad rows. "
        "Since it affects the whole dataset equally, relative comparisons between "
        "routes/regions/ship modes (what this dashboard shows) remain valid, but "
        "raw day counts should not be read as real-world shipping times."
    )

# ---------------------------------------------------------------------------
# APPLY FILTERS
# ---------------------------------------------------------------------------
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_d, end_d = date_range
else:
    start_d, end_d = min_date, max_date

mask = (
    (df["Order Date"].dt.date >= start_d) & (df["Order Date"].dt.date <= end_d) &
    (df["Region"].isin(sel_regions)) &
    (df["State/Province"].isin(sel_states)) &
    (df["Ship Mode"].isin(sel_modes))
)
fdf = df.loc[mask].copy()

if fdf.empty:
    st.warning("No shipments match the current filters. Widen your selection in the sidebar.")
    st.stop()

delay_threshold_days = fdf["Lead Time (Days)"].quantile(pct / 100)
fdf["Is Delayed (filtered)"] = fdf["Lead Time (Days)"] > delay_threshold_days

# ---------------------------------------------------------------------------
# HEADER KPIs
# ---------------------------------------------------------------------------
st.title("🚚 Factory-to-Customer Shipping Route Efficiency")
st.caption("Nassau Candy Distributor — logistics intelligence dashboard")

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Shipments (filtered)", f"{len(fdf):,}")
k2.metric("Avg Lead Time", f"{fdf['Lead Time (Days)'].mean():,.1f} days")
k3.metric("Delay Rate", f"{fdf['Is Delayed (filtered)'].mean()*100:,.1f}%")
k4.metric("Active Routes", f"{fdf['Route (State)'].nunique():,}")
k5.metric("Total Sales", f"${fdf['Sales'].sum():,.0f}")

st.divider()

# ---------------------------------------------------------------------------
# TABS = Dashboard modules
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Route Efficiency Overview",
    "🗺️ Geographic Shipping Map",
    "📦 Ship Mode Comparison",
    "🔎 Route Drill-Down",
])

# ============================ TAB 1: ROUTE EFFICIENCY OVERVIEW =============
with tab1:
    st.subheader("Average Lead Time by Route")

    route_perf = fdf.groupby(["Factory", "State/Province", "Route (State)"], as_index=False).agg(
        Total_Shipments=("Order ID", "count"),
        Avg_Lead_Time=("Lead Time (Days)", "mean"),
        Delay_Rate=("Is Delayed (filtered)", "mean"),
    )
    route_perf["Avg_Lead_Time"] = route_perf["Avg_Lead_Time"].round(2)
    route_perf["Delay_Rate"] = (route_perf["Delay_Rate"] * 100).round(1)

    min_vol = int(route_perf["Total_Shipments"].median()) if len(route_perf) else 1
    vol_filter = st.checkbox(
        f"Leaderboard: only show routes with ≥ {min_vol} shipments (recommended — "
        f"excludes 1-2 order routes that skew averages)", value=True
    )
    pool = route_perf[route_perf["Total_Shipments"] >= min_vol] if vol_filter else route_perf

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**🏆 Top 10 Most Efficient Routes**")
        top10 = pool.nsmallest(10, "Avg_Lead_Time")
        fig = px.bar(top10.sort_values("Avg_Lead_Time"), x="Avg_Lead_Time", y="Route (State)",
                     orientation="h", color_discrete_sequence=["#2E7D32"])
        fig.update_layout(yaxis_title="", xaxis_title="Avg Lead Time (days)", height=420)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown("**🐢 Bottom 10 Least Efficient Routes**")
        bottom10 = pool.nlargest(10, "Avg_Lead_Time")
        fig = px.bar(bottom10.sort_values("Avg_Lead_Time"), x="Avg_Lead_Time", y="Route (State)",
                     orientation="h", color_discrete_sequence=["#C62828"])
        fig.update_layout(yaxis_title="", xaxis_title="Avg Lead Time (days)", height=420)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Route Performance Leaderboard**")
    st.dataframe(
        pool.sort_values("Avg_Lead_Time").rename(columns={
            "Route (State)": "Route", "Total_Shipments": "Shipments",
            "Avg_Lead_Time": "Avg Lead Time (days)", "Delay_Rate": "Delay Rate (%)",
        }),
        use_container_width=True, height=320,
    )

# ============================ TAB 2: GEOGRAPHIC SHIPPING MAP ================
with tab2:
    st.subheader("US Shipping Efficiency Heatmap")

    us_only = fdf[fdf["Country/Region"] == "United States"].copy()
    if us_only.empty:
        st.info("No US shipments in the current filter selection.")
    else:
        state_perf = us_only.groupby("State/Province", as_index=False).agg(
            Avg_Lead_Time=("Lead Time (Days)", "mean"),
            Total_Shipments=("Order ID", "count"),
            Delay_Rate=("Is Delayed (filtered)", "mean"),
        )
        state_perf["Abbr"] = state_perf["State/Province"].map(US_STATE_ABBR)
        state_perf["Avg_Lead_Time"] = state_perf["Avg_Lead_Time"].round(2)
        state_perf["Delay_Rate"] = (state_perf["Delay_Rate"] * 100).round(1)
        state_perf = state_perf.dropna(subset=["Abbr"])

        fig = px.choropleth(
            state_perf, locations="Abbr", locationmode="USA-states",
            color="Avg_Lead_Time", scope="usa",
            color_continuous_scale="RdYlGn_r",
            hover_name="State/Province",
            hover_data={"Abbr": False, "Total_Shipments": True, "Delay_Rate": True},
            labels={"Avg_Lead_Time": "Avg Lead Time (days)", "Delay_Rate": "Delay Rate (%)"},
        )
        fig.update_layout(height=500, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Redder = higher average lead time (relatively slower). Canadian provinces are excluded "
                    "from the map (no US FIPS/abbreviation) but included in all tables and other charts.")

        st.markdown("**Regional Bottleneck Visualization** — volume vs. lead time by region")
        region_perf = fdf.groupby("Region", as_index=False).agg(
            Total_Shipments=("Order ID", "count"),
            Avg_Lead_Time=("Lead Time (Days)", "mean"),
            Delay_Rate=("Is Delayed (filtered)", "mean"),
        )
        region_perf["Delay_Rate"] = (region_perf["Delay_Rate"] * 100).round(1)
        fig2 = px.scatter(
            region_perf, x="Total_Shipments", y="Avg_Lead_Time", size="Delay_Rate",
            color="Region", text="Region", size_max=50,
        )
        fig2.update_traces(textposition="top center")
        fig2.update_layout(height=420, xaxis_title="Total Shipments (Volume)",
                            yaxis_title="Avg Lead Time (days)")
        st.plotly_chart(fig2, use_container_width=True)

# ============================ TAB 3: SHIP MODE COMPARISON ===================
with tab3:
    st.subheader("Ship Mode Performance")

    sm = fdf.groupby("Ship Mode", as_index=False).agg(
        Total_Shipments=("Order ID", "count"),
        Avg_Lead_Time=("Lead Time (Days)", "mean"),
        Delay_Rate=("Is Delayed (filtered)", "mean"),
        Total_Sales=("Sales", "sum"),
        Avg_Gross_Profit=("Gross Profit", "mean"),
    ).round(2).sort_values("Avg_Lead_Time")
    sm["Delay_Rate"] = (sm["Delay_Rate"] * 100).round(1)

    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(sm, x="Ship Mode", y="Avg_Lead_Time", color="Ship Mode",
                     title="Avg Lead Time by Ship Mode")
        fig.update_layout(showlegend=False, height=380)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.box(fdf, x="Ship Mode", y="Lead Time (Days)", color="Ship Mode",
                     title="Lead Time Distribution by Ship Mode")
        fig.update_layout(showlegend=False, height=380)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Cost–Time Tradeoff** (descriptive)")
    fig = go.Figure()
    fig.add_bar(x=sm["Ship Mode"], y=sm["Avg_Lead_Time"], name="Avg Lead Time (days)",
                marker_color="#5B4B8A", yaxis="y1")
    fig.add_trace(go.Scatter(x=sm["Ship Mode"], y=sm["Avg_Gross_Profit"], name="Avg Gross Profit ($)",
                              mode="lines+markers", marker_color="#F5A623", yaxis="y2"))
    fig.update_layout(
        yaxis=dict(title="Avg Lead Time (days)"),
        yaxis2=dict(title="Avg Gross Profit ($)", overlaying="y", side="right"),
        height=400, legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(sm.rename(columns={"Delay_Rate": "Delay Rate (%)"}), use_container_width=True)

# ============================ TAB 4: ROUTE DRILL-DOWN ========================
with tab4:
    st.subheader("State-Level Performance Insights")

    drill_state = st.selectbox("Choose a state / province to inspect", sorted(fdf["State/Province"].unique()))
    sdf = fdf[fdf["State/Province"] == drill_state]

    c1, c2, c3 = st.columns(3)
    c1.metric("Shipments", f"{len(sdf):,}")
    c2.metric("Avg Lead Time", f"{sdf['Lead Time (Days)'].mean():,.1f} days")
    c3.metric("Delay Rate", f"{sdf['Is Delayed (filtered)'].mean()*100:,.1f}%")

    c1, c2 = st.columns(2)
    with c1:
        by_factory = sdf.groupby("Factory", as_index=False)["Lead Time (Days)"].mean().round(2)
        fig = px.bar(by_factory, x="Factory", y="Lead Time (Days)", title=f"Avg Lead Time by Factory — {drill_state}")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        by_mode = sdf.groupby("Ship Mode", as_index=False)["Lead Time (Days)"].mean().round(2)
        fig = px.bar(by_mode, x="Ship Mode", y="Lead Time (Days)", title=f"Avg Lead Time by Ship Mode — {drill_state}")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown(f"**Order-Level Shipment Timeline — {drill_state}**")
    timeline = sdf.sort_values("Order Date")[
        ["Order ID", "Order Date", "Ship Date", "Lead Time (Days)", "Ship Mode", "Factory", "Product Name", "Is Delayed (filtered)"]
    ].rename(columns={"Is Delayed (filtered)": "Delayed?"})
    st.dataframe(timeline, use_container_width=True, height=350)

    fig = px.scatter(
        sdf.sort_values("Order Date"), x="Order Date", y="Lead Time (Days)",
        color="Ship Mode", hover_data=["Order ID", "Factory", "Product Name"],
        title=f"Shipment Timeline — {drill_state}",
    )
    fig.add_hline(y=delay_threshold_days, line_dash="dash", line_color="red",
                  annotation_text=f"Delay threshold (P{pct})")
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.caption(
    "Data: Nassau Candy Distributor factory-to-customer shipment records. "
    "Lead time reflects a known dataset-wide date-logging offset — see the sidebar note and the "
    "accompanying research paper for methodology and the relative-scoring rationale."
)
