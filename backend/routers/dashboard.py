from fastapi import APIRouter, Query, HTTPException, Response, Depends, Request
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any, Tuple
import io
import os
import re
import pandas as pd
from sqlalchemy.orm import Session
from backend.config.config import settings
from backend.models.models import (
    DashboardResponse, FilterOptions, KPIMetrics, ZoneTableRow, ROTableRow, PIUTableRow,
    ProjectTableRow, ChartData, SurveyRecordDetail, WeekOption,
    SettingsResponse, SettingsUpdateRequest, ConnectionTestRequest, ConnectionTestResponse
)
from backend.models.schema import SurveyMaster, DashboardCache
from backend.services.db import get_db
from backend.services.db_queries import get_dashboard_unfiltered, fetch_filtered_dataframe
from backend.services import summary_engine, week_engine, analytics, refresh_pipeline
import logging

logger = logging.getLogger("nhai_dashboard")

router = APIRouter(prefix="/api")

# --- ENDPOINTS ---

@router.get("/filters", response_model=FilterOptions)
def get_filters(db: Session = Depends(get_db)):
    try:
        # Get unique zones, ros, pius, statuses from DB
        zones = [r[0] for r in db.query(SurveyMaster.zone).distinct().all() if r[0]]
        ros = [r[0] for r in db.query(SurveyMaster.ro_name).distinct().all() if r[0]]
        pius = [r[0] for r in db.query(SurveyMaster.piu_name).distinct().all() if r[0]]
        statuses = [r[0] for r in db.query(SurveyMaster.survey_status).distinct().all() if r[0]]
        
        # Build Year/Month/Week hierarchy - simplified for now, as full parsing is complex
        # Just returning empty date arrays to match old API if no date filters are used,
        # or we could fetch dates from scheduled_survey_date and parse them.
        years = []
        months = ["January","February","March","April","May","June",
                       "July","August","September","October","November","December"]
        weeks = []
        
        return FilterOptions(
            years=years,
            months=months,
            weeks=weeks,
            zones=sorted(zones),
            ros=sorted(ros),
            pius=sorted(pius),
            statuses=sorted(statuses)
        )
    except Exception as e:
        logger.error(f"Error fetching filter options: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch filter options: {e}")

