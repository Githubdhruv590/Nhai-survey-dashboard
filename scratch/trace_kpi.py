import json
import logging
import sys
import requests
from sqlalchemy.orm import Session
from backend.services.db import get_db
from backend.models.schema import DashboardCache, SurveyMaster
from backend.routers.dashboard import get_dashboard

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

def trace_kpi():
    db: Session = next(get_db())
    
    print("\n=== STAGE 1: Canonical valid_records count after validation ===")
    # The database represents the exact output of valid_records that was persisted.
    # Exclude soft-deleted rows if they aren't part of valid_records (or maybe they are?)
    total_db = db.query(SurveyMaster).count()
    active_db = db.query(SurveyMaster).filter(SurveyMaster.survey_status != 'Deleted').count()
    print(f"Total rows in SurveyMaster (including Deleted): {total_db}")
    print(f"Active rows in SurveyMaster (excluding Deleted): {active_db}")
    
    print("\n=== STAGE 2: DataFrame row count used to build DashboardCache ===")
    # Look at the cache object to see how many rows it says it processed
    cache = db.query(DashboardCache).filter_by(cache_key="global_dashboard").first()
    if cache:
        print(f"DashboardCache.survey_count: {cache.survey_count}")
        cache_data = cache.payload
        print(f"DashboardCache payload total_surveys_scheduled: {cache_data.get('total_surveys_scheduled')}")
    else:
        print("No cache found!")
        
    print("\n=== STAGE 3: Value returned by /api/dashboard ===")
    try:
        dashboard = get_dashboard(
            year=None, month=None, week_label=None, zone=None, 
            ro=None, piu=None, status=None, search=None, db=db
        )
        print(f"API /dashboard returned total_surveys_scheduled: {dashboard.kpis.total_surveys_scheduled}")
    except Exception as e:
        print(f"Error calling get_dashboard: {e}")

    print("\n=== STAGE 4: Frontend Component (Static check) ===")
    print("Frontend reads `kpis.total_surveys_scheduled` from the API.")

if __name__ == '__main__':
    trace_kpi()
