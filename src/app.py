from pathlib import Path
import sqlite3

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(page_title="Storm Event Harm Dashboard", layout="wide")
st.title("Storm Event Harm Dashboard")
st.caption("Observed probability that an event type caused deaths or injuries")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "data" / "data.db"
EVENTS_QUERY_PATH = PROJECT_ROOT / "queries" / "load_storm_events.sql"


@st.cache_data
def load_events(database_path: str) -> pd.DataFrame:
    query = EVENTS_QUERY_PATH.read_text(encoding="utf-8")
    with sqlite3.connect(database_path) as connection:
        events = pd.read_sql_query(query, connection)

    events["caused_harm"] = (events["deaths"] + events["injuries"]) > 0
    return events


def summarize_harm(events: pd.DataFrame, minimum_events: int) -> pd.DataFrame:
    summary = (
        events.groupby("event_type")
        .agg(
            events=("caused_harm", "size"),
            harmful_events=("caused_harm", "sum"),
        )
    )
    summary = summary[summary["events"] >= minimum_events].copy()
    summary["probability"] = summary["harmful_events"] / summary["events"]

    # Wilson 95% confidence intervals
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


if not DATABASE_PATH.is_file():
    st.error(f"Project database not found: {DATABASE_PATH}")
    st.stop()

events = load_events(str(DATABASE_PATH))
minimum_events = st.sidebar.number_input(
    "Minimum records per event type", min_value=1, value=30
)
number_to_show = st.sidebar.slider(
    "Event types to show", min_value=5, max_value=30, value=15
)

summary = summarize_harm(events, minimum_events)

if summary.empty:
    st.warning("No event types meet that minimum record count.")
    st.stop()

total_events = len(events)
harmful_events = int(events["caused_harm"].sum())
harm_rate = 100 * events["caused_harm"].mean()

col1, col2, col3 = st.columns(3)
col1.metric("Total events", f"{total_events:,}")
col2.metric("Events with deaths or injuries", f"{harmful_events:,}")
col3.metric("Overall harm rate", f"{harm_rate:.1f}%")

chart = summary.head(number_to_show).sort_values("probability")

fig = go.Figure(
    go.Bar(
        x=chart["probability"] * 100,
        y=chart["event_type"],
        orientation="h",
        error_x={
            "type": "data",
            "symmetric": False,
            "array": ((chart["ci_upper"] - chart["probability"]) * 100).tolist(),
            "arrayminus": ((chart["probability"] - chart["ci_lower"]) * 100).tolist(),
        },
        customdata=chart[["events", "harmful_events"]].to_numpy(),
        hovertemplate=(
            "%{y}<br>Harm probability: %{x:.1f}%"
            "<br>Events: %{customdata[0]}"
            "<br>Events with harm: %{customdata[1]}<extra></extra>"
        ),
    )
)
fig.update_layout(
    title="Event types with the highest observed harm probability",
    xaxis_title="Events with deaths or injuries (%)",
    yaxis_title="",
)
st.plotly_chart(fig, use_container_width=True)

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
st.dataframe(table, hide_index=True, use_container_width=True)