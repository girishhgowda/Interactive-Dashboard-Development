import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import requests
import folium
from folium.plugins import Fullscreen, MiniMap, MarkerCluster, HeatMap, MousePosition
from branca.colormap import LinearColormap
from streamlit_folium import st_folium
from math import erfc, sqrt


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Workora Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

DATA = "data/"


# ============================================================
# REGION / ZONE MAPPING
# ============================================================

ZONE = {
    "Delhi": "North",
    "Rajasthan": "North",
    "Karnataka": "South",
    "Telangana": "South",
    "Tamil Nadu": "South",
    "Kerala": "South",
    "Maharashtra": "West",
    "Gujarat": "West",
    "West Bengal": "East"
}


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data
def load_data():

    # ---------------- Web Traffic ----------------
    web = pd.read_csv(
        DATA + "web_traffic.csv",
        parse_dates=["Date"]
    )

    for col in ["StartedRegistration", "Registered", "Bounced"]:
        web[col] = (
            web[col]
            .astype(str)
            .str.strip()
            .str.lower()
            .eq("yes")
        )

    web["Zone"] = web["Region"].map(ZONE)


    # ---------------- Customer Churn ----------------
    churn = pd.read_csv(
        DATA + "customer_churn.csv"
    )

    raw_rows = len(churn)

    churn = churn.drop_duplicates()

    churn["Region"] = (
        churn["Region"]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
    )

    churn["TotalChargesINR"] = pd.to_numeric(
        churn["TotalChargesINR"],
        errors="coerce"
    )

    churn["MonthlyChargesINR"] = pd.to_numeric(
        churn["MonthlyChargesINR"],
        errors="coerce"
    )

    churn["Churned"] = (
        churn["Churn"]
        .astype(str)
        .str.strip()
        .str.lower()
        .eq("yes")
    )

    churn["Outlier"] = churn["MonthlyChargesINR"] > 5000


    # ---------------- Regional Market ----------------
    regional = pd.read_csv(
        DATA + "regional_market.csv"
    )

    regional["Zone"] = regional["State"].map(ZONE)

    regional["Latitude"] = pd.to_numeric(
        regional["Latitude"],
        errors="coerce"
    )

    regional["Longitude"] = pd.to_numeric(
        regional["Longitude"],
        errors="coerce"
    )


    # ---------------- A/B Test ----------------
    ab = pd.read_csv(
        DATA + "checkout_ab_test.csv",
        parse_dates=["Timestamp"]
    )

    ab["Date"] = ab["Timestamp"].dt.normalize()

    for col in ["CheckoutStarted", "Converted"]:
        ab[col] = (
            ab[col]
            .astype(str)
            .str.strip()
            .str.lower()
            .eq("yes")
        )


    return web, churn, regional, ab, raw_rows


web, churn, regional, ab, raw_rows = load_data()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("Filters")

st.sidebar.markdown(
    "Use the filters below to explore the dashboard."
)


# ---------------- Date ----------------

date_min = web["Date"].min().date()
date_max = web["Date"].max().date()

date_range = st.sidebar.date_input(
    "Date range",
    value=(date_min, date_max),
    min_value=date_min,
    max_value=date_max
)

if len(date_range) != 2:
    st.warning("Please select both start and end dates.")
    st.stop()

start_date = pd.Timestamp(date_range[0])
end_date = pd.Timestamp(date_range[1])


# ---------------- Region ----------------

regions = sorted(
    churn["Region"]
    .dropna()
    .unique()
)

selected_regions = st.sidebar.multiselect(
    "Region",
    options=regions,
    default=regions
)


# ---------------- Subscription ----------------

plans = sorted(
    churn["SubscriptionType"]
    .dropna()
    .unique()
)

selected_plans = st.sidebar.multiselect(
    "Category (subscription plan)",
    options=plans,
    default=plans
)


# ---------------- Device ----------------

devices = sorted(
    web["DeviceCategory"]
    .dropna()
    .unique()
)

selected_devices = st.sidebar.multiselect(
    "Device",
    options=devices,
    default=devices
)


st.sidebar.divider()

st.sidebar.caption(
    "Region filtering applies to web traffic, "
    "regional market and customer churn data."
)

st.sidebar.caption(
    "The A/B test does not contain a Region field."
)


