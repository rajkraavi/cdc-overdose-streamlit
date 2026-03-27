# CDC Drug Overdose Surveillance Dashboard
# Posit Connect Demo | Author: Raj Ravi
# Data: VSRR Provisional Drug Overdose Death Counts via data.cdc.gov

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CDC Drug Overdose Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "CDC Drug Overdose Dashboard | Built with Streamlit for Posit Connect Demo"}
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stSidebar"] { background-color: #003087; }
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span { color: #ffffff !important; }
[data-testid="stSidebar"] hr { border-color: #4a7ab5; }

.kpi-card {
    background: white;
    border-radius: 10px;
    padding: 20px 24px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.07);
    border-left: 5px solid #003087;
    margin-bottom: 12px;
}
.kpi-value { font-size: 2rem; font-weight: 700; color: #003087; margin: 0; }
.kpi-label { font-size: 0.85rem; color: #666; margin: 0; text-transform: uppercase; letter-spacing: 0.05em; }
.kpi-delta { font-size: 0.85rem; margin: 4px 0 0 0; }
.kpi-up   { color: #c0392b; }
.kpi-down { color: #27ae60; }

.section-header {
    font-size: 1.1rem;
    font-weight: 600;
    color: #003087;
    padding-bottom: 6px;
    border-bottom: 2px solid #e8eef5;
    margin-bottom: 16px;
}
.deploy-box {
    background: #f4f7fb;
    border: 1px solid #c2d4ec;
    border-radius: 8px;
    padding: 16px 20px;
    font-family: 'Courier New', monospace;
    font-size: 0.88rem;
    color: #1a1a2e;
    margin: 8px 0;
}
.tag-pill {
    display: inline-block;
    background: #e8f0fe;
    color: #003087;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.78rem;
    font-weight: 600;
    margin: 2px;
}
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────────
CDC_API = "https://data.cdc.gov/resource/xkb8-kh2a.json"

MONTH_ORDER = ["January","February","March","April","May","June",
               "July","August","September","October","November","December"]

DRUG_INDICATORS = {
    "All Drug Overdoses":                "Number of Drug Overdose Deaths",
    "All Opioids":                       "Opioids (T40.0-T40.4,T40.6)",
    "Synthetic Opioids (Fentanyl)":      "Synthetic opioids, excl. methadone (T40.4)",
    "Heroin":                            "Heroin (T40.1)",
    "Cocaine":                           "Cocaine (T40.5)",
    "Psychostimulants (Meth)":           "Psychostimulants with abuse potential (T43.6)",
    "Natural/Semi-synthetic Opioids":    "Natural & semi-synthetic opioids (T40.2)",
    "Methadone":                         "Methadone (T40.3)",
}
REVERSE_DRUG = {v: k for k, v in DRUG_INDICATORS.items()}

DRUG_COLORS = {
    "All Drug Overdoses":             "#003087",
    "All Opioids":                    "#c0392b",
    "Synthetic Opioids (Fentanyl)":   "#e74c3c",
    "Heroin":                         "#e67e22",
    "Cocaine":                        "#8e44ad",
    "Psychostimulants (Meth)":        "#16a085",
    "Natural/Semi-synthetic Opioids": "#f39c12",
    "Methadone":                      "#2980b9",
}

# ── Data loading ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner="Fetching CDC overdose data...")
def load_data():
    frames, offset, limit = [], 0, 10000
    while True:
        url = (f"{CDC_API}?$limit={limit}&$offset={offset}"
               f"&period=12%20month-ending&$order=year,month")
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        frames.append(pd.DataFrame(batch))
        if len(batch) < limit:
            break
        offset += limit

    df = pd.concat(frames, ignore_index=True)
    df["data_value"]      = pd.to_numeric(df["data_value"],      errors="coerce")
    df["predicted_value"] = pd.to_numeric(df.get("predicted_value", pd.Series(dtype=float)), errors="coerce")
    df["year"]            = pd.to_numeric(df["year"],             errors="coerce").astype("Int64")
    df["month_num"]       = df["month"].map({m: i+1 for i, m in enumerate(MONTH_ORDER)})
    df["date"]            = pd.to_datetime(dict(year=df["year"], month=df["month_num"], day=1))
    df["drug_label"]      = df["indicator"].map(REVERSE_DRUG).fillna(df["indicator"])
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Could not load CDC data: {e}")
    st.stop()

# Pre-compute key slices
latest_year  = int(df["year"].max())
all_years    = sorted(df["year"].dropna().unique().astype(int))
states_list  = sorted(df[df["state"] != "US"]["state_name"].dropna().unique())
us_overdose  = (df[(df["state"] == "US") &
                   (df["indicator"] == "Number of Drug Overdose Deaths")]
                .sort_values("date"))

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏥 CDC Overdose Dashboard")
    st.markdown("*VSRR Provisional Death Counts*")
    st.markdown("---")

    year_range = st.slider(
        "Year Range",
        min_value=int(all_years[0]),
        max_value=int(all_years[-1]),
        value=(2015, latest_year)
    )

    selected_states = st.multiselect(
        "Filter States",
        options=states_list,
        default=[],
        placeholder="All states"
    )

    selected_drugs = st.multiselect(
        "Drug Categories",
        options=list(DRUG_INDICATORS.keys()),
        default=["All Drug Overdoses", "Synthetic Opioids (Fentanyl)", "Heroin", "Cocaine"],
        placeholder="Select drug types"
    )

    st.markdown("---")
    st.markdown("**Data Source**")
    st.markdown("[data.cdc.gov](https://data.cdc.gov/resource/xkb8-kh2a.json)")
    st.markdown("*12-month rolling totals*")
    st.markdown("*Updated monthly*")
    st.markdown("---")
    st.markdown(
        '<span class="tag-pill">Python</span>'
        '<span class="tag-pill">Streamlit</span>'
        '<span class="tag-pill">Posit Connect</span>',
        unsafe_allow_html=True
    )

# ── Header ─────────────────────────────────────────────────────────────────────
col_title, col_badge = st.columns([5, 1])
with col_title:
    st.markdown("# CDC Drug Overdose Surveillance")
    st.caption(f"Provisional 12-month rolling death counts · 2015–{latest_year} · Source: CDC VSRR")
with col_badge:
    st.markdown("<br>", unsafe_allow_html=True)
    st.success("🟢 Live Data")

st.markdown("---")

# ── Apply filters ──────────────────────────────────────────────────────────────
mask_yr = df["year"].between(year_range[0], year_range[1])

us_filtered = (df[(df["state"] == "US") & mask_yr]
               .copy())

state_filtered = (df[(df["state"] != "US") & mask_yr]
                  .copy())
if selected_states:
    state_filtered = state_filtered[state_filtered["state_name"].isin(selected_states)]

# ── KPI Cards ──────────────────────────────────────────────────────────────────
us_latest = us_overdose[us_overdose["date"] == us_overdose["date"].max()]
us_prev_yr = us_overdose[us_overdose["year"] == latest_year - 1]

latest_deaths  = int(us_latest["data_value"].iloc[0]) if not us_latest.empty else 0
prev_yr_deaths = int(us_prev_yr["data_value"].max()) if not us_prev_yr.empty else 0
yoy_delta      = latest_deaths - prev_yr_deaths
yoy_pct        = (yoy_delta / prev_yr_deaths * 100) if prev_yr_deaths else 0

peak_row     = us_overdose.loc[us_overdose["data_value"].idxmax()]
peak_deaths  = int(peak_row["data_value"])
peak_period  = f"{peak_row['month']} {int(peak_row['year'])}"
total_period = f"{year_range[0]}–{year_range[1]}"

k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(f"""
    <div class="kpi-card">
        <p class="kpi-label">Latest 12-Month Total</p>
        <p class="kpi-value">{latest_deaths:,}</p>
        <p class="kpi-delta {'kpi-up' if yoy_delta > 0 else 'kpi-down'}">
            {'▲' if yoy_delta > 0 else '▼'} {abs(yoy_delta):,} ({yoy_pct:+.1f}%) vs prior year
        </p>
    </div>""", unsafe_allow_html=True)

with k2:
    st.markdown(f"""
    <div class="kpi-card" style="border-left-color:#c0392b">
        <p class="kpi-label">All-Time Peak</p>
        <p class="kpi-value" style="color:#c0392b">{peak_deaths:,}</p>
        <p class="kpi-delta" style="color:#888">{peak_period}</p>
    </div>""", unsafe_allow_html=True)

with k3:
    synth = us_filtered[us_filtered["indicator"] == DRUG_INDICATORS["Synthetic Opioids (Fentanyl)"]]
    synth_latest = int(synth.loc[synth["date"].idxmax(), "data_value"]) if not synth.empty else 0
    synth_share  = round(synth_latest / latest_deaths * 100, 1) if latest_deaths else 0
    st.markdown(f"""
    <div class="kpi-card" style="border-left-color:#e74c3c">
        <p class="kpi-label">Synthetic Opioid Deaths</p>
        <p class="kpi-value" style="color:#e74c3c">{synth_latest:,}</p>
        <p class="kpi-delta" style="color:#888">{synth_share}% of all overdose deaths</p>
    </div>""", unsafe_allow_html=True)

with k4:
    n_states = state_filtered["state"].nunique()
    worst = (state_filtered[state_filtered["indicator"] == "Number of Drug Overdose Deaths"]
             .groupby("state_name")["data_value"].max()
             .idxmax() if not state_filtered.empty else "N/A")
    st.markdown(f"""
    <div class="kpi-card" style="border-left-color:#8e44ad">
        <p class="kpi-label">States Reporting</p>
        <p class="kpi-value" style="color:#8e44ad">{n_states}</p>
        <p class="kpi-delta" style="color:#888">Highest burden: {worst}</p>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📈  National Trends",
    "🗺️  State Explorer",
    "💊  Drug Breakdown",
    "🚀  Deploy to Posit Connect"
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 · National Trends
# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    st.markdown('<p class="section-header">Drug Overdose Deaths Over Time — United States</p>',
                unsafe_allow_html=True)

    drugs_to_plot = selected_drugs if selected_drugs else list(DRUG_INDICATORS.keys())
    indicator_ids = [DRUG_INDICATORS[d] for d in drugs_to_plot if d in DRUG_INDICATORS]

    trend_df = (us_filtered[us_filtered["indicator"].isin(indicator_ids)]
                .sort_values("date"))

    fig_trend = go.Figure()
    for drug_label in drugs_to_plot:
        ind_id = DRUG_INDICATORS.get(drug_label)
        if not ind_id:
            continue
        subset = trend_df[trend_df["indicator"] == ind_id]
        if subset.empty:
            continue
        fig_trend.add_trace(go.Scatter(
            x=subset["date"],
            y=subset["data_value"],
            name=drug_label,
            mode="lines",
            line=dict(color=DRUG_COLORS.get(drug_label, "#888"), width=2.5),
            hovertemplate=(
                f"<b>{drug_label}</b><br>"
                "%{x|%B %Y}<br>"
                "Deaths: <b>%{y:,}</b>"
                "<extra></extra>"
            )
        ))

    fig_trend.update_layout(
        height=440,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis=dict(title="", showgrid=False),
        yaxis=dict(title="12-Month Rolling Death Count", gridcolor="#f0f0f0"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="sans-serif"),
        margin=dict(t=40, l=60, r=20, b=40)
    )
    # Annotate COVID period
    fig_trend.add_vrect(
        x0="2020-03-01", x1="2021-06-01",
        fillcolor="#fff3cd", opacity=0.35,
        line_width=0,
        annotation_text="COVID-19",
        annotation_position="top left",
        annotation_font_size=11
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    # YoY change chart
    st.markdown('<p class="section-header">Year-over-Year Change in Total Overdose Deaths</p>',
                unsafe_allow_html=True)

    yoy_df = (us_overdose[us_overdose["year"].between(year_range[0], year_range[1])]
              .groupby("year")["data_value"].max()
              .reset_index()
              .sort_values("year"))
    yoy_df["yoy_change"] = yoy_df["data_value"].diff()
    yoy_df["color"]      = yoy_df["yoy_change"].apply(lambda x: "#c0392b" if x > 0 else "#27ae60")

    fig_yoy = go.Figure(go.Bar(
        x=yoy_df["year"].astype(str),
        y=yoy_df["yoy_change"],
        marker_color=yoy_df["color"],
        hovertemplate="<b>%{x}</b><br>Change: %{y:+,}<extra></extra>"
    ))
    fig_yoy.update_layout(
        height=260,
        xaxis=dict(title=""),
        yaxis=dict(title="Year-over-Year Change", gridcolor="#f0f0f0", zeroline=True,
                   zerolinecolor="#999"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="sans-serif"),
        margin=dict(t=20, l=60, r=20, b=40)
    )
    st.plotly_chart(fig_yoy, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 · State Explorer
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    col_map_ctrl, _ = st.columns([2, 3])
    with col_map_ctrl:
        map_year = st.selectbox("Select Year", options=sorted(all_years, reverse=True),
                                index=0, key="map_year")

    state_year = (df[(df["state"] != "US") &
                     (df["year"] == map_year) &
                     (df["indicator"] == "Number of Drug Overdose Deaths")]
                  .dropna(subset=["data_value"]))

    state_max = (state_year.groupby(["state","state_name"])["data_value"]
                 .max()
                 .reset_index()
                 .rename(columns={"data_value": "deaths"}))

    c_map, c_rank = st.columns([6, 4])

    with c_map:
        st.markdown('<p class="section-header">Drug Overdose Deaths by State</p>',
                    unsafe_allow_html=True)
        fig_map = px.choropleth(
            state_max,
            locations="state",
            locationmode="USA-states",
            color="deaths",
            color_continuous_scale="YlOrRd",
            scope="usa",
            hover_name="state_name",
            hover_data={"state": False, "deaths": ":,"},
            labels={"deaths": "Deaths"},
            title=f"12-Month Overdose Deaths — {map_year}"
        )
        fig_map.update_layout(
            height=400,
            geo=dict(bgcolor="white", lakecolor="white"),
            coloraxis_colorbar=dict(title="Deaths"),
            margin=dict(t=40, l=0, r=0, b=0),
            paper_bgcolor="white"
        )
        st.plotly_chart(fig_map, use_container_width=True)

    with c_rank:
        st.markdown('<p class="section-header">State Rankings</p>', unsafe_allow_html=True)
        top_states = state_max.sort_values("deaths", ascending=True).tail(20)
        fig_rank = go.Figure(go.Bar(
            x=top_states["deaths"],
            y=top_states["state_name"],
            orientation="h",
            marker_color="#003087",
            hovertemplate="<b>%{y}</b><br>Deaths: %{x:,}<extra></extra>",
            text=top_states["deaths"].apply(lambda x: f"{int(x):,}"),
            textposition="outside"
        ))
        fig_rank.update_layout(
            height=400,
            xaxis=dict(title="Deaths", gridcolor="#f0f0f0"),
            yaxis=dict(title=""),
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(t=10, l=10, r=60, b=40),
            font=dict(family="sans-serif", size=11)
        )
        st.plotly_chart(fig_rank, use_container_width=True)

    # State trend (if specific states selected)
    if selected_states:
        st.markdown('<p class="section-header">Trend for Selected States</p>',
                    unsafe_allow_html=True)
        st_trend = (state_filtered[state_filtered["indicator"] == "Number of Drug Overdose Deaths"]
                    .sort_values("date"))
        fig_st = px.line(
            st_trend,
            x="date", y="data_value", color="state_name",
            labels={"data_value": "Deaths", "date": "", "state_name": "State"},
            height=320
        )
        fig_st.update_layout(
            hovermode="x unified",
            plot_bgcolor="white",
            paper_bgcolor="white",
            yaxis=dict(gridcolor="#f0f0f0"),
            xaxis=dict(showgrid=False),
            legend=dict(orientation="h", y=-0.25),
            margin=dict(t=10, l=60, r=20, b=60)
        )
        st.plotly_chart(fig_st, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 · Drug Breakdown
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown('<p class="section-header">Drug Type Composition Over Time</p>',
                unsafe_allow_html=True)

    breakdown_indicators = [
        "Synthetic Opioids (Fentanyl)",
        "Heroin",
        "Cocaine",
        "Natural/Semi-synthetic Opioids",
        "Psychostimulants (Meth)",
        "Methadone",
    ]
    breakdown_ids = [DRUG_INDICATORS[d] for d in breakdown_indicators]

    area_df = (us_filtered[us_filtered["indicator"].isin(breakdown_ids)]
               .sort_values("date")
               .dropna(subset=["data_value"]))
    area_df["drug_label"] = area_df["indicator"].map(REVERSE_DRUG)

    fig_area = px.area(
        area_df,
        x="date", y="data_value",
        color="drug_label",
        color_discrete_map=DRUG_COLORS,
        labels={"data_value": "Deaths", "date": "", "drug_label": "Drug Type"},
        height=380
    )
    fig_area.update_layout(
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.25, x=0),
        xaxis=dict(showgrid=False, title=""),
        yaxis=dict(gridcolor="#f0f0f0", title="12-Month Rolling Deaths"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=10, l=60, r=20, b=80)
    )
    st.plotly_chart(fig_area, use_container_width=True)

    # Latest year breakdown — donut
    col_donut, col_shift = st.columns(2)

    with col_donut:
        st.markdown('<p class="section-header">Latest Year: Drug Share</p>',
                    unsafe_allow_html=True)
        latest_breakdown = (us_filtered[
            (us_filtered["year"] == latest_year) &
            (us_filtered["indicator"].isin(breakdown_ids))
        ].groupby("indicator")["data_value"].max().reset_index())
        latest_breakdown["drug_label"] = latest_breakdown["indicator"].map(REVERSE_DRUG)

        fig_donut = go.Figure(go.Pie(
            labels=latest_breakdown["drug_label"],
            values=latest_breakdown["data_value"],
            hole=0.45,
            marker_colors=[DRUG_COLORS.get(d, "#888") for d in latest_breakdown["drug_label"]],
            hovertemplate="<b>%{label}</b><br>%{value:,} deaths<br>%{percent}<extra></extra>"
        ))
        fig_donut.update_layout(
            height=320,
            legend=dict(orientation="v", x=1, y=0.5),
            margin=dict(t=10, l=0, r=120, b=10),
            paper_bgcolor="white"
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with col_shift:
        st.markdown('<p class="section-header">The Opioid Shift: Heroin → Fentanyl</p>',
                    unsafe_allow_html=True)
        shift_ids = [DRUG_INDICATORS["Synthetic Opioids (Fentanyl)"],
                     DRUG_INDICATORS["Heroin"]]
        shift_df = (us_filtered[us_filtered["indicator"].isin(shift_ids)]
                    .groupby(["year", "indicator"])["data_value"].max()
                    .reset_index()
                    .sort_values("year"))
        shift_df["drug_label"] = shift_df["indicator"].map(REVERSE_DRUG)

        fig_shift = px.line(
            shift_df,
            x="year", y="data_value", color="drug_label",
            color_discrete_map=DRUG_COLORS,
            markers=True,
            labels={"data_value": "Deaths", "year": "Year", "drug_label": ""},
            height=300
        )
        fig_shift.update_layout(
            hovermode="x unified",
            plot_bgcolor="white",
            paper_bgcolor="white",
            xaxis=dict(showgrid=False, dtick=1),
            yaxis=dict(gridcolor="#f0f0f0"),
            legend=dict(orientation="h", y=-0.3),
            margin=dict(t=10, l=60, r=20, b=70)
        )
        st.plotly_chart(fig_shift, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 · Deploy to Posit Connect
# ─────────────────────────────────────────────────────────────────────────────
with tab4:
    st.markdown("## 🚀 Deploying to Posit Connect")
    st.markdown(
        "Posit Connect is a publishing platform that supports **both R and Python** — "
        "Shiny apps, Streamlit apps, Jupyter notebooks, APIs, and more, all in one place. "
        "This dashboard can be deployed with a single command."
    )

    st.markdown("---")

    d1, d2 = st.columns(2)

    with d1:
        st.markdown("### Step 1 — Install rsconnect-python")
        st.markdown('<div class="deploy-box">pip install rsconnect-python</div>',
                    unsafe_allow_html=True)

        st.markdown("### Step 2 — Add your server")
        st.markdown(
            '<div class="deploy-box">'
            'rsconnect add \\\n'
            '  --server https://your-connect-server.example.com \\\n'
            '  --name my-connect \\\n'
            '  --api-key &lt;YOUR_API_KEY&gt;'
            '</div>',
            unsafe_allow_html=True
        )

        st.markdown("### Step 3 — Deploy")
        st.markdown(
            '<div class="deploy-box">'
            'rsconnect deploy streamlit \\\n'
            '  --name my-connect \\\n'
            '  --title "CDC Overdose Dashboard" \\\n'
            '  .'
            '</div>',
            unsafe_allow_html=True
        )

    with d2:
        st.markdown("### Why Posit Connect?")
        features = {
            "🔁 Scheduled Refresh":    "Pin datasets on a schedule so dashboards always show current data.",
            "🔐 Access Control":       "Share with specific users, groups, or make public — all via the UI.",
            "🐍 + 📊 Polyglot":        "R Shiny and Python Streamlit live side by side on the same server.",
            "📦 Dependency Mgmt":      "Connect reads requirements.txt / renv.lock and handles environments.",
            "🔗 Vanity URLs":          "Give your app a branded URL like connect.org/cdc-dashboard.",
            "📬 Email Reports":        "Schedule automated report delivery alongside interactive apps.",
        }
        for title, desc in features.items():
            st.markdown(f"**{title}** — {desc}")

        st.markdown("---")
        st.markdown("### This Project on Posit Connect")
        st.markdown(
            "| App | Framework | Language |\n"
            "|-----|-----------|----------|\n"
            "| CDC PLACES Health Dashboard | **Shiny** | **R** |\n"
            "| CDC Drug Overdose Dashboard | **Streamlit** | **Python** |"
        )
        st.info(
            "Both apps deployed from the same Posit Connect instance — "
            "one URL, one access policy, one platform."
        )

    st.markdown("---")
    st.markdown("### requirements.txt")
    st.code(
        "streamlit>=1.32.0\npandas>=2.0.0\nplotly>=5.18.0\nrequests>=2.31.0",
        language="text"
    )

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center; color:#888; font-size:0.8rem;'>"
    "CDC Drug Overdose Surveillance Dashboard &nbsp;|&nbsp; "
    "Data: <a href='https://data.cdc.gov/resource/xkb8-kh2a.json' target='_blank'>CDC VSRR Provisional Death Counts</a>"
    " &nbsp;|&nbsp; Built with Streamlit for Posit Connect Demo &nbsp;|&nbsp; Raj Ravi 2026"
    "</div>",
    unsafe_allow_html=True
)
