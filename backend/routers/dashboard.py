from fastapi import APIRouter, Query, HTTPException, Response
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any, Tuple
import io
import os
import re
import pandas as pd
from backend.config.config import settings
from backend.models.models import (
    DashboardResponse, FilterOptions, KPIMetrics, ZoneTableRow, ROTableRow, PIUTableRow,
    ProjectTableRow, ChartData, SurveyRecordDetail, WeekOption,
    SettingsResponse, SettingsUpdateRequest, ConnectionTestRequest, ConnectionTestResponse
)
from backend.services import google_sheet_reader, summary_engine, week_engine, analytics
import logging

logger = logging.getLogger("nhai_dashboard")

router = APIRouter(prefix="/api")

def normalize_ro_name(name: str) -> str:
    """
    Cleans and normalizes RO Name to a canonical form for matching.
    """
    if not name or pd.isna(name):
        return ""
    val = str(name).lower().strip()
    
    # Remove prefix 'ro '
    if val.startswith("ro "):
        val = val[3:].strip()
        
    # Collapse spaces
    val = re.sub(r'\s+', ' ', val)
    
    # Handle brackets (extract text before bracket or normalize)
    val = re.sub(r'\(.*?\)', '', val).strip()
    
    # Handle specific manual aliases
    if "banglore" in val or "bangalore" in val or "bengaluru" in val:
        return "bengaluru"
    if "thiruvananthapuram" in val or "kerala" in val:
        return "kerala"
    if "up west" in val:
        return "up west"
    if "up east" in val:
        return "up east"
    if "chittoor" in val:
        return "vijayawada"
        
    return val

