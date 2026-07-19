import json
import logging
import sys
from collections import Counter
from sqlalchemy.orm import Session

# Setup logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

from backend.services.db import get_db
from backend.models.schema import SurveyMaster, DashboardCache
from backend.routers.dashboard import get_filters, get_dashboard

def investigate():
    db: Session = next(get_db())
    
    print("\n--- 1. Checking Database Records ---")
    recovered = db.query(SurveyMaster).filter(
        SurveyMaster.zone.isnot(None), 
        SurveyMaster.zone != ''
    ).all()
    print(f"Total rows in DB with a Zone: {len(recovered)}")
    
    print("\n--- 2. Checking Dashboard Cache ---")
    cache = db.query(DashboardCache).filter(DashboardCache.cache_key == 'zone_summary').first()
    if cache:
        cache_data = json.loads(cache.cache_value)
        # Zone summary looks like [{"zone": "East", "metrics": {...}}, {"zone": "", "metrics": {...}}]
        zones_in_cache = [row.get("zone", "") for row in cache_data]
        print("Zones stored in the pre-computed Cache:")
        print(zones_in_cache)
        if "" in zones_in_cache or None in zones_in_cache:
            print("WARNING: Blank zone exists in Cache!")
            
    print("\n--- 3. Checking API Responses ---")
    try:
        filters = get_filters(zone=None, ro=None, db=db)
        print("Zones from /api/filters (Queries SurveyMaster directly):")
        print(filters.zones)
    except Exception as e:
        print(f"Error calling get_filters: {e}")
        
    try:
        # Pass all required query params as None
        dashboard = get_dashboard(
            year=None, month=None, week_label=None, zone=None, 
            ro=None, piu=None, status=None, search=None, db=db
        )
        print("\nZones from /api/dashboard ZoneTable (Queries DashboardCache):")
        dashboard_zones = [z.zone for z in dashboard.zone_table]
        print(dashboard_zones)
    except Exception as e:
        print(f"Error calling get_dashboard: {e}")
        
    print("\n--- Conclusion ---")
    print("Metadata recovery mutates 'valid_records', which ARE persisted to SurveyMaster.")
    print("Therefore /api/filters (which reads SurveyMaster) shows the recovered Zones.")
    print("However, the Dashboard Cache is built from 'df_merged' BEFORE metadata recovery occurs.")
    print("Therefore /api/dashboard (which reads the Cache) serves the old un-recovered values, resulting in blank Zones in the UI.")

if __name__ == '__main__':
    investigate()