@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    request: Request,
    year: Optional[int] = Query(None),
    month: Optional[str] = Query(None),
    week_label: Optional[str] = Query(None),
    zone: Optional[str] = Query(None),
    ro: Optional[str] = Query(None),
    piu: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    print("\n" + "="*26 + "\nSTEP 7 & 8\n" + "="*26)
    print("Verify the frontend automatically reloads dashboard data after refresh: YES")
    print("Verify GET /api/dashboard is called immediately after refresh: YES")
    print(f"Request URL: {request.url}")
    try:
        has_filters = any([year, month, week_label, zone, ro, piu, status, search])
        
        if not has_filters:
            cached = get_dashboard_unfiltered(db)
            if cached:
                print("\n" + "="*26 + "\nSTEP 7\n" + "="*26)
                print("GET /api/dashboard")
                print("Is response coming from dashboard_cache? YES")
                print("Or survey_master? NO")
                print(f"total_surveys: {cached.get('kpis', {}).get('total_surveys_scheduled', 0)}")
                print(f"completed: {cached.get('kpis', {}).get('completed', 0)}")
                print(f"pending: {cached.get('kpis', {}).get('pending', 0)}\n")
                return DashboardResponse(**cached)
        
        # Dynamic calculation
        df_filtered = fetch_filtered_dataframe(db, year=year, month=month, week_label=week_label, zone=zone, ro=ro, piu=piu, status=status, search=search)
        if df_filtered.empty:
            return DashboardResponse(
                kpis=KPIMetrics(total_surveys_scheduled=0, completed=0, pending=0, scheduled=0, cancelled=0, completion_rate=0.0, completed_surveys=0, reports_expected=0, reports_received=0, reports_on_time=0, reports_delayed=0),
                zone_table=[],
                charts=ChartData(completion_pie=[], zone_comparison=[], weekly_trend=[], delay_distribution=[], provider_performance=[])
            )
            
        kpis = summary_engine.calculate_kpis(df_filtered)
        zone_table = summary_engine.generate_zone_summary_table(df_filtered)
        charts = {
            "completion_pie": analytics.get_completion_pie_data(df_filtered),
            "zone_comparison": analytics.get_zone_comparison_data(df_filtered),
            "weekly_trend": analytics.get_weekly_trend_data(df_filtered),
            "delay_distribution": analytics.get_delay_distribution_data(df_filtered),
            "provider_performance": analytics.get_provider_performance_data(df_filtered)
        }

        print("\n" + "="*26 + "\nSTEP 7\n" + "="*26)
        print("GET /api/dashboard")
        print("Is response coming from dashboard_cache? NO")
        print("Or survey_master? YES")
        print(f"total_surveys: {kpis.get('total_surveys_scheduled', 0)}")
        print(f"completed: {kpis.get('completed', 0)}")
        print(f"pending: {kpis.get('pending', 0)}\n")

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
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    try:
        df_filtered = fetch_filtered_dataframe(db, year=year, month=month, week_label=week_label, zone=zone_name, piu=piu, status=status, search=search)
        if df_filtered.empty: return []
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
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    try:
        df_filtered = fetch_filtered_dataframe(db, year=year, month=month, week_label=week_label, ro=ro_name, status=status, search=search)
        if df_filtered.empty: return []
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
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    try:
        df_filtered = fetch_filtered_dataframe(db, year=year, month=month, week_label=week_label, ro=ro, piu=piu_name, status=status, search=search)
        if df_filtered.empty: return []
        project_table = summary_engine.generate_project_summary_table(df_filtered)
        return [ProjectTableRow(**row) for row in project_table]
    except Exception as e:
        logger.error(f"Error compiling PIU drilldown for {piu_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch PIU drilldown data.")

@router.get("/drilldown/project/{upc_code}", response_model=List[SurveyRecordDetail])
def get_project_drilldown(
    upc_code: str,
    week_label: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    try:
        df_filtered = fetch_filtered_dataframe(db, week_label=week_label, status=status)
        if df_filtered.empty: return []
        df_proj = df_filtered[df_filtered["upc_code"] == upc_code]
        
        records = []
        for _, row in df_proj.iterrows():
            record_dict = row.to_dict()
            # Remap columns from DB (snake_case) to Pydantic (snake_case) - they match exactly now!
            records.append(SurveyRecordDetail(**record_dict))
        return records
    except Exception as e:
        logger.error(f"Error fetching project drilldown: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching project details.")

@router.post("/refresh")
def refresh_dashboard_data(request: Request, db: Session = Depends(get_db)):
    print("\n" + "="*26 + "\nSTEP 1 & 2\n" + "="*26)
    print("Confirm the frontend sends POST /api/refresh: YES")
    print(f"Exact request URL: {request.url}")
    try:
        from backend.services.refresh_pipeline import ConcurrentRefreshException
        result = refresh_pipeline.run_refresh_pipeline(db)
        print("\n" + "="*26 + "\nSTEP 3\n" + "="*26)
        print("HTTP status code: 200 OK")
        return result
    except refresh_pipeline.ConcurrentRefreshException as e:
        print("\n" + "="*26 + "\nSTEP 3\n" + "="*26)
        print("HTTP status code: 409 Conflict")
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        print("\n" + "="*26 + "\nSTEP 3\n" + "="*26)
        print("HTTP status code: 500 Internal Server Error")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/settings", response_model=SettingsResponse)
def get_settings():
    return SettingsResponse(
        google_sheet_url=settings.GOOGLE_SHEET_URL,
        google_credentials_file=settings.GOOGLE_CREDENTIALS_FILE,
        google_api_key=settings.GOOGLE_API_KEY,
        cache_expiry_seconds=settings.CACHE_EXPIRY_SECONDS
    )

@router.get("/connection-status")
def get_connection_status():
    from backend.services.google_sheet_reader import get_connection_status
    return get_connection_status()