# ============================================================
# FILTER DATA
# ============================================================

filtered_web = web[
    web["Date"].between(start_date, end_date)
    & web["Zone"].isin(selected_regions)
    & web["DeviceCategory"].isin(selected_devices)
].copy()


filtered_churn = churn[
    churn["Region"].isin(selected_regions)
    & churn["SubscriptionType"].isin(selected_plans)
].copy()


filtered_regional = regional[
    regional["Zone"].isin(selected_regions)
].copy()


filtered_ab = ab[
    ab["Date"].between(start_date, end_date)
    & ab["Device"].isin(selected_devices)
].copy()


# ============================================================
# HEADER
# ============================================================

st.title("Workora Analytics Dashboard")

st.caption(
    "Business performance, traffic, regional market, "
    "customer churn and checkout A/B testing analytics."
)

st.info(
    "All data is synthetic and intended for learning purposes. "
    "It does not represent real business results."
)


# ============================================================
# KPI CALCULATIONS
# ============================================================

converted_orders = filtered_ab[
    filtered_ab["Converted"]
].copy()


total_revenue = converted_orders["OrderValueINR"].sum()

active_users = int(
    (~filtered_churn["Churned"]).sum()
)

churn_rate = (
    filtered_churn["Churned"].mean() * 100
    if len(filtered_churn) > 0
    else 0
)

avg_ticket = (
    converted_orders["OrderValueINR"].mean()
    if len(converted_orders) > 0
    else 0
)


# ============================================================
# KPI CARDS
# ============================================================

k1, k2, k3, k4 = st.columns(4)

k1.metric(
    "Total Revenue",
    f"₹{total_revenue:,.0f}"
)

k2.metric(
    "Active Users",
    f"{active_users:,}"
)

k3.metric(
    "Churn Rate",
    f"{churn_rate:.1f}%"
)

k4.metric(
    "Avg Ticket Size",
    f"₹{avg_ticket:,.0f}"
)


st.divider()


# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Overview",
        "Traffic & Conversion",
        "Regional Market",
        "Customer Churn",
        "Checkout A/B Test"
    ]
)


# ============================================================
# TAB 1 — OVERVIEW
# ============================================================

with tab1:

    st.subheader("Business Overview")

    col1, col2 = st.columns(2)

    # Monthly traffic
    if len(filtered_web) > 0:

        monthly = (
            filtered_web
            .assign(
                Month=lambda x:
                x["Date"].dt.to_period("M").dt.to_timestamp()
            )
            .groupby("Month")
            .agg(
                Sessions=("SessionID", "count"),
                Registered=("Registered", "sum")
            )
            .reset_index()
        )

        fig = px.line(
            monthly,
            x="Month",
            y=["Sessions", "Registered"],
            markers=True,
            title="Monthly Sessions & Registrations"
        )

        fig.update_layout(
            hovermode="x unified",
            legend_title=""
        )

        col1.plotly_chart(
            fig,
            use_container_width=True
        )

    else:
        col1.info("No traffic data for the selected filters.")


    # Churn by plan
    if len(filtered_churn) > 0:

        plan_churn = (
            filtered_churn
            .groupby("SubscriptionType")["Churned"]
            .mean()
            .mul(100)
            .round(1)
            .reset_index()
        )

        fig = px.bar(
            plan_churn,
            x="SubscriptionType",
            y="Churned",
            text="Churned",
            title="Churn Rate by Subscription Plan"
        )

        fig.update_traces(
            texttemplate="%{text:.1f}%",
            textposition="outside"
        )

        fig.update_yaxes(
            title="Churn %"
        )

        col2.plotly_chart(
            fig,
            use_container_width=True
        )

    else:
        col2.info("No churn data for the selected filters.")


    st.caption(
        "Revenue and average ticket size come from converted "
        "orders in the checkout A/B test."
    )


# ============================================================
# TAB 2 — TRAFFIC & CONVERSION
# ============================================================

