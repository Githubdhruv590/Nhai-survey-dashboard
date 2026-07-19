import os
import csv
from datetime import datetime
from collections import defaultdict
import pandas as pd
from backend.services.metadata_recovery import MetadataRecoveryEngine, MetadataRecoveryRule


class RefreshThresholdExceededError(Exception):
    pass

VALIDATION_FAILURE_THRESHOLD = 0.10  # 10%

def normalize_date(date_str):
    if not date_str:
        return ""
    try:
        # We assume the date parsing in refresh_pipeline is already doing its best. 
        # But we must ensure a canonical format YYYY-MM-DD
        dt = pd.to_datetime(date_str, errors='coerce', dayfirst=True)
        if pd.isna(dt):
            return ""
        return dt.strftime('%Y-%m-%d')
    except:
        return ""

def validate_business_keys(survey_records, refresh_logger):
    """
    Validates business keys and quarantines invalid records.
    Returns: (valid_records, all_business_keys, validation_metrics)
    """
    valid_records = []
    invalid_records = []
    all_business_keys = set()
    
    # Pass all surveys through, as Survey ID is not mandatory
    valid_survey_records = survey_records.copy()
            
    # Apply Intelligent Metadata Recovery
    engine = MetadataRecoveryEngine(rules=[
        MetadataRecoveryRule(target_field="zone", source_field="piu_name")
    ])
    valid_survey_records = engine.recover(valid_survey_records)
    
    # Validation counters
    metrics = {
        "total_rows": len(valid_survey_records),
        "valid_rows": 0,
        "invalid_rows": 0,
        "blank_survey_id": 0,
        "blank_upc": 0,
        "blank_scheduled_date": 0,
        "duplicate_business_keys": 0,
        "report_path": ""
    }
    
    if not valid_survey_records:
        return valid_records, all_business_keys, metrics
        
    # Phase 1: Normalize and track business keys
    bkey_counts = defaultdict(int)
    for record in valid_survey_records:
        upc = record.get("upc_code", "").strip()
        date_raw = record.get("scheduled_survey_date", "")
        
        # We need a robust date normalizer here if it isn't already normalized
        norm_upc = upc
        norm_date = normalize_date(date_raw)
        
        record["_norm_upc"] = norm_upc
        record["_norm_date"] = norm_date
        
        # Only count towards duplicates if it has BOTH parts valid
        if norm_upc and norm_date:
            bkey_counts[(norm_upc, norm_date)] += 1
            all_business_keys.add((norm_upc, norm_date))
            
    # Phase 2: Validate each record
    for record in valid_survey_records:
        norm_upc = record["_norm_upc"]
        norm_date = record["_norm_date"]
        sid = record.get("survey_id", "").strip()
        
        reasons = []
        # Blank Survey ID is an informational metric, not an invalidation reason
        if not sid or str(sid).strip().lower() in ["nan", "none"]:
            metrics["blank_survey_id"] += 1
            
        if not norm_upc:
            reasons.append("Blank UPC Code")
            metrics["blank_upc"] += 1
            
        if not norm_date:
            reasons.append("Blank Scheduled Survey Date")
            metrics["blank_scheduled_date"] += 1
            
        if norm_upc and norm_date and bkey_counts[(norm_upc, norm_date)] > 1:
            reasons.append("Duplicate Business Key")
            metrics["duplicate_business_keys"] += 1
            
        if reasons:
            record["_validation_reason"] = " | ".join(reasons)
            invalid_records.append(record)
        else:
            record.pop("_norm_upc", None)
            record.pop("_norm_date", None)
            valid_records.append(record)
            
    metrics["valid_rows"] = len(valid_records)
    metrics["invalid_rows"] = len(invalid_records)
    
    # Generate Report if invalid records exist
    if invalid_records:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "business_validation")
        os.makedirs(log_dir, exist_ok=True)
        report_path = os.path.join(log_dir, f"validation_{ts}.csv")
        metrics["report_path"] = report_path
        
        with open(report_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Row Number (Appx)", "RO", "PIU", "Project Name", "Survey ID", "UPC Code", "Scheduled Survey Date", "Validation Reason"])
            for idx, r in enumerate(invalid_records):
                writer.writerow([
                    idx,
                    r.get("ro_name", ""),
                    r.get("piu_name", ""),
                    r.get("project_name", ""),
                    r.get("survey_id", ""),
                    r.get("upc_code", ""),
                    r.get("scheduled_survey_date", ""),
                    r.get("_validation_reason", "")
                ])
                
        # We also need to keep track of these all_business_keys for soft delete, 
        # but if an invalid record lacks a UPC or date, we can't track it.
        # This is fine, since it wouldn't exist in the DB anyway.
        
        # Check Threshold
        failure_rate = metrics["invalid_rows"] / metrics["total_rows"]
        if failure_rate > VALIDATION_FAILURE_THRESHOLD:
            # We want to throw so that the pipeline completely fails and does not sync
            raise RefreshThresholdExceededError(
                f"Validation failure rate {failure_rate:.1%} exceeds threshold of {VALIDATION_FAILURE_THRESHOLD:.1%}. "
                f"See {report_path} for details."
            )
            
    return valid_records, list(all_business_keys), metrics
