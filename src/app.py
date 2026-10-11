from pathlib import Path
import sqlite3

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(page_title="NOAA Storm Event Dashboard", layout="wide")
st.title("NOAA Storm Event Dashboard")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "data" / "data.db"
QUERY_PATHS = {
    "Injuries": PROJECT_ROOT / "queries" / "load_injuries.sql",
    "Property & crop damage": PROJECT_ROOT / "queries" / "load_damage.sql",
}
STATE_CODES = {
    "ALABAMA": "AL",
    "ALASKA": "AK",
    "ARIZONA": "AZ",
    "ARKANSAS": "AR",
    "CALIFORNIA": "CA",
    "COLORADO": "CO",
    "CONNECTICUT": "CT",
    "DELAWARE": "DE",
    "DISTRICT OF COLUMBIA": "DC",
    "FLORIDA": "FL",
    "GEORGIA": "GA",
    "HAWAII": "HI",
    "IDAHO": "ID",
    "ILLINOIS": "IL",
    "INDIANA": "IN",
    "IOWA": "IA",
    "KANSAS": "KS",
    "KENTUCKY": "KY",
    "LOUISIANA": "LA",
    "MAINE": "ME",
    "MARYLAND": "MD",
    "MASSACHUSETTS": "MA",
    "MICHIGAN": "MI",
    "MINNESOTA": "MN",
    "MISSISSIPPI": "MS",
    "MISSOURI": "MO",
    "MONTANA": "MT",
    "NEBRASKA": "NE",
    "NEVADA": "NV",
    "NEW HAMPSHIRE": "NH",
    "NEW JERSEY": "NJ",
    "NEW MEXICO": "NM",
    "NEW YORK": "NY",
    "NORTH CAROLINA": "NC",
    "NORTH DAKOTA": "ND",
    "OHIO": "OH",
    "OKLAHOMA": "OK",
    "OREGON": "OR",
    "PENNSYLVANIA": "PA",
    "RHODE ISLAND": "RI",
    "SOUTH CAROLINA": "SC",
    "SOUTH DAKOTA": "SD",
    "TENNESSEE": "TN",
    "TEXAS": "TX",
    "UTAH": "UT",
    "VERMONT": "VT",
    "VIRGINIA": "VA",
    "WASHINGTON": "WA",
    "WEST VIRGINIA": "WV",
    "WISCONSIN": "WI",
    "WYOMING": "WY",
}


@st.cache_data
def load_events(database_path: str, query: str, data_view: str) -> pd.DataFrame:
    with sqlite3.connect(database_path) as connection:
        events = pd.read_sql_query(query, connection)

    if data_view == "Injuries":
        events["caused_harm"] = (events["deaths"] + events["injuries"]) > 0
    return events


def summarize_injury_states(events: pd.DataFrame) -> pd.DataFrame:
    summary = (
        events.groupby("state_name")
        .agg(
            events=("caused_harm", "size"),
            harmful_events=("caused_harm", "sum"),
            deaths=("deaths", "sum"),
            injuries=("injuries", "sum"),
        )
        .reset_index()
    )
    summary["state_code"] = summary["state_name"].map(STATE_CODES)
    summary = summary.dropna(subset=["state_code"]).copy()
    summary["measure"] = summary["harmful_events"] / summary["events"] * 100
    return summary


def summarize_damage_states(events: pd.DataFrame) -> pd.DataFrame:
    summary = (
        events.groupby("state_name")
        .agg(
            events=("event_type", "size"),
            property_damage=("property_damage", "sum"),
            crop_damage=("crop_damage", "sum"),
        )
        .reset_index()
    )
    summary["state_code"] = summary["state_name"].map(STATE_CODES)
    summary = summary.dropna(subset=["state_code"]).copy()
    summary["total_damage"] = (
        summary["property_damage"] + summary["crop_damage"]
    )
    summary["measure"] = summary["total_damage"]
    return summary


def summarize_injuries(
    events: pd.DataFrame, minimum_events: int
) -> pd.DataFrame:
    summary = (
        events.groupby("event_type")
        .agg(
            events=("caused_harm", "size"),
            harmful_events=("caused_harm", "sum"),
        )
    )
    summary = summary[summary["events"] >= minimum_events].copy()
    summary["probability"] = summary["harmful_events"] / summary["events"]

    n = summary["events"].to_numpy()
    p = summary["probability"].to_numpy()
    z = 1.96
    denominator = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denominator
    margin = z * (
        p * (1 - p) / n + z**2 / (4 * n**2)
    ) ** 0.5 / denominator

    summary["ci_lower"] = center - margin
    summary["ci_upper"] = center + margin
    return summary.reset_index().sort_values("probability", ascending=False)