with tab2:

    st.subheader("Traffic & Conversion Analysis")

    col1, col2 = st.columns(2)

    if len(filtered_web) > 0:

        # Funnel
        funnel = pd.DataFrame({
            "Stage": [
                "Sessions",
                "Engaged",
                "Started Registration",
                "Registered"
            ],
            "Count": [
                len(filtered_web),
                int((~filtered_web["Bounced"]).sum()),
                int(filtered_web["StartedRegistration"].sum()),
                int(filtered_web["Registered"].sum())
            ]
        })

        fig = px.funnel(
            funnel,
            x="Count",
            y="Stage",
            title="Conversion Funnel"
        )

        col1.plotly_chart(
            fig,
            use_container_width=True
        )


        # Conversion by source
        source = (
            filtered_web
            .groupby("Source")
            .agg(
                Sessions=("SessionID", "count"),
                Registered=("Registered", "sum"),
                Bounce=("Bounced", "mean")
            )
            .reset_index()
        )

        source["Conversion %"] = (
            source["Registered"]
            / source["Sessions"]
            * 100
        ).round(1)

        source["Bounce %"] = (
            source["Bounce"] * 100
        ).round(1)


        fig = px.bar(
            source.sort_values("Conversion %"),
            x="Conversion %",
            y="Source",
            orientation="h",
            text="Conversion %",
            title="Conversion Rate by Source"
        )

        fig.update_traces(
            texttemplate="%{text:.1f}%",
            textposition="outside"
        )

        col2.plotly_chart(
            fig,
            use_container_width=True
        )


        st.subheader("Landing Page Performance")

        col3, col4 = st.columns(2)


        landing = (
            filtered_web
            .groupby("LandingPage")
            .agg(
                Sessions=("SessionID", "count"),
                Registered=("Registered", "sum")
            )
            .reset_index()
        )

        landing["Drop-off %"] = (
            100
            - landing["Registered"]
            / landing["Sessions"]
            * 100
        ).round(1)


        fig = px.bar(
            landing.sort_values("Drop-off %"),
            x="Drop-off %",
            y="LandingPage",
            orientation="h",
            text="Drop-off %",
            title="Drop-off by Landing Page"
        )

        fig.update_traces(
            texttemplate="%{text:.1f}%",
            textposition="outside"
        )

        col3.plotly_chart(
            fig,
            use_container_width=True
        )


        col4.dataframe(
            source[
                [
                    "Source",
                    "Sessions",
                    "Bounce %",
                    "Conversion %"
                ]
            ].sort_values(
                "Conversion %",
                ascending=False
            ),
            hide_index=True,
            use_container_width=True
        )


# ============================================================
# TAB 3 — REGIONAL MARKET
# ============================================================

@st.cache_data(show_spinner=False)
def load_geojson(url):
    """Download and cache a GeoJSON boundary layer."""
    response = requests.get(
        url,
        timeout=30,
        headers={"User-Agent": "Workora-Analytics-Dashboard/1.0"}
    )
    response.raise_for_status()
    return response.json()


INDIA_GEOJSON_URL = (
    "https://cdn.jsdelivr.net/gh/udit-001/india-maps-data@2884453/"
    "geojson/india.geojson"
)

STATE_GEOJSON_BASE = (
    "https://cdn.jsdelivr.net/gh/udit-001/india-maps-data@2884453/"
    "geojson/states/"
)

STATE_SLUGS = {
    "Andhra Pradesh": "andhra-pradesh",
    "Arunachal Pradesh": "arunachal-pradesh",
    "Assam": "assam",
    "Bihar": "bihar",
    "Chhattisgarh": "chhattisgarh",
    "Goa": "goa",
    "Gujarat": "gujarat",
    "Haryana": "haryana",
    "Himachal Pradesh": "himachal-pradesh",
    "Jharkhand": "jharkhand",
    "Karnataka": "karnataka",
    "Kerala": "kerala",
    "Madhya Pradesh": "madhya-pradesh",
    "Maharashtra": "maharashtra",
    "Manipur": "manipur",
    "Meghalaya": "meghalaya",
    "Mizoram": "mizoram",
    "Nagaland": "nagaland",
    "Odisha": "odisha",
    "Punjab": "punjab",
    "Rajasthan": "rajasthan",
    "Sikkim": "sikkim",
    "Tamil Nadu": "tamil-nadu",
    "Telangana": "telangana",
    "Tripura": "tripura",
    "Uttar Pradesh": "uttar-pradesh",
    "Uttarakhand": "uttarakhand",
    "West Bengal": "west-bengal",
    "Delhi": "delhi",
    "Jammu and Kashmir": "jammu-and-kashmir",
    "Ladakh": "ladakh",
    "Puducherry": "puducherry",
    "Chandigarh": "chandigarh"
}


