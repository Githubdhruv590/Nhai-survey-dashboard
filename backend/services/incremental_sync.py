import hashlib
import json
import traceback
import time
import os
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Set, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from backend.models.schema import SurveyMaster
from backend.utils.refresh_logger import RefreshLogger
from backend.services.business_validation import normalize_date

class DuplicatePrimaryKeyException(Exception):
    pass

class ChangeSet:
    def __init__(self):
        self.inserted_ids: Set[str] = set()
        self.updated_ids: Set[str] = set()
        self.deleted_ids: Set[str] = set()
        self.unchanged_ids: Set[str] = set()

def canonicalize_value(val):
    if val is None:
        return ""
        
    s_val = str(val).strip()
    s_lower = s_val.lower()
    if s_lower in ["nan", "nat", "none", ""]:
        return ""
        
    if isinstance(val, (int, float)):
        try:
            formatted = f"{float(val):.6f}".rstrip('0').rstrip('.')
            if formatted == "":
                return "0"
            return formatted
        except:
            return s_val
            
    return s_val

def compute_row_hash(record: dict) -> str:
    # Exclude database-generated fields and metadata
    exclude = {"id", "created_at", "updated_at", "row_hash"}
    
    hash_dict = {}
    for k, v in record.items():
        if k in exclude:
            continue
        hash_dict[k] = canonicalize_value(v)
        
    # Create stable json string for hashing
    hash_str = json.dumps(hash_dict, sort_keys=True)
    return hashlib.sha256(hash_str.encode('utf-8')).hexdigest()