def summarize_damage(
    events: pd.DataFrame, minimum_events: int
) -> pd.DataFrame:
    summary = (
        events.groupby("event_type")
        .agg(
            events=("event_type", "size"),
            property_damage=("property_damage", "sum"),
            crop_damage=("crop_damage", "sum"),
        )
    )
    summary = summary[summary["events"] >= minimum_events].copy()
    summary["total_damage"] = (
        summary["property_damage"] + summary["crop_damage"]
    )
    return summary.reset_index().sort_values("total_damage", ascending=False)


if not DATABASE_PATH.is_file():
    st.error(f"Project database not found: {DATABASE_PATH}")
    st.stop()

data_view = st.sidebar.selectbox(
    "Choose data to view",
    options=list(QUERY_PATHS),
)
query_path = QUERY_PATHS[data_view]
if not query_path.is_file():
    st.error(f"Query file not found: {query_path}")
    st.stop()

query = query_path.read_text(encoding="utf-8")
events = load_events(str(DATABASE_PATH), query, data_view)
minimum_events = st.sidebar.number_input(
    "Minimum records per event type", min_value=1, value=30
)
number_to_show = st.sidebar.slider(
    "Event types to show", min_value=5, max_value=30, value=15
)

if data_view == "Injuries":
    st.caption("Observed deaths and injuries associated with NOAA storm events.")
    state_summary = summarize_injury_states(events)
    map_measure = state_summary["measure"]
    map_customdata = state_summary[
        ["state_name", "events", "harmful_events", "deaths", "injuries"]
    ].to_numpy()
    map_hovertemplate = (
        "%{customdata[0]}<br>Events with harm: %{z:.1f}%"
        "<br>Total events: %{customdata[1]:,}"
        "<br>Events with harm: %{customdata[2]:,}"
        "<br>Deaths: %{customdata[3]:,}"
        "<br>Injuries: %{customdata[4]:,}<extra></extra>"
    )
    colorbar_title = "Events with harm (%)"
    summary = summarize_injuries(events, minimum_events)
else:
    st.caption("Reported property and crop damage from NOAA storm events.")
    state_summary = summarize_damage_states(events)
    map_measure = state_summary["measure"]
    map_customdata = state_summary[
        ["state_name", "events", "property_damage", "crop_damage", "total_damage"]
    ].to_numpy()
    map_hovertemplate = (
        "%{customdata[0]}<br>Total damage: $%{z:,.0f}"
        "<br>Events: %{customdata[1]:,}"
        "<br>Property damage: $%{customdata[2]:,.0f}"
        "<br>Crop damage: $%{customdata[3]:,.0f}"
        "<br>Combined damage: $%{customdata[4]:,.0f}<extra></extra>"
    )
    colorbar_title = "Total damage ($)"
    summary = summarize_damage(events, minimum_events)

if state_summary.empty:
    st.warning("No state-level data is available to display.")
    st.stop()

st.subheader(f"{data_view} statistics by state")
st.caption(
    "Click a state to filter the dashboard. The map remains a full-dataset "
    "overview. Hover for state details. Territories and offshore regions "
    "are not shown."
)
state_map = go.Figure(
    go.Choropleth(
        locations=state_summary["state_code"],
        z=map_measure,
        locationmode="USA-states",
        colorscale="YlOrRd",
        colorbar_title=colorbar_title,
        customdata=map_customdata,
        hovertemplate=map_hovertemplate,
    )
)
state_map.update_layout(
    geo={
        "scope": "usa",
        "projection_type": "albers usa",
        "showlakes": True,
        "lakecolor": "rgb(255, 255, 255)",
    },
    margin={"r": 0, "t": 10, "l": 0, "b": 0},
)

map_version = st.session_state.get("state_map_version", 0)
map_selection = st.plotly_chart(
    state_map,
    width="stretch",
    key=f"state_map_{data_view}_{map_version}",
    on_select="rerun",
    selection_mode="points",
)
selected_points = map_selection.get("selection", {}).get("points", [])
selected_state = (
    selected_points[-1]["customdata"][0] if selected_points else None
)