def conversion_color(value, low, high):
    """Green = high conversion, yellow = medium, red = low."""
    if pd.isna(value):
        return "#9CA3AF"
    if high <= low:
        return "#22C55E"
    scale = LinearColormap(
        ["#DC2626", "#FACC15", "#22C55E"],
        vmin=low,
        vmax=high
    )
    return scale(float(value))


with tab3:

    st.subheader("Regional Market Opportunity")
    st.caption("Interactive India market map — opportunity score, demand, conversion and competition")

    if len(filtered_regional) == 0:
        st.warning("No regional market data available for the selected regions.")
    else:
        map_data = filtered_regional.copy()

        # Clean numeric fields.
        for col in ["Latitude", "Longitude", "MonthlySearchDemand", "LeadConversionRate", "ExistingCompetitors", "EstimatedAcquisitionCostINR"]:
            if col in map_data.columns:
                map_data[col] = pd.to_numeric(map_data[col], errors="coerce")

        map_data["MonthlySearchDemand"] = map_data["MonthlySearchDemand"].fillna(0)
        map_data["LeadConversionRate"] = map_data["LeadConversionRate"].fillna(0)
        map_data["ExistingCompetitors"] = map_data["ExistingCompetitors"].fillna(0)
        map_data["EstimatedAcquisitionCostINR"] = map_data["EstimatedAcquisitionCostINR"].fillna(0)
        map_data = map_data.dropna(subset=["Latitude", "Longitude"]).copy()

        # --------------------------------------------------------
        # Opportunity score
        # High demand + high conversion + low competition + lower CAC.
        # --------------------------------------------------------
        def minmax(series, inverse=False):
            lo, hi = float(series.min()), float(series.max())
            if hi <= lo:
                out = pd.Series(1.0, index=series.index)
            else:
                out = (series - lo) / (hi - lo)
            return 1 - out if inverse else out

        map_data["DemandScore"] = minmax(map_data["MonthlySearchDemand"])
        map_data["ConversionScore"] = minmax(map_data["LeadConversionRate"])
        map_data["CompetitionScore"] = minmax(map_data["ExistingCompetitors"], inverse=True)
        map_data["CostScore"] = minmax(map_data["EstimatedAcquisitionCostINR"], inverse=True)
        map_data["OpportunityScore"] = (
            map_data["DemandScore"] * 35
            + map_data["ConversionScore"] * 35
            + map_data["CompetitionScore"] * 20
            + map_data["CostScore"] * 10
        ).round(1)

        map_data["DemandPerCompetitor"] = (
            map_data["MonthlySearchDemand"] /
            map_data["ExistingCompetitors"].replace(0, 1)
        )

        # Top 3 underserved / highest-opportunity markets.
        top3 = map_data.sort_values(
            ["OpportunityScore", "DemandPerCompetitor"], ascending=False
        ).head(3).copy()

        controls1, controls2, controls3 = st.columns([1.1, 1.5, 1.2])
        with controls1:
            map_detail = st.radio("Map detail", ["India", "State focus"], horizontal=True)
        with controls2:
            if map_detail == "State focus":
                states = sorted(map_data["State"].dropna().astype(str).unique())
                focus_state = st.selectbox("Focus state", states)
                map_data = map_data[map_data["State"].astype(str) == focus_state].copy()
                top3 = map_data.sort_values(["OpportunityScore", "DemandPerCompetitor"], ascending=False).head(3)
            else:
                focus_state = None
        with controls3:
            map_style = st.selectbox("Map style", ["Esri Street Map", "OpenStreetMap"], index=0)

        if len(map_data) == 0:
            st.warning("No valid market locations for the selected state.")
        else:
            center_lat = float(map_data["Latitude"].mean())
            center_lon = float(map_data["Longitude"].mean())

            fmap = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=5 if focus_state is None else 7,
                tiles=None,
                control_scale=True,
                zoom_control=True,
                prefer_canvas=True,
                width="100%",
                height=680
            )

            # Detailed road basemap similar to the earlier Leaflet map.
            esri_tiles = (
                "https://server.arcgisonline.com/ArcGIS/rest/services/"
                "World_Street_Map/MapServer/tile/{z}/{y}/{x}"
            )
            esri_attr = "Tiles © Esri — Sources: Esri, HERE, Garmin, Intermap, increment P Corp., GEBCO, USGS, FAO, NPS, NRCAN, GeoBase, IGN, Kadaster NL, Ordnance Survey, Esri Japan, METI, Esri China (Hong Kong), (c) OpenStreetMap contributors"

            folium.TileLayer(
                tiles=esri_tiles,
                attr=esri_attr,
                name="Esri Street Map",
                overlay=False,
                control=True,
                show=(map_style == "Esri Street Map"),
                max_zoom=19
            ).add_to(fmap)
            folium.TileLayer(
                tiles="OpenStreetMap",
                name="OpenStreetMap",
                overlay=False,
                control=True,
                show=(map_style == "OpenStreetMap"),
                max_zoom=19
            ).add_to(fmap)

            # India/state administrative boundaries.
            try:
                boundary_geojson = load_geojson(
                    INDIA_GEOJSON_URL if focus_state is None else
                    STATE_GEOJSON_BASE + STATE_SLUGS.get(focus_state, "") + ".geojson"
                )
                folium.GeoJson(
                    boundary_geojson,
                    name="Administrative Boundaries",
                    style_function=lambda feature: {
                        "color": "#475569",
                        "weight": 1.1,
                        "fillColor": "#86EFAC",
                        "fillOpacity": 0.035,
                    },
                    highlight_function=lambda feature: {
                        "color": "#16A34A",
                        "weight": 2.5,
                        "fillOpacity": 0.10,
                    }
                ).add_to(fmap)
            except Exception as e:
                st.info(f"Boundary layer unavailable: {e}")

            # Legend styled like the Claude map.
            legend = """
            <div style="position: fixed; bottom: 25px; left: 25px; z-index:9999;
                        background:white; color:#111827; padding:12px 14px; border:1px solid #aaa;
                        border-radius:6px; font-size:13px; font-family:Arial,sans-serif;
                        line-height:1.65; box-shadow:0 1px 5px rgba(0,0,0,.25);">
                <b style="color:#111827">Opportunity score</b><br>
                <span style="color:#15803D">●</span> <span style="color:#111827">High (65+)</span><br>
                <span style="color:#F59E0B">●</span> <span style="color:#111827">Medium (45–65)</span><br>
                <span style="color:#DC2626">●</span> <span style="color:#111827">Low (&lt;45)</span><br>
                <span style="color:#334155">○</span> <span style="color:#111827">Circle size = monthly search demand</span><br>
                <span style="color:#111827;font-size:15px">★</span> <span style="color:#111827">= Top 3 underserved markets</span>
            </div>
            """
            fmap.get_root().html.add_child(folium.Element(legend))

            def score_color(score):
                if score >= 65:
                    return "#15803D"
                if score >= 45:
                    return "#F59E0B"
                return "#DC2626"

            marker_group = folium.FeatureGroup(name="Market opportunities", show=True)
            cluster = MarkerCluster(
                name="Market locations",
                options={"disableClusteringAtZoom": 8, "spiderfyOnMaxZoom": True}
            ).add_to(marker_group)

            q90 = max(float(map_data["MonthlySearchDemand"].quantile(0.90)), 1.0)

            for _, row in map_data.iterrows():
                score = float(row["OpportunityScore"])
                demand = float(row["MonthlySearchDemand"])
                radius = 6 + min(14, 16 * (max(demand, 0) / q90) ** 0.5)
                city = str(row.get("City", "Unknown"))
                state = str(row.get("State", "Unknown"))
                color = score_color(score)
                is_top = city in set(top3["City"].astype(str))

                popup = f"""
                <div style='font-family:Arial,sans-serif;min-width:250px;color:#111827;background:#ffffff;padding:4px'>
                  <h3 style='margin:0 0 8px'>📍 {city}</h3>
                  <b>State:</b> {state}<br>
                  <b>Opportunity score:</b> {score:.1f}/100<br>
                  <b>Monthly search demand:</b> {demand:,.0f}<br>
                  <b>Lead conversion:</b> {float(row['LeadConversionRate']):.1%}<br>
                  <b>Competitors:</b> {float(row['ExistingCompetitors']):,.0f}<br>
                  <b>Demand / competitor:</b> {float(row['DemandPerCompetitor']):,.0f}<br>
                  <b>Estimated acquisition cost:</b> ₹{float(row['EstimatedAcquisitionCostINR']):,.0f}
                </div>
                """

                folium.CircleMarker(
                    location=[float(row["Latitude"]), float(row["Longitude"])],
                    radius=radius,
                    color="#FFFFFF",
                    weight=2,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.88,
                    popup=folium.Popup(popup, max_width=330),
                    tooltip=f"{city} • {state} • Opportunity {score:.1f}"
                ).add_to(cluster)

                if is_top:
                    folium.Marker(
                        location=[float(row["Latitude"]), float(row["Longitude"])],
                        icon=folium.DivIcon(html="""
                            <div style="font-size:25px;color:#111;line-height:25px;
                                        text-shadow:0 1px 2px white,1px 0 2px white;"><b>★</b></div>
                        """),
                        tooltip=f"TOP UNDERSERVED MARKET — {city}"
                    ).add_to(marker_group)

            marker_group.add_to(fmap)

            # Heatmap is available from the layer selector, hidden initially.
            heat_points = [
                [float(r.Latitude), float(r.Longitude), float(r.MonthlySearchDemand)]
                for r in map_data.itertuples()
            ]
            if heat_points:
                heat = folium.FeatureGroup(name="Search demand heatmap", show=False)
                HeatMap(
                    heat_points,
                    radius=28,
                    blur=22,
                    min_opacity=0.20,
                    gradient={0.20: "#FDE68A", 0.45: "#FACC15", 0.70: "#22C55E", 1.0: "#15803D"}
                ).add_to(heat)
                heat.add_to(fmap)

            Fullscreen(position="topleft").add_to(fmap)
            MiniMap(toggle_display=True, zoom_level_offset=-5).add_to(fmap)
            MousePosition(position="bottomright", separator=" | ", prefix="Lat/Lon:").add_to(fmap)
            folium.LayerControl(collapsed=False, position="topright").add_to(fmap)

            # Fit to market points while keeping India view sensible.
            if len(map_data) > 1:
                fmap.fit_bounds(
                    [[float(map_data.Latitude.min()), float(map_data.Longitude.min())],
                     [float(map_data.Latitude.max()), float(map_data.Longitude.max())]],
                    padding=(20, 20),
                    max_zoom=7 if focus_state is None else 10
                )

            st_folium(fmap, use_container_width=True, height=680, returned_objects=[])

            st.caption("🟢 High opportunity • 🟠 Medium • 🔴 Low • ★ Top 3 underserved markets • Circle size = monthly search demand")

        st.subheader("Market Opportunity by City")

        city_summary = (
            filtered_regional
            .groupby("City")
            .agg(
                Search_Demand=("MonthlySearchDemand", "sum"),
                Competitors=("ExistingCompetitors", "mean"),
                Avg_Conversion=("LeadConversionRate", "mean"),
                Avg_Acquisition_Cost=("EstimatedAcquisitionCostINR", "mean")
            )
            .reset_index()
        )

        city_summary["Demand per Competitor"] = (
            city_summary["Search_Demand"]
            / city_summary["Competitors"].replace(0, pd.NA)
        ).round(0)

        city_summary = city_summary.sort_values(
            "Demand per Competitor",
            ascending=False
        )

        col1, col2 = st.columns(2)

        fig = px.bar(
            city_summary,
            x="Demand per Competitor",
            y="City",
            orientation="h",
            text="Demand per Competitor",
            title="Demand per Competitor"
        )
        fig.update_traces(
            texttemplate="%{text:,.0f}",
            textposition="outside"
        )
        col1.plotly_chart(fig, use_container_width=True)

        conversion_city = city_summary.sort_values(
            "Avg_Conversion",
            ascending=True
        )

        fig = px.bar(
            conversion_city,
            x="Avg_Conversion",
            y="City",
            orientation="h",
            text="Avg_Conversion",
            title="Average Lead Conversion Rate",
            color="Avg_Conversion",
            color_continuous_scale="RdYlGn"
        )
        fig.update_traces(
            texttemplate="%{text:.1%}",
            textposition="outside"
        )
        col2.plotly_chart(fig, use_container_width=True)

        st.subheader("Regional Market Data")

        display_city = city_summary.copy()
        display_city["Avg_Conversion"] = display_city["Avg_Conversion"].map(
            lambda x: f"{x:.1%}"
        )
        display_city["Avg_Acquisition_Cost"] = display_city["Avg_Acquisition_Cost"].map(
            lambda x: f"₹{x:,.0f}"
        )

        st.dataframe(
            display_city,
            hide_index=True,
            use_container_width=True
        )