def sync_to_database(db: Session, incoming_records: List[Dict[str, Any]], all_business_keys: List[tuple], refresh_logger: RefreshLogger) -> Tuple[ChangeSet, Dict[str, float]]:
    hash_start = time.time()
    
    # Fetch current DB state mapping (upc, date) -> (id, row_hash)
    db_records = db.query(SurveyMaster.id, SurveyMaster.upc_code, SurveyMaster.scheduled_survey_date, SurveyMaster.row_hash).all()
    db_state = {}
    for r in db_records:
        r_upc = str(r.upc_code).strip() if r.upc_code else ""
        r_date = normalize_date(r.scheduled_survey_date)
        db_state[(r_upc, r_date)] = {"id": r.id, "row_hash": r.row_hash}
    
    changes = ChangeSet()
    to_insert = []
    to_update = []
    skipped_invalid = 0
    
    incoming_ids = set(all_business_keys)
    for record in incoming_records:
        r_upc = str(record.get("upc_code", "")).strip()
        r_date = normalize_date(record.get("scheduled_survey_date", ""))
        bkey = (r_upc, r_date)
        
        r_hash = compute_row_hash(record)
        record["row_hash"] = r_hash
        
        if bkey not in db_state:
            changes.inserted_ids.add(str(bkey))
            to_insert.append(record)
        elif db_state[bkey]["row_hash"] != r_hash:
            changes.updated_ids.add(str(bkey))
            record["id"] = db_state[bkey]["id"]
            to_update.append(record)
        else:
            changes.unchanged_ids.add(str(bkey))
            
    # Soft delete missing surveys (exist in DB but not in incoming)
    deleted_db_ids = []
    for bkey, state in db_state.items():
        if bkey not in incoming_ids:
            changes.deleted_ids.add(str(bkey))
            deleted_db_ids.append(state["id"])
            
    hash_time = time.time() - hash_start
    
    db_sync_start = time.time()
    
    # Execute inserts
    if to_insert:
        db.bulk_insert_mappings(SurveyMaster, to_insert)
        
    # Execute batch upserts (solves N+1 UPDATE problem natively in Postgres)
    if to_update:
        # Chunk the updates in case there are thousands of rows to prevent SQL length limits
        chunk_size = 1000
        for i in range(0, len(to_update), chunk_size):
            chunk = to_update[i:i+chunk_size]
            stmt = pg_insert(SurveyMaster).values(chunk)
            update_dict = {c.name: c for c in stmt.excluded if c.name != "id"}
            stmt = stmt.on_conflict_do_update(
                index_elements=[SurveyMaster.id],
                set_=update_dict
            )
            refresh_logger.log_upsert_start(
                rows_attempting=len(chunk),
                table_name=SurveyMaster.__tablename__,
                conflict_column="id",
                insert_cols=len(chunk[0]) if chunk else 0,
                pk="id",
                stmt_type="INSERT ON CONFLICT DO UPDATE"
            )
            
            # --- DUPLICATE ANALYSIS BLOCK ---
            df = pd.DataFrame(chunk)
            duplicate_mask_id = df.duplicated(subset=["id"], keep=False)
            
            if duplicate_mask_id.any():
                duplicate_rows = df[duplicate_mask_id].copy()
                
                msg = f"""========================================
DUPLICATE ID ANALYSIS
========================================
Total rows: {len(df)}
Unique IDs: {df['id'].nunique()}
Duplicate IDs: {duplicate_rows['id'].nunique()}
Duplicate Records: {len(duplicate_rows)}"""
                
                # Setup directories
                log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
                duplicates_dir = os.path.join(log_dir, "duplicates")
                os.makedirs(duplicates_dir, exist_ok=True)
                
                ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                
                # 3. Save duplicates
                csv_path = os.path.join(duplicates_dir, f"duplicate_ids_{ts}.csv")
                duplicate_rows.to_csv(csv_path, index=False, encoding="utf-8")
                
                # 4. Save duplicate summary
                summary_path = os.path.join(duplicates_dir, f"duplicate_summary_{ts}.txt")
                with open(summary_path, "w", encoding="utf-8") as f:
                    # Group by ID
                    for dup_id, group in duplicate_rows.groupby("id"):
                        f.write(f"Duplicate ID: {dup_id}\n")
                        f.write(f"Occurrence Count: {len(group)}\n\n")
                        f.write(f"Survey IDs: {group.get('survey_id', []).tolist()}\n\n")
                        f.write(f"Project Names: {group.get('project_name', []).tolist()}\n\n")
                        f.write(f"Zone: {group.get('zone', []).tolist()}\n\n")
                        f.write(f"RO: {group.get('ro_name', []).tolist()}\n\n")
                        f.write(f"PIU: {group.get('piu_name', []).tolist()}\n\n")
                        f.write(f"Spreadsheet Row Index: {group.index.tolist()}\n")
                        f.write("-" * 50 + "\n")
                        
                # 5. Log duplicate frequency
                freq = duplicate_rows["id"].value_counts().reset_index()
                freq.columns = ["ID", "Count"]
                freq = freq.sort_values(by="Count", ascending=False)
                msg += "\n\nID\n----------------------------------\n"
                for _, row in freq.iterrows():
                    msg += f"{row['ID']}      {row['Count']}\n"
                    
                # 6. Detect duplicate survey_id
                duplicate_mask_sid = df.duplicated(subset=["survey_id"], keep=False)
                if duplicate_mask_sid.any():
                    sid_path = os.path.join(duplicates_dir, f"duplicate_survey_ids_{ts}.csv")
                    df[duplicate_mask_sid].to_csv(sid_path, index=False, encoding="utf-8")
                    msg += f"\n\n[!] Duplicate survey_ids detected: {duplicate_mask_sid.sum()} rows exported to {sid_path}"
                    
                # 7. Detect completely identical rows
                identical_mask = df.duplicated(keep=False)
                if identical_mask.any():
                    msg += f"\n\n[!] Completely identical rows detected: {identical_mask.sum()}"
                    
                refresh_logger.info(msg)
                
                # 8. Validate primary key (Print before fail)
                pk_val_msg = f"""
Rows: {len(df)}
Unique IDs: {df['id'].nunique()}
Unique Survey IDs: {df['survey_id'].nunique()}
Duplicate IDs: {duplicate_mask_id.sum()}
Duplicate Survey IDs: {duplicate_mask_sid.sum() if duplicate_mask_sid.any() else 0}
Null IDs: {df['id'].isnull().sum()}
Null Survey IDs: {df['survey_id'].isnull().sum()}
"""
                refresh_logger.info(pk_val_msg)
                
                # 9. Fail fast
                raise DuplicatePrimaryKeyException("Duplicate IDs detected before UPSERT. See backend/logs/duplicates for full diagnostics.")
            # --- END DUPLICATE ANALYSIS BLOCK ---

            try:
                t0_upsert = time.time()
                db.execute(stmt)
                refresh_logger.log_upsert_success(len(chunk), time.time() - t0_upsert)
            except Exception as e:
                trace_str = traceback.format_exc()
                refresh_logger.log_upsert_failed(len(chunk), e, trace_str)
                raise
        
    # Execute soft deletes (mark survey_status as 'Deleted')
    if changes.deleted_ids:
        # We need to chunk if the list is huge, but for ~1000 items ANY(:ids) works perfectly in postgres
        db.execute(
            text("UPDATE survey_master SET survey_status = 'Deleted' WHERE id = ANY(:ids)"),
            {"ids": deleted_db_ids}
        )
        
    db_sync_time = time.time() - db_sync_start
    
    metrics = {
        "inserted": len(changes.inserted_ids),
        "updated": len(changes.updated_ids),
        "deleted": len(changes.deleted_ids),
        "unchanged": len(changes.unchanged_ids),
        "skipped_invalid": skipped_invalid,
        "hash_time": hash_time,
        "db_sync_time": db_sync_time
    }
    
    return changes, metrics
