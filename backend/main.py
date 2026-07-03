import os
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.routers import dashboard
from backend.config.config import settings
from backend.services import google_sheet_reader

logger = logging.getLogger("nhai_dashboard")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="NHAI Executive Survey Monitoring Dashboard API",
    version="1.0.0",
    description="API for dynamically reading road survey information from Google Sheets and generating summaries."
)

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust to specific domains in production if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Dashboard Router
app.include_router(dashboard.router)

@app.on_event("startup")
def validate_config():
    logger.info("Initializing NHAI Survey Dashboard Backend...")
    if not settings.GOOGLE_SHEET_URL:
        logger.error("==================================================================")
        logger.error("CONFIGURATION ERROR: GOOGLE_SHEET_URL environment variable is missing!")
        logger.error("Please configure it in the .env file or use the Settings screen.")
        logger.error("Do not silently fall back to mock data.")
        logger.error("==================================================================")
        return

    try:
        from backend.services import google_sheet_reader
        # 1. Fetch metadata and detect all worksheets
        spreadsheet_name, sheet_names = google_sheet_reader.get_spreadsheet_metadata(force_refresh=True)
        print("==================================================================")
        print(f"Spreadsheet Name: {spreadsheet_name}")
        print(f"Worksheets Found: {len(sheet_names)}")
        
        _, _, auth_method = google_sheet_reader.get_auth_headers_and_params()
        logger.info(f"Authentication Method: {auth_method}")
        print("Authentication Method:")
        print(f"- {auth_method}")
        print("==================================================================")
        
        # 2. Force load every worksheet at startup and trigger compilation report
        sheets_dict = google_sheet_reader.get_all_data(force_refresh=True)
        print(f"Total worksheets loaded: {len(sheets_dict)}")
        print("==================================================================")
        
        # Calculate startup validation metrics
        from backend.services.summary_engine import compile_master_data, calculate_kpis
        _, df_merged = compile_master_data(sheets_dict)
        kpis = calculate_kpis(df_merged)
        
        print("STARTUP KPI VALIDATION VALUES:")
        print(f"  Total Surveys:              {kpis['total_scheduled']}")
        print(f"  Scheduled:                  {kpis['scheduled']}")
        print(f"  Pending:                    {kpis['pending']}")
        print(f"  Completed:                  {kpis['completed']}")
        print(f"  Delayed Reports:            {kpis['delayed_reports']}")
        
        prec_avail = "Yes" if kpis['average_precision'] is not None else "No"
        rec_avail = "Yes" if kpis['average_recall'] is not None else "No"
        disc_avail = "Yes" if kpis['discrepancies_raised'] is not None else "No"
        
        print(f"  Precision data available:   {prec_avail}")
        print(f"  Recall data available:      {rec_avail}")
        print(f"  Discrepancy data available: {disc_avail}")
        print("==================================================================")
    except Exception as e:
        logger.error(f"Startup validation failed: {e}")
        print(f"Startup validation failed: {e}")
        raise e

@app.get("/health")
def health_check():
    """
    Improved health check endpoint returning detailed connectivity status.
    """
    conn_status = google_sheet_reader.get_connection_status()
    cache_populated = len(google_sheet_reader._cache.worksheets) > 0
    
    return {
        "status": "healthy" if conn_status["status"] == "Connected" else "degraded",
        "spreadsheet_connected": conn_status["status"] == "Connected",
        "spreadsheet_name": conn_status["spreadsheet_name"],
        "worksheets_loaded": conn_status["worksheets_count"],
        "cache_status": "Populated" if cache_populated else "Empty",
        "last_sync": conn_status["last_sync_time"],
        "google_api_status": conn_status["status"],
        "error_message": conn_status["error_message"]
    }

# SPA-friendly static file serving if frontend/dist exists
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend/dist"))

if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
    
    @app.exception_handler(404)
    async def spa_fallback(request, exc):
        if request.url.path.startswith("/api"):
            return FileResponse(os.path.join(frontend_dist, "index.html"))
        return FileResponse(os.path.join(frontend_dist, "index.html"))
else:
    @app.get("/")
    def index():
        return {
            "message": "NHAI Survey API is running. Frontend static build is not present yet.",
            "api_docs": "/docs"
        }

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