# ============================================================
# TAB 4 — CUSTOMER CHURN
# ============================================================

with tab4:

    st.subheader("Customer Churn Analysis")

    if len(filtered_churn) == 0:

        st.warning("No churn data for the selected filters.")

    else:

        col1, col2 = st.columns(2)


        # Contract
        contract = (
            filtered_churn
            .groupby("ContractType")["Churned"]
            .mean()
            .mul(100)
            .round(1)
            .reset_index()
        )

        fig = px.bar(
            contract,
            x="ContractType",
            y="Churned",
            text="Churned",
            title="Churn Rate by Contract"
        )

        fig.update_traces(
            texttemplate="%{text:.1f}%",
            textposition="outside"
        )

        col1.plotly_chart(
            fig,
            use_container_width=True
        )


        # Region
        region_churn = (
            filtered_churn
            .groupby("Region")["Churned"]
            .mean()
            .mul(100)
            .round(1)
            .reset_index()
        )

        fig = px.bar(
            region_churn,
            x="Region",
            y="Churned",
            text="Churned",
            title="Churn Rate by Region"
        )

        fig.update_traces(
            texttemplate="%{text:.1f}%",
            textposition="outside"
        )

        col2.plotly_chart(
            fig,
            use_container_width=True
        )


        # Tenure
        col3, col4 = st.columns(2)

        churn_tenure = filtered_churn.copy()

        churn_tenure["TenureGroup"] = pd.cut(
            churn_tenure["TenureMonths"],
            bins=[-1, 12, 24, 48, 72],
            labels=[
                "0–12",
                "13–24",
                "25–48",
                "49–72"
            ]
        )


        tenure = (
            churn_tenure
            .groupby(
                "TenureGroup",
                observed=False
            )["Churned"]
            .mean()
            .mul(100)
            .round(1)
            .reset_index()
        )


        fig = px.bar(
            tenure,
            x="TenureGroup",
            y="Churned",
            text="Churned",
            title="Churn Rate by Customer Tenure"
        )

        fig.update_traces(
            texttemplate="%{text:.1f}%",
            textposition="outside"
        )

        col3.plotly_chart(
            fig,
            use_container_width=True
        )


        # AutoPay
        autopay = (
            filtered_churn
            .groupby("AutoPay")["Churned"]
            .mean()
            .mul(100)
            .round(1)
            .reset_index()
        )

        fig = px.bar(
            autopay,
            x="AutoPay",
            y="Churned",
            text="Churned",
            title="Churn Rate by AutoPay"
        )

        fig.update_traces(
            texttemplate="%{text:.1f}%",
            textposition="outside"
        )

        col4.plotly_chart(
            fig,
            use_container_width=True
        )


        # Average charge
        clean_charges = filtered_churn[
            ~filtered_churn["Outlier"]
        ]

        if len(clean_charges) > 0:

            avg_charge = (
                clean_charges["MonthlyChargesINR"]
                .mean()
            )

            st.metric(
                "Average Monthly Charge",
                f"₹{avg_charge:,.0f}"
            )


