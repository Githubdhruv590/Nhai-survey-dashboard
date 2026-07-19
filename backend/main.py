import os
import logging
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone
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

scheduler = None

def scheduled_refresh_job():
    from backend.services.db import SessionLocal
    from backend.services.refresh_pipeline import run_refresh_pipeline, ConcurrentRefreshException
    db = SessionLocal()
    try:
        run_refresh_pipeline(db, trigger_source="Scheduled")
    except ConcurrentRefreshException:
        logger.info("Scheduled refresh skipped: Another refresh is already running.")
    except Exception as e:
        logger.error(f"Scheduled refresh failed: {e}")
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing NHAI Survey Dashboard Backend...")
    # Initialize DB tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")
    
    global scheduler
    scheduler = BackgroundScheduler(timezone=timezone('Asia/Kolkata'))
    # Run at 12:05 AM and 12:05 PM IST
    scheduler.add_job(scheduled_refresh_job, 'cron', hour=0, minute=5)
    scheduler.add_job(scheduled_refresh_job, 'cron', hour=12, minute=5)
    import datetime
    scheduler.add_job(scheduled_refresh_job, 'date', run_date=datetime.datetime.now(timezone('Asia/Kolkata')) + datetime.timedelta(seconds=15))
    scheduler.start()
    logger.info("APScheduler started with jobs for 12:05 AM and 12:05 PM IST.")
    
    yield
    
    # Shutdown
    if scheduler:
        scheduler.shutdown()
        logger.info("APScheduler stopped.")

app = FastAPI(
    title="NHAI Executive Survey Monitoring Dashboard API",
    version="4.0.0",
    description="API for dynamically reading road survey information from PostgreSQL Database.",
    lifespan=lifespan
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

@app.get("/scheduler_status")
def scheduler_status():
    global scheduler
    if not scheduler:
        return {"status": "not running", "jobs": []}
    
    jobs = []
    try:
        for job in scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": str(job.next_run_time),
                "trigger": str(job.trigger)
            })
    except Exception as e:
        return {"status": "error", "message": str(e)}
        
    return {"status": "running", "jobs": jobs, "pid": os.getpid()}
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
        
        from datetime import timezone, timedelta
        # Get last sync time
        last_refresh = db.query(RefreshHistory).filter(RefreshHistory.status.in_(['SUCCESS', 'SUCCESS WITH WARNINGS'])).order_by(desc(RefreshHistory.ended_at)).first()
        if last_refresh and last_refresh.ended_at:
            # Render servers are in UTC. Convert explicitly to IST (UTC+05:30)
            utc_dt = last_refresh.ended_at.replace(tzinfo=timezone.utc)
            ist_dt = utc_dt + timedelta(hours=5, minutes=30)
            last_sync = ist_dt.strftime('%Y-%m-%d %I:%M %p')
        else:
            last_sync = "Never"
        
        # Get active surveys loaded
        survey_count = db.query(SurveyMaster).filter(SurveyMaster.survey_status != 'Deleted').count()
        
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

# --- Serve Frontend Static Files ---
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")

if os.path.exists(frontend_dist):
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
        
    @app.get("/{catchall:path}")
    def serve_spa(catchall: str):
        # Ignore API routes and let them 404 naturally if missing
        if catchall.startswith("api/") or catchall == "health":
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not Found")
            
        # Serve exact file if it exists (e.g. favicon.ico, logo.png)
        file_path = os.path.join(frontend_dist, catchall)
        if catchall and os.path.isfile(file_path):
            return FileResponse(file_path)
            
        # SPA Fallback: serve index.html
        index_path = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
            
        return {"error": "Frontend build not found"}
else:
    logger.warning("Frontend dist directory not found. Static files will not be served.")

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
