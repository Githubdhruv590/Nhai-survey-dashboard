from fastapi import APIRouter, Query, HTTPException, Response, Depends
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
def get_filters(
    zone: Optional[str] = Query(None),
    ro: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    try:
        # Get unique zones, ros, pius, statuses from DB
        zones = [r[0] for r in db.query(SurveyMaster.zone).distinct().all() if r[0]]
        
        ro_query = db.query(SurveyMaster.ro_name).distinct()
        if zone:
            ro_query = ro_query.filter(SurveyMaster.zone.ilike(zone))
        ros = [r[0] for r in ro_query.all() if r[0]]
        
        piu_query = db.query(SurveyMaster.piu_name).distinct()
        if zone:
            piu_query = piu_query.filter(SurveyMaster.zone.ilike(zone))
        if ro:
            piu_query = piu_query.filter(SurveyMaster.ro_name.ilike(ro))
        pius = [r[0] for r in piu_query.all() if r[0]]
        
        statuses = [r[0] for r in db.query(SurveyMaster.survey_status).distinct().all() if r[0]]
        
        # Dynamically build Year/Month/Week hierarchy from SurveyMaster dates
        from backend.services.week_engine import parse_date, get_week_boundaries, get_week_label
        
        dates_raw = [r[0] for r in db.query(SurveyMaster.scheduled_survey_date).distinct().all() if r[0]]
        
        years_set = set()
        months_set = set()
        weeks_dict = {}
        
        for d_str in dates_raw:
            dt = parse_date(d_str)
            if dt:
                years_set.add(dt.year)
                months_set.add(dt.strftime("%B"))
                
                mon, sun = get_week_boundaries(dt)
                
                # A week belongs entirely to the month in which its Monday falls
                # Ensure the Monday's month and year are available in the filters
                years_set.add(mon.year)
                months_set.add(mon.strftime("%B"))
                
                label = get_week_label(mon, sun)
                if label not in weeks_dict:
                    weeks_dict[label] = {
                        "label": label,
                        "start": mon.strftime("%Y-%m-%d"),
                        "end": sun.strftime("%Y-%m-%d"),
                        "year": mon.year,
                        "month": mon.strftime("%B")
                    }
                    
        years = sorted(list(years_set))
        
        month_order = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        months = sorted(list(months_set), key=lambda m: month_order.index(m) if m in month_order else 99)
        
        weeks_list = sorted(list(weeks_dict.values()), key=lambda x: x["start"])
        weeks = [WeekOption(**w) for w in weeks_list]
        
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
    try:
        has_filters = any([year, month, week_label, zone, ro, piu, status, search])
        
        if not has_filters:
            cached = get_dashboard_unfiltered(db)
            if cached:
                return DashboardResponse(**cached)
        
        # Dynamic calculation
        df_filtered = fetch_filtered_dataframe(db, year=year, month=month, week_label=week_label, zone=zone, ro=ro, piu=piu, status=status, search=search)
        if df_filtered.empty:
            return DashboardResponse(
                kpis=KPIMetrics(
                    total_surveys_scheduled=0,
                    scheduled=0,
                    completed=0,
                    pending=0,
                    cancelled=0,
                    completion_rate=0.0,
                    completed_surveys=0,
                    reports_expected=0,
                    reports_received=0,
                    reports_on_time=0,
                    reports_delayed=0,
                    average_delay=0.0,
                    # Legacy defaults
                    total_scheduled=0,
                    on_time_reports=0,
                    delayed_reports=0,
                    pending_reports=0,
                    maximum_delay=0.0,
                    total_surveyed_length=0.0
                ),
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
def refresh_dashboard_data(db: Session = Depends(get_db)):
    print("\n" + "="*40)
    print("REFRESH PIPELINE CALL CHAIN TRACE")
    print("1. Endpoint handling request: POST /api/refresh")
    print("2. Function executing: backend.routers.dashboard.refresh_dashboard_data")
    import inspect
    import backend.services.refresh_pipeline as rp
    import os
    print(f"3. Resolving run_refresh_pipeline(): {hasattr(rp, 'run_refresh_pipeline')}")
    print(f"4. Absolute file path of refresh_pipeline.py: {os.path.abspath(rp.__file__)}")
    
    # Check if we're somehow importing the wrong module or function
    print(f"5. Target function signature: {inspect.signature(rp.run_refresh_pipeline)}")
    print("="*40 + "\n")
    try:
        from backend.services.refresh_pipeline import ConcurrentRefreshException
        return rp.run_refresh_pipeline(db)
    except rp.ConcurrentRefreshException as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
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
