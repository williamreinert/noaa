# NOAA Storm Events

Create or refresh the SQLite database from the 2023 Storm Events details CSV:

```powershell
python src\create_database.py
```

The script reads `src\StormEvents_details-ftp_v1.0_d2023_c20240117.csv` and
creates `data\data.db` with a `StormEvents` table. CSV columns are retained as
text except for columns guessed to be numeric, which use SQLite `INTEGER` or
`REAL`. `BEGIN_DATE_TIME` and `END_DATE_TIME` use SQLite `DATETIME` columns;
their source values are normalized to `YYYY-MM-DD HH:MM:SS`. Damage amounts
with `K`, `M`, or `B` suffixes are converted to numeric amounts, and blank
values are stored as `NULL`. Running the script again replaces the existing
`StormEvents` table with a fresh import.

Run the Streamlit dashboard from the project root with:

```powershell
python -m streamlit run src\app.py
```

Choose **Injuries** or **Property & crop damage** in the sidebar to switch the
map, metrics, event-type chart, and table. The interactive U.S. map covers the
50 states and Washington, D.C.; territories and offshore regions are excluded.
Clicking a state filters the dashboard, and **Clear state filter** returns to
all states.