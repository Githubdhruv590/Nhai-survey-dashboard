import os
import logging
import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.routers import dashboard
from backend.config.config import settings
from backend.models.schema import Base
from backend.services.db import engine, get_db

logger = logging.getLogger("nhai_dashboard")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="NHAI Executive Survey Monitoring Dashboard API",
    version="4.0.0",
    description="API for dynamically reading road survey information from PostgreSQL Database."
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
def startup_db():
    logger.info("Initializing NHAI Survey Dashboard Backend...")
    # Initialize DB tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")
    
    # We do NOT run an automatic refresh here. 
    # Data is refreshed exclusively via POST /api/refresh.

@app.get("/health")
def health_check(db = Depends(get_db)):
    """
    Improved health check endpoint returning detailed database connectivity status.
    """
    from backend.models.schema import RefreshHistory, SurveyMaster
    from sqlalchemy import desc
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db_status = "Connected"
        
        from datetime import timezone
        # Get last sync time
        last_refresh = db.query(RefreshHistory).filter(RefreshHistory.status == 'SUCCESS').order_by(desc(RefreshHistory.ended_at)).first()
        if last_refresh and last_refresh.ended_at:
            utc_dt = last_refresh.ended_at.replace(tzinfo=timezone.utc)
            local_dt = utc_dt.astimezone()
            last_sync = local_dt.strftime('%Y-%m-%d %I:%M %p')
        else:
            last_sync = "Never"
        
        # Get surveys loaded
        survey_count = db.query(SurveyMaster).count()
        
    except Exception as e:
        db_status = f"Disconnected: {str(e)}"
        last_sync = "Unknown"
        survey_count = 0
        
    return {
        "status": "healthy" if db_status == "Connected" else "degraded",
        "database_connected": db_status == "Connected",
        "last_sync": last_sync,
        "surveys_loaded": survey_count,
        "error_message": db_status if db_status != "Connected" else ""
    }

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
