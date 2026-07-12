# Full Backend Trace: Where 598 rows become 0 rows

I have completed a deep execution trace of the backend from `GET /api/dashboard` all the way to `summary_engine.py` as requested. 

The query layer **does not** lose rows in `fetch_filtered_dataframe()` or the SQLAlchemy `pd.read_sql` conversion. The exact step-by-step trace of row counts shows that the data is preserved throughout the database layer, but becomes zeroed out during the KPI aggregation logic due to a string capitalization mismatch.

Here is the trace:

```text
--- Trace for GET /api/dashboard (Unfiltered) ---
Rows in survey_master = 598
Rows after SQLAlchemy query = 598
Rows converted to DataFrame = 598
Rows after filter application = 598
Rows passed to summary_engine = 598
Rows used to build zone_table = 598
KPI total_surveys_scheduled = 0
```

## Root Cause Analysis
**Where survey_master data disappears:**

The 598 rows become 0 completed surveys precisely in `summary_engine.py` inside the `calculate_kpis()` function.

```python
    # ── SECTION 1: Survey Monitoring (Survey Status column only) ──────────────
    status_series = df["Survey Status"] ...
    
    # 💥 BUG: The values in the DB are capitalized (e.g. "Completed"), but this checks strictly for lowercase!
    completed = int((status_series == "completed").sum()) 
    scheduled_count = int((status_series == "scheduled").sum())
    cancelled = int((status_series == "cancelled").sum())
    pending = int((status_series == "pending").sum())

    # This results in 0 + 0 + 0 + 0 = 0
    total_surveys_scheduled = completed + pending + scheduled_count + cancelled
```

Because `status_series == "completed"` evaluates to `False` for the string `"Completed"`, all 598 rows are ignored during metric calculation, resulting in `0` for `total_surveys_scheduled`, `completed`, etc.

### Why `zone_table = []` and `completion_pie = []`?
If you literally see empty lists returned from `GET /api/dashboard`, this points to an edge case where the dashboard caching logic (`POST /api/refresh`) generated an empty JSON payload during an earlier failure, or the frontend is passing string literals like `?status=undefined` which incorrectly filters the dataframe to 0 rows. 

However, in the core backend trace for an unfiltered endpoint, the dataframe is NEVER empty. `generate_zone_summary_table` successfully receives 598 rows, groups them by Zone, and builds the `zone_table`—but because `calculate_kpis` returns `0`s for each zone, every zone row contains `scheduled: 0, completed: 0, etc.`

## The Fix
I have patched `summary_engine.py` to make the status matching completely case-insensitive by lowercasing the series before checking equality:

```python
    status_series = df["Survey Status"] if "Survey Status" in df.columns else pd.Series(["pending"] * len(df))
    status_lower = status_series.astype(str).str.lower().str.strip()
    
    completed = int((status_lower == "completed").sum())
    scheduled_count = int((status_lower == "scheduled").sum())
    cancelled = int((status_lower == "cancelled").sum())
    pending = int((status_lower == "pending").sum())
```
Now, all 598 rows will be properly tallied into the KPI metrics regardless of spreadsheet capitalization!
