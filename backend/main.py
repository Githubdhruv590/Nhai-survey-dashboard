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
    
    print("\n" + "="*40)
    print("FRONTEND SERVING DIAGNOSTICS")
    frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
    print(f"1. Absolute frontend_dist path: {os.path.abspath(frontend_dist)}")
    exists = os.path.exists(frontend_dist)
    print(f"2. os.path.exists(frontend_dist): {exists}")
    if not exists:
        print(f"3. os.getcwd(): {os.getcwd()}")
    print(f"4. os.path.dirname(__file__): {os.path.dirname(__file__)}")
    
    parent_dir = os.path.dirname(os.path.dirname(__file__))
    print(f"5a. Contents of parent directory ({parent_dir}):")
    try:
        print(os.listdir(parent_dir))
    except Exception as e:
        print(f"Error reading parent dir: {e}")
        
    frontend_dir = os.path.join(parent_dir, "frontend")
    print(f"5b. Contents of frontend directory ({frontend_dir}):")
    try:
        print(os.listdir(frontend_dir))
    except Exception as e:
        print(f"Error reading frontend dir: {e}")
        
    index_html = os.path.join(frontend_dist, "index.html")
    print(f"6. Final path where index.html is expected: {os.path.abspath(index_html)}")
    print("="*40 + "\n")
    
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
        
        from datetime import timezone, timedelta
        # Get last sync time
        last_refresh = db.query(RefreshHistory).filter(RefreshHistory.status == 'SUCCESS').order_by(desc(RefreshHistory.ended_at)).first()
        if last_refresh and last_refresh.ended_at:
            # Render servers are in UTC. Convert explicitly to IST (UTC+05:30)
            utc_dt = last_refresh.ended_at.replace(tzinfo=timezone.utc)
            ist_dt = utc_dt + timedelta(hours=5, minutes=30)
            last_sync = ist_dt.strftime('%Y-%m-%d %I:%M %p')
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
