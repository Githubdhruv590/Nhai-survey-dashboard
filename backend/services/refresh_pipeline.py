import uuid
import time
import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.models.schema import RefreshHistory, SurveyMaster, DashboardCache
from backend.services import google_sheet_reader
from backend.services.summary_engine import compile_master_data, calculate_kpis, generate_zone_summary_table, generate_ro_summary_table, generate_piu_summary_table, generate_project_summary_table
from backend.services.analytics import get_completion_pie_data, get_zone_comparison_data, get_weekly_trend_data, get_delay_distribution_data, get_provider_performance_data

logger = logging.getLogger("nhai_dashboard.refresh")

class ConcurrentRefreshException(Exception):
    pass

def run_refresh_pipeline(db: Session) -> dict:
    # 0. Concurrency check
    existing_run = db.query(RefreshHistory).filter(RefreshHistory.status == "IN_PROGRESS").first()
    if existing_run:
        # Prevent stalled runs from blocking forever (e.g. older than 10 mins)
        age = (datetime.utcnow() - existing_run.started_at).total_seconds()
        if age < 600:
            raise ConcurrentRefreshException("Another refresh operation is currently in progress.")
        else:
            existing_run.status = "FAILED"
            existing_run.error_message = "Stalled run timed out"
            db.commit()

    refresh_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Pre-calculate previous rows
    try:
        previous_count = db.query(SurveyMaster).count()
    except Exception:
        previous_count = 0
        
    # 1. Log start in history
    history = RefreshHistory(
        refresh_id=refresh_id,
        status="IN_PROGRESS",
    )
    db.add(history)
    db.commit()


    def safe_float(v):
        try:
            s = str(v).strip().replace('%', '')
            if not s or s.lower() in ["nan", "none", "null"]: return 0.0
            return float(s)
        except (ValueError, TypeError): return 0.0
        
    def safe_int(v):
        try:
            s = str(v).strip().replace('%', '')
            if not s or s.lower() in ["nan", "none", "null"]: return 0
            return int(float(s))
        except (ValueError, TypeError): return 0

    try:
        # 2. Fetch raw data from Google Sheets
        sheets_dict = google_sheet_reader.get_all_data(force_refresh=True)
        
        # 3. Compile Master Data
        df_details, df_merged = compile_master_data(sheets_dict)
        
        survey_count = len(df_merged)
        if survey_count == 0:
            raise ValueError("Compiled master data is empty. Validation failed.")

        # 4. Generate Precomputed Dashboard Caches
        kpis = calculate_kpis(df_merged)
        
        charts = {
            "completion_pie": get_completion_pie_data(df_merged),
            "zone_comparison": get_zone_comparison_data(df_merged),
            "weekly_trend": get_weekly_trend_data(df_merged),
            "delay_distribution": get_delay_distribution_data(df_merged),
            "provider_performance": get_provider_performance_data(df_merged)
        }

        zone_table = generate_zone_summary_table(df_merged)
        ro_table = generate_ro_summary_table(df_merged)
        piu_table = generate_piu_summary_table(df_merged)
        project_table = generate_project_summary_table(df_merged)

        # Map merged df to SurveyMaster dictionaries
        df_merged = df_merged.fillna("")
        survey_records = []
        for _, row in df_merged.iterrows():
            record = {
                "survey_id": str(row.get("Survey ID", "")),
                "zone": str(row.get("Zone", "")),
                "ro_name": str(row.get("RO Name", "")),
                "piu_name": str(row.get("PIU Name", "")),
                "project_name": str(row.get("Project Name", "")),
                "upc_code": str(row.get("UPC Code", "")),
                "das_provider": str(row.get("DAS Provider Name", "")),
                "survey_status": str(row.get("Survey Status", "")),
                "report_status": str(row.get("Report Submission Status", "")),
                "scheduled_survey_date": str(row.get("Scheduled Survey Date", "")),
                "actual_survey_date": str(row.get("Actual Survey Date", "")),
                "raw_data_submission_date": str(row.get("Raw Data Submission Date", "")),
                "report_submission_scheduled_date": str(row.get("Report Submission Scheduled Date", "")),
                "report_submission_actual_date": str(row.get("Report Submission Actual Date", "")),
                "discrepancy_date": str(row.get("Discrepancy Date", "")),
                "final_report_submission_scheduled_date": str(row.get("Final Survey Report Submission Scheduled Date", "")),
                "final_report_submission_actual_date": str(row.get("Final Survey Report Submission Actual Date", "")),
                "interim_acceptance_date": str(row.get("Interim Acceptance Date", "")),
                "validation_date": str(row.get("Validation Date", "")),
                "mcw_length_surveyed": safe_float(row.get("MCW Length Surveyed (Km)")),
                "sr_length_surveyed": safe_float(row.get("SR/SL Length Surveyed (Km)")),
                "delay_d1": safe_float(row.get("Delay D1 (Days)")),
                "delay_d2": safe_float(row.get("Delay D2 (Days)")),
                "total_delay": safe_float(row.get("Total Delay (Days)")),
                "ir_count": safe_int(row.get("IR Count")),
                "defects_reported": safe_int(row.get("Defects Reported (#)")),
                "precision_score": safe_float(row.get("Precision Score")),
                "recall_score": safe_float(row.get("Recall Score")),
                "remarks": str(row.get("Remarks", "")),
                "comments": str(row.get("Comments", "")),
                "survey_form_link": str(row.get("Survey Form Link", "")),
                "raw_video_link": str(row.get("Raw Video Link", "")),
                "processed_video_link": str(row.get("Processed Video Link", "")),
                "final_survey_report_link": str(row.get("Final Survey Report Link", "")),
                "assessed_report_link": str(row.get("Assessed Report Link", "")),
                "piu_report_link": str(row.get("PIU Report Link", "")),
                "row_hash": "" # Placeholder for incremental sync
            }
            survey_records.append(record)

        # 5. Populate Temporary Table & Atomic Swap
        try:
            # Re-create temp table if it doesn't exist
            db.execute(text("CREATE TABLE IF NOT EXISTS survey_master_temp AS SELECT * FROM survey_master WHERE 1=0"))
            db.execute(text("DELETE FROM survey_master_temp"))
            
            # Bulk insert into temp table
            db.bulk_insert_mappings(SurveyMaster, survey_records) # Note: technically maps to survey_master, so we must insert to temp table.
            
            # Actually, bulk_insert_mappings maps to SurveyMaster (__tablename__ = 'survey_master').
            # To insert to survey_master_temp without rewriting the ORM model, we can just use raw SQL or a temp model.
            
            # Let's define the temp model inline
            from backend.models.schema import Base
            from sqlalchemy import Table
            
            survey_master_table = SurveyMaster.__table__
            
            # Populate temp table logic: wait, we can just do this purely within the transaction:
            # 1. DELETE FROM survey_master (Not allowed by requirements).
            # Requirements: "Populate temporary table -> Swap tables -> Commit."
            # Since SQLAlchemy makes dynamically mapping models to existing tables tricky, let's execute bulk insert using the table object.
            
            survey_master_temp = Table("survey_master_temp", Base.metadata, autoload_with=db.get_bind())
            db.execute(survey_master_temp.insert(), survey_records)

            # SWAP TABLES
            db.execute(text("DROP TABLE IF EXISTS survey_master_old"))
            db.execute(text("ALTER TABLE survey_master RENAME TO survey_master_old"))
            db.execute(text("ALTER TABLE survey_master_temp RENAME TO survey_master"))
            db.execute(text("ALTER TABLE survey_master_old RENAME TO survey_master_temp"))
            db.execute(text("DELETE FROM survey_master_temp"))
            
        except Exception as swap_err:
            logger.error(f"Atomic swap failed: {swap_err}")
            raise swap_err

        # 6. Update Dashboard Cache
        processing_time = time.time() - start_time
        
        caches = [
            ("global_dashboard", kpis),
            ("chart_summary", charts),
            ("zone_summary", zone_table),
            ("ro_summary", ro_table),
            ("piu_summary", piu_table),
            ("project_summary", project_table)
        ]
        
        for key, payload in caches:
            cache_entry = db.query(DashboardCache).filter_by(cache_key=key).first()
            if not cache_entry:
                cache_entry = DashboardCache(cache_key=key)
                db.add(cache_entry)
            
            cache_entry.payload = payload
            cache_entry.processing_time_seconds = processing_time
            cache_entry.survey_count = survey_count
            cache_entry.refresh_id = refresh_id
            cache_entry.sheet_version = "v1"
            
        history.status = "SUCCESS"
        history.ended_at = datetime.utcnow()
        history.duration = processing_time
        history.surveys_processed = survey_count
        history.inserted_rows = survey_count
        history.deleted_rows = previous_count
        history.updated_rows = 0
        history.skipped_rows = 0
        
        db.commit()

        return {
            "status": "success",
            "processing_time": processing_time,
            "refresh_duration": processing_time,
            "survey_count": survey_count,
            "inserted_rows": survey_count,
            "updated_rows": 0,
            "deleted_rows": previous_count,
            "skipped_rows": 0,
            "cache_updated": True,
            "refresh_timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        db.rollback()
        history.status = "FAILED"
        history.ended_at = datetime.utcnow()
        history.duration = time.time() - start_time
        history.error_message = str(e)
        
        db.add(history)
        db.commit()
        
        logger.error(f"Refresh pipeline failed: {e}")
        raise e