if selected_state is not None:
    if selected_state not in STATE_CODES:
        st.error(f"Unexpected state selected on map: {selected_state}")
        st.stop()
    st.info(f"Dashboard filtered to {selected_state.title()}.")
    if st.button("Clear state filter"):
        st.session_state["state_map_version"] = map_version + 1
        st.rerun()
    filtered_events = events.loc[events["state_name"] == selected_state]
else:
    filtered_events = events

if data_view == "Injuries":
    total_events = len(filtered_events)
    harmful_events = int(filtered_events["caused_harm"].sum())
    harm_rate = (
        100 * filtered_events["caused_harm"].mean() if total_events else 0
    )
    col1, col2, col3 = st.columns(3)
    col1.metric("Total events", f"{total_events:,}")
    col2.metric("Events with deaths or injuries", f"{harmful_events:,}")
    col3.metric("Overall harm rate", f"{harm_rate:.1f}%")

    summary = summarize_injuries(filtered_events, minimum_events)
    if summary.empty:
        st.warning("No event types meet that minimum record count.")
    else:
        chart = summary.head(number_to_show).sort_values("probability")
        figure = go.Figure(
            go.Bar(
                x=chart["probability"] * 100,
                y=chart["event_type"],
                orientation="h",
                error_x={
                    "type": "data",
                    "symmetric": False,
                    "array": (
                        (chart["ci_upper"] - chart["probability"]) * 100
                    ).tolist(),
                    "arrayminus": (
                        (chart["probability"] - chart["ci_lower"]) * 100
                    ).tolist(),
                },
                customdata=chart[["events", "harmful_events"]].to_numpy(),
                hovertemplate=(
                    "%{y}<br>Harm probability: %{x:.1f}%"
                    "<br>Events: %{customdata[0]}"
                    "<br>Events with harm: %{customdata[1]:,}<extra></extra>"
                ),
            )
        )
        figure.update_layout(
            title="Event types with the highest observed harm probability",
            xaxis_title="Events with deaths or injuries (%)",
            yaxis_title="",
        )
        st.plotly_chart(figure, width="stretch")

        table = summary.head(number_to_show).copy()
        for column in ("probability", "ci_lower", "ci_upper"):
            table[column] = (100 * table[column]).round(1)
        table = table.rename(
            columns={
                "event_type": "Event type",
                "events": "Events",
                "harmful_events": "Events with harm",
                "probability": "Harm probability (%)",
                "ci_lower": "95% CI lower (%)",
                "ci_upper": "95% CI upper (%)",
            }
        )
        st.dataframe(table, hide_index=True, width="stretch")
else:
    total_events = len(filtered_events)
    property_total = filtered_events["property_damage"].sum()
    crop_total = filtered_events["crop_damage"].sum()
    col1, col2, col3 = st.columns(3)
    col1.metric("Total events", f"{total_events:,}")
    col2.metric("Property damage", f"${property_total:,.0f}")
    col3.metric("Crop damage", f"${crop_total:,.0f}")

    summary = summarize_damage(filtered_events, minimum_events)
    if summary.empty:
        st.warning("No event types meet that minimum record count.")
    else:
        chart = summary.head(number_to_show).sort_values("total_damage")
        figure = go.Figure()
        figure.add_trace(
            go.Bar(
                x=chart["property_damage"],
                y=chart["event_type"],
                orientation="h",
                name="Property damage",
                marker_color="steelblue",
                hovertemplate="%{y}<br>Property damage: $%{x:,.0f}<extra></extra>",
            )
        )
        figure.add_trace(
            go.Bar(
                x=chart["crop_damage"],
                y=chart["event_type"],
                orientation="h",
                name="Crop damage",
                marker_color="darkorange",
                hovertemplate="%{y}<br>Crop damage: $%{x:,.0f}<extra></extra>",
            )
        )
        figure.update_layout(
            barmode="stack",
            title="Event types with the highest reported damage",
            xaxis_title="Reported damage ($)",
            xaxis_tickprefix="$",
            xaxis_tickformat="~s",
            yaxis_title="",
            legend_title="Damage category",
        )
        st.plotly_chart(figure, width="stretch")

        table = summary.head(number_to_show).copy()
        for column in ("property_damage", "crop_damage", "total_damage"):
            table[column] = table[column].map(lambda value: f"${value:,.2f}")
        table = table.rename(
            columns={
                "event_type": "Event type",
                "events": "Events",
                "property_damage": "Property damage",
                "crop_damage": "Crop damage",
                "total_damage": "Total damage",
            }
        )
        st.dataframe(table, hide_index=True, width="stretch")