def get_filtered_dataset(
    year: Optional[int] = None,
    month: Optional[str] = None,
    week_label: Optional[str] = None,
    zone: Optional[str] = None,
    ro: Optional[str] = None,
    piu: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns compiled master DataFrames from memory cache, then applies filters in-memory.
    All filtering is done purely in-memory - NO re-reading Google Sheets per request.
    """
    if not settings.GOOGLE_SHEET_URL or not settings.GOOGLE_SHEET_URL.strip():
        raise HTTPException(
            status_code=412,
            detail="No Google Spreadsheet configured. Please configure your spreadsheet."
        )

    try:
        # Load compiled master DataFrames from in-memory cache (instant - no network call if cached)
        df_details, df_surveys = google_sheet_reader.get_compiled_data()
    except Exception as e:
        logger.error(f"Error loading compiled data: {e}")
        raise HTTPException(status_code=412, detail=str(e))

    if df_surveys.empty:
        return df_details, df_surveys

    df_filtered = df_surveys.copy()

    # Filter by Year (precomputed column)
    if year:
        if "Year" in df_filtered.columns:
            df_filtered = df_filtered[df_filtered["Year"] == year]

    # Filter by Month (precomputed column)
    if month and month.strip():
        if "Month" in df_filtered.columns:
            df_filtered = df_filtered[df_filtered["Month"].astype(str).str.lower() == month.lower().strip()]

    # Filter by Week Label (precomputed column)
    if week_label and week_label.strip():
        if "Week Label" in df_filtered.columns:
            df_filtered = df_filtered[df_filtered["Week Label"].astype(str).str.strip() == week_label.strip()]
        else:
            # Fallback: old date-range filter
            weeks_list = week_engine.get_unique_weeks(df_surveys)
            matched_week = next((w for w in weeks_list if w["label"].strip() == week_label.strip()), None)
            if matched_week:
                df_filtered = week_engine.filter_by_week(df_filtered, matched_week["start"], matched_week["end"])

    # Filter by Zone
    if zone and zone.strip():
        df_filtered = df_filtered[df_filtered["Zone"].astype(str).str.lower() == zone.lower().strip()]

    # Filter by RO Name
    if ro and ro.strip():
        df_filtered = df_filtered[df_filtered["RO Name"].astype(str).str.lower() == ro.lower().strip()]

    # Filter by PIU Name
    if piu and piu.strip():
        df_filtered = df_filtered[df_filtered["PIU Name"].astype(str).str.lower() == piu.lower().strip()]

    # Filter by Survey Status
    if status and status.strip():
        df_filtered = df_filtered[df_filtered["Survey Status"].astype(str).str.lower() == status.lower().strip()]

    # Search Filter
    if search and search.strip():
        q = search.lower().strip()
        mask = (
            df_filtered["Project Name"].astype(str).str.lower().str.contains(q, na=False) |
            df_filtered["UPC Code"].astype(str).str.lower().str.contains(q, na=False) |
            df_filtered["Survey ID"].astype(str).str.lower().str.contains(q, na=False) |
            df_filtered["RO Name"].astype(str).str.lower().str.contains(q, na=False) |
            df_filtered.get("PIU Name", pd.Series(dtype=str)).astype(str).str.lower().str.contains(q, na=False)
        )
        df_filtered = df_filtered[mask]

    return df_details, df_filtered

# --- ENDPOINTS ---

@router.get("/filters", response_model=FilterOptions)
def get_filters():
    """
    Returns Year/Month/Week hierarchy, zones (with provider), ROs, and PIUs from in-memory cache.
    """
    if not settings.GOOGLE_SHEET_URL or not settings.GOOGLE_SHEET_URL.strip():
        raise HTTPException(
            status_code=412,
            detail="No Google Spreadsheet configured. Please configure your spreadsheet."
        )
    try:
        df_details, df_surveys = google_sheet_reader.get_compiled_data()

        if df_surveys.empty:
            return FilterOptions(years=[], months=[], weeks=[], zones=[], ros=[], pius=[], statuses=[])

        # Build Year/Month/Week hierarchy from precomputed columns
        def get_col(col: str, df: pd.DataFrame):
            if col not in df.columns:
                return pd.Series(dtype=object)
            return df[col].dropna()

        # Unique sorted years
        year_vals = get_col("Year", df_surveys)
        
        def is_valid_year(y):
            s = str(y).strip().lower()
            if s in ["nan", "unknown", "none", "", "0", "0.0"]: return False
            try: return int(float(s)) > 2000
            except ValueError: return False
            
        years = sorted(list(set(int(float(y)) for y in year_vals.unique() if is_valid_year(y))))

        # Ordered calendar months present in data
        month_order = ["January","February","March","April","May","June",
                       "July","August","September","October","November","December"]
        month_vals = get_col("Month", df_surveys)
        months_present = set(str(m).strip() for m in month_vals.unique() if str(m).strip() not in ["nan", ""])
        months = [m for m in month_order if m in months_present]

        # Build WeekOption list enriched with year and month
        if "Week Label" in df_surveys.columns and "Week Monday" in df_surveys.columns:
            week_df = df_surveys[["Week Monday", "Week Label", "Year", "Month"]].dropna(subset=["Week Monday"])
            week_df = week_df.drop_duplicates(subset=["Week Monday"]).sort_values("Week Monday")
            weeks = []
            for _, row in week_df.iterrows():
                mon_str = str(row["Week Monday"]).strip()
                try:
                    from datetime import datetime, timedelta
                    mon = datetime.strptime(mon_str, "%Y-%m-%d")
                    sun = mon + timedelta(days=6)
                    weeks.append(WeekOption(
                        label=str(row["Week Label"]),
                        start=mon_str,
                        end=sun.strftime("%Y-%m-%d"),
                        year=int(row["Year"]),
                        month=str(row["Month"])
                    ))
                except Exception:
                    pass
        else:
            raw_weeks = week_engine.get_unique_weeks(df_surveys)
            weeks = [WeekOption(label=w["label"], start=w["start"], end=w["end"], year=0, month="") for w in raw_weeks]

        # Unique list helper
        def get_unique_list(col: str, df: pd.DataFrame = df_surveys) -> List[str]:
            if col not in df.columns:
                return []
            vals = df[col].dropna().unique()
            return sorted([str(v).strip() for v in vals if str(v).strip() not in ["", "nan"]])

        # Zones enriched with provider name
        zone_provider_map: Dict[str, str] = {}
        if "Zone" in df_surveys.columns and "DAS Provider Name" in df_surveys.columns:
            for _, row in df_surveys[["Zone", "DAS Provider Name"]].dropna(subset=["Zone"]).iterrows():
                z = str(row["Zone"]).strip()
                p = str(row["DAS Provider Name"]).strip()
                if z and z not in zone_provider_map and p not in ["", "nan"]:
                    zone_provider_map[z] = p
        raw_zones = get_unique_list("Zone")
        zones = raw_zones  # Keep as plain zone names; provider shown in UI via zone_provider_map

        ros = get_unique_list("RO Name")
        # PIUs from Project Details metadata sheet if available, else from surveys
        if df_details is not None and not df_details.empty and "PIU Name" in df_details.columns:
            pius = get_unique_list("PIU Name", df_details)
        else:
            pius = get_unique_list("PIU Name")
        statuses = get_unique_list("Survey Status")

        return FilterOptions(
            years=years,
            months=months,
            weeks=weeks,
            zones=zones,
            ros=ros,
            pius=pius,
            statuses=statuses
        )
    except Exception as e:
        logger.error(f"Error compiling filter options: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch filter options: {e}")

@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    year: Optional[int] = Query(None),
    month: Optional[str] = Query(None),
    week_label: Optional[str] = Query(None),
    zone: Optional[str] = Query(None),
    ro: Optional[str] = Query(None),
    piu: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """
    Generates summary KPIs, Zone comparisons table, and chart datasets based on active filters.
    All filtering is done in-memory from the compiled cache - instant response on filter change.
    """
    try:
        _, df_filtered = get_filtered_dataset(
            year=year, month=month, week_label=week_label,
            zone=zone, ro=ro, piu=piu, status=status, search=search
        )

        print("\n=== DIAGNOSTICS BEFORE generate_zone_summary_table ===")
        bad = df_filtered[~df_filtered["Zone"].isin(["A", "B", "C", "D", "E", "A Zone", "B Zone", "C Zone", "D Zone", "E Zone"])]
        print("Records where Zone is invalid:")
        cols = ["UPC Code", "Project Name", "RO Worksheet Name", "PIU Name", "RO Name", "Zone", "Scheduled Survey Date"]
        avail_cols = [c for c in cols if c in bad.columns]
        print(bad[avail_cols].to_string())
        
        print("\nUnique Zones in df_filtered:")
        if "Zone" in df_filtered.columns:
            print(df_filtered["Zone"].unique())
        
        print("\nRecords where Zone is empty, 'Zone', or NaN:")
        if "Zone" in df_filtered.columns:
            empty_zones = df_filtered[df_filtered["Zone"].isin(["", "Zone"]) | df_filtered["Zone"].isna()]
            print(empty_zones[avail_cols].to_string())
        print("====================================================\n")

        kpis = summary_engine.calculate_kpis(df_filtered)
        zone_table = summary_engine.generate_zone_summary_table(df_filtered)

        charts = {
            "completion_pie": analytics.get_completion_pie_data(df_filtered),
            "zone_comparison": analytics.get_zone_comparison_data(df_filtered),
            "weekly_trend": analytics.get_weekly_trend_data(df_filtered),
            "delay_distribution": analytics.get_delay_distribution_data(df_filtered),
            "provider_performance": analytics.get_provider_performance_data(df_filtered)
        }

        return DashboardResponse(
            kpis=KPIMetrics(**kpis),
            zone_table=[ZoneTableRow(**row) for row in zone_table],
            charts=ChartData(**charts)
        )
    except Exception as e:
        logger.error(f"Error compiling dashboard data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch dashboard data: {e}")

@router.get("/drilldown/zone/{zone_name}", response_model=List[ROTableRow])
def get_zone_drilldown(
    zone_name: str,
    year: Optional[int] = Query(None),
    month: Optional[str] = Query(None),
    week_label: Optional[str] = Query(None),
    piu: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """
    Returns lists of ROs within a given zone.
    """
    try:
        _, df_filtered = get_filtered_dataset(
            year=year, month=month, week_label=week_label,
            zone=zone_name, piu=piu, status=status, search=search
        )
        ro_table = summary_engine.generate_ro_summary_table(df_filtered)
        return [ROTableRow(**row) for row in ro_table]
    except Exception as e:
        logger.error(f"Error compiling zone drilldown for {zone_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch zone drilldown data.")

@router.get("/drilldown/ro/{ro_name}", response_model=List[PIUTableRow])
def get_ro_drilldown(
    ro_name: str,
    year: Optional[int] = Query(None),
    month: Optional[str] = Query(None),
    week_label: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """
    Returns list of PIUs under a given RO.
    """
    try:
        _, df_filtered = get_filtered_dataset(
            year=year, month=month, week_label=week_label,
            ro=ro_name, status=status, search=search
        )
        piu_table = summary_engine.generate_piu_summary_table(df_filtered)
        return [PIUTableRow(**row) for row in piu_table]
    except Exception as e:
        logger.error(f"Error compiling RO drilldown for {ro_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch RO drilldown data.")

@router.get("/drilldown/piu/{piu_name}", response_model=List[ProjectTableRow])
def get_piu_drilldown(
    piu_name: str,
    year: Optional[int] = Query(None),
    month: Optional[str] = Query(None),
    week_label: Optional[str] = Query(None),
    ro: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """
    Returns list of Projects under a given PIU.
    """
    try:
        _, df_filtered = get_filtered_dataset(
            year=year, month=month, week_label=week_label,
            ro=ro, piu=piu_name, status=status, search=search
        )
        project_table = summary_engine.generate_project_summary_table(df_filtered)
        return [ProjectTableRow(**row) for row in project_table]
    except Exception as e:
        logger.error(f"Error compiling PIU drilldown for {piu_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch PIU drilldown data.")

@router.get("/drilldown/project/{upc_code}", response_model=List[SurveyRecordDetail])
def get_project_drilldown(
    upc_code: str,
    week_label: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """
    Returns list of detailed survey records for a given project UPC.
    """
    try:
        # Filter strictly by UPC Code
        _, df_filtered = get_filtered_dataset(
            week_label=week_label, status=status
        )
        
        if df_filtered.empty:
            return []
            
        df_proj = df_filtered[df_filtered["UPC Code"] == upc_code]
        
        records = []
        for _, row in df_proj.iterrows():
            # Pad/Coerce missing values to match schema
            record_dict = row.to_dict()
            
            # Numeric coercions
            record_dict["mcw_length_surveyed"] = pd.to_numeric(row.get("MCW Length Surveyed"), errors="coerce")
            if pd.isna(record_dict["mcw_length_surveyed"]):
                record_dict["mcw_length_surveyed"] = 0.0
                
            record_dict["sr_length_surveyed"] = pd.to_numeric(row.get("SR Length Surveyed"), errors="coerce")
            if pd.isna(record_dict["sr_length_surveyed"]):
                record_dict["sr_length_surveyed"] = 0.0
                
            record_dict["ir_count"] = pd.to_numeric(row.get("IR Count"), errors="coerce")
            if pd.isna(record_dict["ir_count"]):
                record_dict["ir_count"] = 0
            else:
                record_dict["ir_count"] = int(record_dict["ir_count"])
                
            record_dict["delay_d1"] = pd.to_numeric(row.get("Delay D1"), errors="coerce")
            if pd.isna(record_dict["delay_d1"]):
                record_dict["delay_d1"] = 0.0
                
            record_dict["delay_d2"] = pd.to_numeric(row.get("Delay D2"), errors="coerce")
            if pd.isna(record_dict["delay_d2"]):
                record_dict["delay_d2"] = 0.0
                
            record_dict["total_delay"] = pd.to_numeric(row.get("Total Delay"), errors="coerce")
            if pd.isna(record_dict["total_delay"]):
                record_dict["total_delay"] = 0.0
                
            record_dict["defects_reported"] = pd.to_numeric(row.get("Defects Reported"), errors="coerce")
            if pd.isna(record_dict["defects_reported"]):
                record_dict["defects_reported"] = 0
            else:
                record_dict["defects_reported"] = int(record_dict["defects_reported"])
                
            record_dict["precision_score"] = pd.to_numeric(row.get("Precision Score"), errors="coerce")
            if pd.isna(record_dict["precision_score"]):
                record_dict["precision_score"] = 0.0
                
            record_dict["recall_score"] = pd.to_numeric(row.get("Recall Score"), errors="coerce")
            if pd.isna(record_dict["recall_score"]):
                record_dict["recall_score"] = 0.0
                
            # Replace remaining pandas NaNs with empty string
            for key, val in list(record_dict.items()):
                if pd.isna(val):
                    record_dict[key] = ""
                    
            # Map camelCase to snake_case matching schema
            mapping = {
                "Zone": "zone",
                "RO Name": "ro_name",
                "PIU Name": "piu_name",
                "Project Name": "project_name",
                "UPC Code": "upc_code",
                "Survey ID": "survey_id",
                "Scheduled Survey Date": "scheduled_survey_date",
                "Actual Survey Date": "actual_survey_date",
                "Survey Status": "survey_status",
                "Remarks": "remarks",
                "Raw Data Submission Date": "raw_data_submission_date",
                "MCW Length Surveyed": "mcw_length_surveyed",
                "SR Length Surveyed": "sr_length_surveyed",
                "IR Count": "ir_count",
                "Comments": "comments",
                "Report Submission Scheduled Date": "report_submission_scheduled_date",
                "Report Submission Actual Date": "report_submission_actual_date",
                "Delay D1": "delay_d1",
                "Report Submission Status": "report_submission_status",
                "Discrepancy Date": "discrepancy_date",
                "Final Report Submission Scheduled Date": "final_report_submission_scheduled_date",
                "Final Report Submission Actual Date": "final_report_submission_actual_date",
                "Final Report Submission Status": "final_report_submission_status",
                "Delay D2": "delay_d2",
                "Total Delay": "total_delay",
                "Defects Reported": "defects_reported",
                "Precision Score": "precision_score",
                "Recall Score": "recall_score",
                "Interim Acceptance Date": "interim_acceptance_date",
                "Validation Date": "validation_date",
                "Survey Form Link": "survey_form_link",
                "Raw Video Link": "raw_video_link",
                "Processed Video Link": "processed_video_link",
                "Final Survey Report Link": "final_survey_report_link",
                "Assessed Report Link": "assessed_report_link",
                "PIU Report Link": "piu_report_link"
            }
            
            clean_rec = {}
            for col_name, schema_name in mapping.items():
                clean_rec[schema_name] = record_dict.get(col_name, record_dict.get(schema_name, ""))
                
            records.append(SurveyRecordDetail(**clean_rec))
            
        return records
    except Exception as e:
        logger.error(f"Error compiling project details for {upc_code}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch project details: {e}")

@router.post("/refresh")
def refresh_cache():
    """
    Clears cache and immediately fetches the latest Google Spreadsheet.
    """
    try:
        google_sheet_reader.clear_cache()
        google_sheet_reader.get_all_data(force_refresh=True)
        return {"status": "success", "message": "Spreadsheet loaded and cache pre-populated successfully."}
    except Exception as e:
        logger.error(f"Error on cache refresh: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# --- SETTINGS ENDPOINTS ---

@router.get("/settings", response_model=SettingsResponse)
def get_app_settings():
    return SettingsResponse(
        google_sheet_url=settings.GOOGLE_SHEET_URL,
        google_credentials_file=settings.GOOGLE_CREDENTIALS_FILE,
        google_api_key=settings.GOOGLE_API_KEY,
        cache_expiry_seconds=settings.CACHE_EXPIRY_SECONDS
    )

def save_to_env(url: str, creds: Optional[str], expiry: int, api_key: Optional[str]):
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(backend_dir, ".env")
    
    content = f"""GOOGLE_SHEET_URL={url}
GOOGLE_CREDENTIALS_FILE={creds if creds else ''}
CACHE_EXPIRY_SECONDS={expiry}
GOOGLE_API_KEY={api_key if api_key else ''}
"""
    with open(env_path, "w") as f:
        f.write(content)

@router.post("/settings", response_model=SettingsResponse)
def update_app_settings(payload: SettingsUpdateRequest):
    try:
        # 1. Test configuration first
        google_sheet_reader.test_connection_params(
            url=payload.google_sheet_url,
            creds_file=payload.google_credentials_file,
            api_key=payload.google_api_key
        )
        
        # 2. Write to disk
        save_to_env(
            url=payload.google_sheet_url,
            creds=payload.google_credentials_file,
            expiry=payload.cache_expiry_seconds,
            api_key=payload.google_api_key
        )
        
        # 3. Reload settings
        settings.GOOGLE_SHEET_URL = payload.google_sheet_url
        settings.GOOGLE_CREDENTIALS_FILE = payload.google_credentials_file
        settings.GOOGLE_API_KEY = payload.google_api_key
        settings.CACHE_EXPIRY_SECONDS = payload.cache_expiry_seconds
        
        # 4. Invalidate cache and sync metadata and Project Details immediately (lazy loading)
        google_sheet_reader.clear_cache()
        google_sheet_reader.get_spreadsheet_metadata(force_refresh=True)
        google_sheet_reader.get_worksheet_data("Project Details", force_refresh=True)
        
        return get_app_settings()
    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/settings/test-connection", response_model=ConnectionTestResponse)
def test_connection(payload: ConnectionTestRequest):
    try:
        res = google_sheet_reader.test_connection_params(
            url=payload.google_sheet_url,
            creds_file=payload.google_credentials_file,
            api_key=payload.google_api_key
        )
        return ConnectionTestResponse(
            status="Success",
            spreadsheet_name=res["spreadsheet_name"],
            worksheets_count=res["worksheets_count"],
            sheet_names=res["sheet_names"]
        )
    except Exception as e:
        logger.error(f"Test connection failure: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/export/csv")
def export_csv(
    week_label: Optional[str] = Query(None),
    zone: Optional[str] = Query(None),
    ro: Optional[str] = Query(None),
    piu: Optional[str] = Query(None),
    provider: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """
    Generates and streams a CSV download of the current filtered survey records dataset.
    """
    try:
        _, df_filtered = get_filtered_dataset(
            week_label=week_label, zone=zone, ro=ro, piu=piu, provider=provider, status=status, search=search
        )
        
        # Remove internal columns
        if "RO Worksheet Name" in df_filtered.columns:
            df_filtered.drop(columns=["RO Worksheet Name"], inplace=True)
            
        stream = io.StringIO()
        df_filtered.to_csv(stream, index=False)
        response = Response(
            content=stream.getvalue(),
            media_type="text/csv"
        )
        response.headers["Content-Disposition"] = "attachment; filename=nhai_filtered_surveys.csv"
        return response
    except Exception as e:
        logger.error(f"Error exporting CSV: {e}")
        raise HTTPException(status_code=500, detail="Failed to export CSV file")

@router.get("/export/excel")
def export_excel(
    week_label: Optional[str] = Query(None),
    zone: Optional[str] = Query(None),
    ro: Optional[str] = Query(None),
    piu: Optional[str] = Query(None),
    provider: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """
    Generates and streams an Excel download of the current filtered dataset.
    """
    try:
        _, df_filtered = get_filtered_dataset(
            week_label=week_label, zone=zone, ro=ro, piu=piu, provider=provider, status=status, search=search
        )
        
        if "RO Worksheet Name" in df_filtered.columns:
            df_filtered.drop(columns=["RO Worksheet Name"], inplace=True)
            
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_filtered.to_excel(writer, index=False, sheet_name="Filtered Surveys")
            
        response = Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response.headers["Content-Disposition"] = "attachment; filename=nhai_filtered_surveys.xlsx"
        return response
    except Exception as e:
        logger.error(f"Error exporting Excel: {e}")
        raise HTTPException(status_code=500, detail="Failed to export Excel file")
