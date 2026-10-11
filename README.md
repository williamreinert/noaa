# NOAA Storm Events Explorer

An interactive dashboard for exploring the **2023 NOAA Storm Events dataset**.
Compare reported deaths and injuries with property and crop damage, and see
how impacts vary across U.S. states and storm event types.

## What you can explore

- Switch between **Injuries** and **Property & crop damage**.
- Select a state on the interactive U.S. map to filter the dashboard.
- Compare state-level totals and event-type summaries.
- Set a minimum event count to focus rankings on event types with enough
  records.
- Inspect the underlying summary table, including uncertainty intervals for
  injury-related harm probabilities.

The injury view reports the observed percentage of events with at least one
death or injury. This is a descriptive statistic, not a measure of causal risk.
The map includes the 50 states and Washington, D.C.; territories and offshore
regions are omitted.

## Built with

Python · Streamlit · SQLite · pandas · Plotly

## Run locally

Requirements: Python 3.13 and the 2023 Storm Events details CSV included in
`src/`.

From the project root, create and activate a virtual environment, install
dependencies, and build the SQLite database:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python src\create_database.py
```

Start the dashboard:

```powershell
python -m streamlit run src\app.py
```

Streamlit prints a local URL (usually `http://localhost:8501`) to open in your
browser.

> **Note:** Re-running `create_database.py` replaces the `StormEvents` table in
> `data/data.db` with a fresh import from the CSV.

## Project layout

```text
noaa-1/
├── data/                 # Generated SQLite database
├── notebooks/            # Exploratory and damage analysis
├── queries/              # SQL queries used by the dashboard
├── src/
│   ├── app.py             # Streamlit dashboard
│   ├── create_database.py # CSV-to-SQLite import
│   └── StormEvents_...csv # NOAA 2023 storm-event records
└── requirements.txt
```

## Data source

The bundled CSV is the NOAA Storm Events **2023 details** file. For dataset
documentation and other years, visit the
[NOAA Storm Events Database](https://www.ncei.noaa.gov/stormevents/).
