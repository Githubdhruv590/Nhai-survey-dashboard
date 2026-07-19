import sys
import logging
from sqlalchemy import func

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger("db_cleanup")

from backend.services.db import get_db
from backend.models.schema import SurveyMaster

def run_cleanup():
    db = next(get_db())
    logger.info("Starting database cleanup...")
    
    # 1. Permanently delete soft-deleted rows
    deleted_rows = db.query(SurveyMaster).filter(SurveyMaster.survey_status == 'Deleted').all()
    if deleted_rows:
        logger.info(f"Found {len(deleted_rows)} soft-deleted rows. Hard deleting...")
        for row in deleted_rows:
            db.delete(row)
        db.commit()
        logger.info(f"Successfully deleted {len(deleted_rows)} soft-deleted rows.")
    else:
        logger.info("No soft-deleted rows found.")
        
    # 2. Find duplicate active rows (same upc and date) and delete the oldest ones
    dupes = db.query(
        SurveyMaster.upc_code, 
        SurveyMaster.scheduled_survey_date, 
        func.count(SurveyMaster.id)
    ).filter(
        SurveyMaster.survey_status != 'Deleted'
    ).group_by(
        SurveyMaster.upc_code, 
        SurveyMaster.scheduled_survey_date
    ).having(func.count(SurveyMaster.id) > 1).all()
    
    if dupes:
        logger.info(f"Found {len(dupes)} groups with duplicate business keys. Purging older duplicates...")
        total_orphaned_deleted = 0
        for upc, date, count in dupes:
            records = db.query(SurveyMaster).filter(
                SurveyMaster.upc_code == upc,
                SurveyMaster.scheduled_survey_date == date,
                SurveyMaster.survey_status != 'Deleted'
            ).order_by(SurveyMaster.id.desc()).all()
            
            # Keep the first one (highest ID, i.e., most recent), delete the rest
            records_to_delete = records[1:]
            for row in records_to_delete:
                db.delete(row)
                total_orphaned_deleted += 1
                
        db.commit()
        logger.info(f"Successfully deleted {total_orphaned_deleted} orphaned active duplicate rows.")
    else:
        logger.info("No active duplicate business keys found.")
        
    total_physical = db.query(SurveyMaster).count()
    active_recs = db.query(SurveyMaster).filter(SurveyMaster.survey_status != 'Deleted').count()
    logger.info(f"Cleanup complete. Total Physical Rows: {total_physical} | Active Rows: {active_recs}")

if __name__ == "__main__":
    run_cleanup()
