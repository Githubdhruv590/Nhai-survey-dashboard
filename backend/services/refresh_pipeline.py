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
    print("\n" + "="*26 + "\nSTEP 4\n" + "="*26)
    print("Verify run_refresh_pipeline() is executed: YES")
    
    start_time = time.time()
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
        
        print("\n" + "="*26 + "\nSTEP 1\n" + "="*26)
        print("Rows returned from Google Sheets.\n")
        total_raw = 0
        for name, df in sheets_dict.items():
            print(f"{name} = {len(df)}")
            total_raw += len(df)
        print(f"\nTOTAL RAW ROWS = {total_raw}\n")
        
        # 3. Compile Master Data
        df_details, df_merged = compile_master_data(sheets_dict)
        
        print("\n" + "="*26 + "\nSTEP 2\n" + "="*26)
        print("Rows after compile_master_data()")
        print(f"df_merged.shape: {df_merged.shape}")
        
        survey_ids = df_merged["Survey ID"].astype(str).str.strip()
        unique_ids = survey_ids.nunique()
        duplicate_ids = len(survey_ids) - unique_ids
        blank_ids = survey_ids.isin(["", "nan", "None"]).sum()
        
        zones = df_merged["Zone"].astype(str).str.strip()
        blank_zones = zones.isin(["", "nan", "None"]).sum()
        
        print(f"Unique Survey IDs: {unique_ids}")
        print(f"Duplicate Survey IDs: {duplicate_ids}")
        print(f"Rows with blank Survey ID: {blank_ids}")
        print(f"Rows with blank Zone: {blank_zones}\n")
        
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
        
        print("\n" + "="*26 + "\nSTEP 5\n" + "="*26)
        print("Immediately after dashboard_cache generation")
        print(f"cache total_surveys: {kpis.get('total_surveys', 0)}")
        print(f"cache completed: {kpis.get('completed', 0)}")
        print(f"cache pending: {kpis.get('pending', 0)}")
        print(f"zone_summary count: {len(zone_table)}\n")

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

        # 5. Populate Main Table (Simple Transaction)
        try:
            print("\n" + "="*26 + "\nSTEP 3\n" + "="*26)
            print("Immediately before inserting into survey_master print")
            print(f"len(survey_records): {len(survey_records)}\n")
            
            db.execute(text("DELETE FROM survey_master"))
            db.flush()
            
            db.bulk_insert_mappings(SurveyMaster, survey_records)
            db.flush()
            
            print("\n" + "="*26 + "\nSTEP 4\n" + "="*26)
            print("Immediately after SQLAlchemy bulk insert")
            try:
                count_res = db.execute(text("SELECT COUNT(*) FROM survey_master")).scalar()
                print(f"SELECT COUNT(*) FROM survey_master result: {count_res}\n")
            except Exception as e:
                import traceback
                print(f"Exception during count: {e}")
                traceback.print_exc()
            
        except Exception as insert_err:
            logger.error(f"Insertion failed: {insert_err}")
            import traceback
            traceback.print_exc()
            raise insert_err

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
            
        print("\n" + "="*26 + "\nSTEP 5\n" + "="*26)
        print("Verify dashboard_cache is regenerated: YES")
            
        history.status = "SUCCESS"
        
        utc_now = datetime.utcnow()
        history.ended_at = utc_now
        history.duration = processing_time
        history.surveys_processed = survey_count
        history.inserted_rows = survey_count
        history.deleted_rows = previous_count
        history.updated_rows = 0
        history.skipped_rows = 0
        
        db.commit()
        
        from datetime import timezone
        utc_dt = utc_now.replace(tzinfo=timezone.utc)
        local_dt = utc_dt.astimezone()
        
        print("\n" + "="*26 + "\nTIMESTAMP AUDIT\n" + "="*26)
        print(f"Server UTC: {utc_now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Local Time: {local_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Timestamp stored in database: {history.ended_at.strftime('%Y-%m-%d %H:%M:%S')} (Naive UTC)")
        
        print("\n" + "="*26 + "\nSTEP 6\n" + "="*26)
        print("Immediately after COMMIT - Verify survey_master is updated: YES")
        try:
            count_res2 = db.execute(text("SELECT COUNT(*) FROM survey_master")).scalar()
            print(f"SELECT COUNT(*) FROM survey_master result: {count_res2}\n")
        except Exception as e:
            import traceback
            print(f"Exception during count: {e}")
            traceback.print_exc()

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
        import traceback
        print("\n" + "="*26 + "\nEXCEPTION IN REFRESH PIPELINE\n" + "="*26)
        traceback.print_exc()
        db.rollback()
        history.status = "FAILED"
        history.ended_at = datetime.utcnow()
        history.duration = time.time() - start_time
        history.error_message = str(e)
        
        db.add(history)
        db.commit()
        
        logger.error(f"Refresh pipeline failed: {e}")
        raise e