# ============================================================
# TAB 5 — A/B TEST
# ============================================================

with tab5:

    st.subheader("Checkout A/B Test")

    if len(filtered_ab) == 0:

        st.warning(
            "No A/B test data exists for the selected date range."
        )

    else:

        ab_summary = (
            filtered_ab
            .groupby("Variant")
            .agg(
                Visitors=("VisitorID", "count"),
                Conversions=("Converted", "sum"),
                Revenue=("OrderValueINR", "sum")
            )
            .reset_index()
        )


        ab_summary["Conversion %"] = (
            ab_summary["Conversions"]
            / ab_summary["Visitors"]
            * 100
        ).round(2)


        col1, col2 = st.columns(2)


        # Conversion chart
        fig = px.bar(
            ab_summary,
            x="Variant",
            y="Conversion %",
            text="Conversion %",
            title="Checkout Conversion by Variant"
        )

        fig.update_traces(
            texttemplate="%{text:.2f}%",
            textposition="outside"
        )

        col1.plotly_chart(
            fig,
            use_container_width=True
        )


        # Table
        col2.dataframe(
            ab_summary,
            hide_index=True,
            use_container_width=True
        )


        # ====================================================
        # STATISTICAL TEST
        # ====================================================

        if set(["A", "B"]).issubset(
            set(ab_summary["Variant"])
        ):

            stats = ab_summary.set_index("Variant")

            visitors_a = stats.loc["A", "Visitors"]
            visitors_b = stats.loc["B", "Visitors"]

            conversions_a = stats.loc["A", "Conversions"]
            conversions_b = stats.loc["B", "Conversions"]


            rate_a = conversions_a / visitors_a
            rate_b = conversions_b / visitors_b


            pooled_rate = (
                conversions_a + conversions_b
            ) / (
                visitors_a + visitors_b
            )


            standard_error = sqrt(
                pooled_rate
                * (1 - pooled_rate)
                * (
                    1 / visitors_a
                    + 1 / visitors_b
                )
            )


            z_score = (
                (rate_b - rate_a)
                / standard_error
                if standard_error != 0
                else 0
            )


            p_value = erfc(
                abs(z_score) / sqrt(2)
            )


            lift = (
                (rate_b - rate_a) * 100
            )


            st.divider()

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "Variant A",
                f"{rate_a * 100:.2f}%"
            )

            c2.metric(
                "Variant B",
                f"{rate_b * 100:.2f}%"
            )

            c3.metric(
                "B over A",
                f"{lift:+.2f} pts"
            )


            if p_value < 0.05:

                st.success(
                    f"Statistically significant result "
                    f"(p = {p_value:.3f}). Variant B shows "
                    f"a meaningful difference compared with A."
                )

            else:

                st.warning(
                    f"Not statistically significant "
                    f"(p = {p_value:.3f}). More data is needed "
                    f"before declaring a winner."
                )


        # ====================================================
        # DEVICE ANALYSIS
        # ====================================================

        device_ab = (
            filtered_ab
            .groupby(
                ["Device", "Variant"]
            )["Converted"]
            .mean()
            .mul(100)
            .round(2)
            .reset_index()
        )


        fig = px.bar(
            device_ab,
            x="Device",
            y="Converted",
            color="Variant",
            barmode="group",
            text="Converted",
            title="Conversion Rate by Device & Variant",
            labels={
                "Converted": "Conversion %"
            }
        )

        fig.update_traces(
            texttemplate="%{text:.2f}%",
            textposition="outside"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


# ============================================================
# DATA QUALITY / ASSUMPTIONS
# ============================================================

st.divider()

with st.expander(
    "Data Cleaning & Assumptions",
    expanded=False
):

    st.markdown(
        f"""
### Data Quality

- **Customer churn data:** {raw_rows} raw rows.
- **Duplicate rows removed:** {raw_rows - len(churn)}.
- **Final customer records:** {len(churn)}.
- Missing regions are labelled **Unknown**.
- Invalid `TotalChargesINR` values are converted to missing values.
- Monthly charges above **₹5,000** are treated as outliers.
- Outliers remain in churn calculations but are excluded from average charge calculations.

### Regional Mapping

The web traffic and regional market datasets contain Indian states,
while the customer churn dataset contains zones.

States are therefore mapped into:

- Delhi / Rajasthan → North
- Karnataka / Telangana / Tamil Nadu / Kerala → South
- Maharashtra / Gujarat → West
- West Bengal → East

### KPI Definitions

- **Total Revenue:** revenue from converted A/B-test orders.
- **Active Users:** customers who have not churned.
- **Churn Rate:** churned customers ÷ total customers.
- **Average Ticket Size:** average order value among converted orders.

### A/B Test

The A/B test data covers July 2026.

A p-value below 0.05 is treated as statistically significant.

### Important

All datasets are synthetic and intended for learning/demo purposes.
"""
    )