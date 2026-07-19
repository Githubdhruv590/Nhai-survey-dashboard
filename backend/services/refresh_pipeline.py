import uuid
import time
import json
import logging
import traceback
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.models.schema import RefreshHistory, SurveyMaster, DashboardCache
from backend.services import google_sheet_reader
from backend.services.summary_engine import compile_master_data, calculate_kpis, generate_zone_summary_table, generate_ro_summary_table, generate_piu_summary_table, generate_project_summary_table
from backend.services.analytics import get_completion_pie_data, get_zone_comparison_data, get_weekly_trend_data, get_delay_distribution_data, get_provider_performance_data
from backend.services.incremental_sync import sync_to_database
from backend.services.business_validation import validate_business_keys, RefreshThresholdExceededError
from backend.services.db_queries import DB_TO_PANDAS_MAP
from backend.utils.refresh_logger import RefreshLogger

logger = logging.getLogger("nhai_dashboard.refresh")

class ConcurrentRefreshException(Exception):
    pass

USE_SMART_REFRESH = True

def run_refresh_pipeline(db: Session, trigger_source: str = "Manual") -> dict:
    refresh_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Initialize Persistent Logger
    refresh_logger = RefreshLogger(refresh_id, trigger_source, start_time)
    
    # 0. Concurrency check
    existing_run = db.query(RefreshHistory).filter(RefreshHistory.status == "IN_PROGRESS").order_by(RefreshHistory.started_at.desc()).first()
        
    if existing_run:
        age = (datetime.utcnow() - existing_run.started_at).total_seconds()
        # Prevent stalled runs from blocking forever (e.g. older than 10 mins)
        if age < 600:
            raise ConcurrentRefreshException(f"Another refresh operation is currently in progress. Started {age:.1f}s ago.")
        else:
            existing_run.status = "FAILED"
            existing_run.error_message = "Stalled run timed out"
            db.commit()

    # Pre-calculate previous rows
    try:
        previous_count = db.query(SurveyMaster).count()
    except Exception:
        previous_count = 0
        
    # 1. Log start in history
    history = RefreshHistory(
        refresh_id=refresh_id,
        status="IN_PROGRESS",
        trigger_source=trigger_source
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
        db_url = str(db.bind.url)
        refresh_logger.log_start(db_url)
        print(f"[INFO] Refresh Started (Trigger: {trigger_source})")
        
        # 2. Fetch raw data from Google Sheets
        refresh_logger.log_stage("Google Authentication & Sheets Download")
        t0 = time.time()
        sheets_dict = google_sheet_reader.get_all_data(force_refresh=True)
        read_time = time.time() - t0
        
        # 3. Compile Master Data
        refresh_logger.log_stage("Data Cleaning & Compilation")
        t0 = time.time()
        df_details, df_merged = compile_master_data(sheets_dict)
        compile_time = time.time() - t0
        
        survey_count = len(df_merged)
        if survey_count == 0:
            raise ValueError("Compiled master data is empty. Validation failed.")

        # 4. Map merged df to DB format dictionaries
        refresh_logger.log_stage("Date Parsing & Formatting")
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
                "row_hash": ""
            }
            survey_records.append(record)

        # 5. Business Validation & Metadata Recovery
        refresh_logger.log_stage("Business Validation & Quarantine")
        valid_records, all_business_keys, val_metrics = validate_business_keys(survey_records, refresh_logger)
        
        # 6. Database UPSERT
        try:
            if USE_SMART_REFRESH:
                refresh_logger.log_stage("Hash Generation & Incremental Sync Started")
                changes, metrics = sync_to_database(db, valid_records, all_business_keys, refresh_logger)
                db_sync_time = metrics["db_sync_time"]
                hash_time = metrics["hash_time"]
                inserted = metrics["inserted"]
                updated = metrics["updated"]
                deleted = metrics["deleted"]
                unchanged = metrics["unchanged"]
                
                # Attach validation metrics to the sync metrics
                metrics["val_skipped"] = val_metrics["invalid_rows"]
                metrics["val_report_path"] = val_metrics["report_path"]
            else:
                pass
        except RefreshThresholdExceededError as r_err:
            trace_str = traceback.format_exc()
            refresh_logger.log_refresh_failed(r_err, trace_str)
            raise
        except Exception as swap_err:
            trace_str = traceback.format_exc()
            refresh_logger.log_refresh_failed(swap_err, trace_str)
            raise swap_err

        # 7. Generate Precomputed Dashboard Caches (from validated dataset!)
        refresh_logger.log_stage("Cache Build (Pre-computation)")
        t0 = time.time()
        
        # Create canonical DataFrame and map column names for summary_engine
        df_validated = pd.DataFrame(valid_records).rename(columns=DB_TO_PANDAS_MAP)
        
        kpis = calculate_kpis(df_validated)
        
        charts = {
            "completion_pie": get_completion_pie_data(df_validated),
            "zone_comparison": get_zone_comparison_data(df_validated),
            "weekly_trend": get_weekly_trend_data(df_validated),
            "delay_distribution": get_delay_distribution_data(df_validated),
            "provider_performance": get_provider_performance_data(df_validated)
        }

        zone_table = generate_zone_summary_table(df_validated)
        ro_table = generate_ro_summary_table(df_validated)
        piu_table = generate_piu_summary_table(df_validated)
        project_table = generate_project_summary_table(df_validated)
        cache_build_time = time.time() - t0

        # 8. Update Dashboard Cache
        refresh_logger.log_stage("Refresh History Update")
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
            cache_entry.sheet_version = "v5.2"
            
        history.status = "SUCCESS WITH WARNINGS" if metrics.get("val_skipped", 0) > 0 else "SUCCESS"
        history.ended_at = datetime.utcnow()
        history.duration = processing_time
        history.surveys_processed = survey_count
        history.inserted_rows = inserted
        history.deleted_rows = deleted
        history.updated_rows = updated
        history.skipped_rows = unchanged
        
        db.commit()
        
        refresh_logger.log_stage("Refresh Completed")
        
        final_metrics = {
            "Total Refresh Time": f"{processing_time:.4f}s",
            "Rows Read": survey_count,
            "Inserted": inserted,
            "Updated": updated,
            "Unchanged": unchanged,
            "Soft Deleted": deleted,
            "Skipped Invalid": metrics.get("val_skipped", 0),
            "Google Read Time": f"{read_time:.4f}s",
            "Compilation Time": f"{compile_time:.4f}s",
            "Hash Time": f"{hash_time:.4f}s",
            "Database Sync Time": f"{db_sync_time:.4f}s",
            "Cache Build Time": f"{cache_build_time:.4f}s"
        }
        
        refresh_logger.log_refresh_success(final_metrics)
        print("[INFO] Refresh Completed Successfully")

        return {
            "status": "success",
            "processing_time": processing_time,
            "refresh_duration": processing_time,
            "survey_count": survey_count,
            "inserted_rows": inserted,
            "updated_rows": updated,
            "deleted_rows": deleted,
            "skipped_rows": unchanged,
            "cache_updated": True,
            "refresh_timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        trace_str = traceback.format_exc()
        # Ensure refresh_logger is bound before catching
        if 'refresh_logger' in locals():
            refresh_logger.log_refresh_failed(e, trace_str)
        print(f"[ERROR] Refresh Failed: {e}")
        
        db.rollback()
        history.status = "FAILED"
        history.ended_at = datetime.utcnow()
        history.duration = time.time() - start_time
        history.error_message = str(e)
        
        db.add(history)
        db.commit()
        raise e
