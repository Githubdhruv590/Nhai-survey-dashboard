import os
import sys
import logging
import traceback
import subprocess
from logging.handlers import RotatingFileHandler
from datetime import datetime
import threading

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
FAILURES_DIR = os.path.join(LOG_DIR, "failures")

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(FAILURES_DIR, exist_ok=True)

# Configure singleton logger
logger = logging.getLogger("persistent_refresh_logger")
logger.setLevel(logging.INFO)

# Only add handler if it doesn't already have one to prevent duplicates during reloads
if not logger.handlers:
    log_file = os.path.join(LOG_DIR, "refresh_pipeline.log")
    handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    # Ensure it doesn't propagate up and print to the console
    logger.propagate = False

def get_git_info():
    try:
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
        return branch, commit
    except Exception:
        return "Unknown", "Unknown"

class RefreshLogger:
    def __init__(self, refresh_id: str, trigger_source: str, start_time: float):
        self.refresh_id = refresh_id
        self.trigger_source = trigger_source
        self.start_time = start_time
        self.current_stage = "START REFRESH"
        
    def _elapsed(self) -> str:
        import time
        return f"{time.time() - self.start_time:.2f}s"

    def log_start(self, db_url: str):
        branch, commit = get_git_info()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Mask password in URL safely
        masked_url = db_url
        if "@" in masked_url and ":" in masked_url:
            try:
                protocol_part = masked_url.split("://")[0]
                rest = masked_url.split("://")[1]
                user = rest.split(":")[0]
                host_part = rest.split("@")[1]
                masked_url = f"{protocol_part}://{user}:***@{host_part}"
            except:
                masked_url = "*** MASKED ***"
                
        msg = f"""====================================================
REFRESH START
====================================================
Timestamp          : {now}
Refresh ID         : {self.refresh_id}
Trigger Source     : {self.trigger_source}
Process ID         : {os.getpid()}
Thread ID          : {threading.get_ident()}
Python Version     : {sys.version.split()[0]}
Database URL       : {masked_url}
Git Branch         : {branch}
Git Commit SHA     : {commit}
Version            : V5.2
===================================================="""
        logger.info(msg)
        
    def log_stage(self, stage_name: str):
        self.current_stage = stage_name
        now = datetime.now().strftime("%H:%M:%S")
        logger.info(f"[{now}] STAGE: {stage_name} | Elapsed: {self._elapsed()}")

    def log_upsert_start(self, rows_attempting: int, table_name: str, conflict_column: str, insert_cols: int, pk: str, stmt_type: str):
        msg = f"""========================
UPSERT START
========================
Rows attempting          : {rows_attempting}
Table name               : {table_name}
Conflict column          : {conflict_column}
Number of insert columns : {insert_cols}
Primary key              : {pk}
Unique constraint        : {conflict_column}
Statement type           : {stmt_type}"""
        logger.info(msg)

    def log_upsert_success(self, rows_affected: int, exec_time: float):
        msg = f"""========================
UPSERT SUCCESS
========================
Rows affected    : {rows_affected}
Execution time   : {exec_time:.4f}s
Commit successful: (Deferred to pipeline end)"""
        logger.info(msg)

    def log_upsert_failed(self, rows_attempting: int, e: Exception, trace: str):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        orig = getattr(e, "orig", None)
        
        msg = f"""========================
UPSERT FAILED
========================
Current Stage            : {self.current_stage}
Rows attempted           : {rows_attempting}
Refresh ID               : {self.refresh_id}
Elapsed Time             : {self._elapsed()}
Exception Type           : {type(e).__name__}
Exception Message        : {str(e)}
repr(exception)          : {repr(e)}"""

        if orig:
            msg += f"""
Underlying Exception Type: {type(orig).__name__}
Underlying Exception repr: {repr(orig)}
Underlying Exception str : {str(orig)}"""

        msg += f"""
SQLAlchemy Exception Class: {e.__class__.__module__}.{e.__class__.__name__}
Traceback:
{trace}"""
        logger.error(msg)
        
    def log_refresh_failed(self, e: Exception, trace: str, metrics: dict = None, records: list = None):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        orig = getattr(e, "orig", None)
        
        msg = f"""====================================================
REFRESH FAILED
====================================================
Timestamp        : {now}
Refresh ID       : {self.refresh_id}
Trigger Source   : {self.trigger_source}
Current Stage    : {self.current_stage}
Elapsed Time     : {self._elapsed()}
Exception Type   : {type(e).__name__}
Exception Message: {str(e)}
repr(exception)  : {repr(e)}
Thread ID        : {threading.get_ident()}
PID              : {os.getpid()}
"""
        if orig:
            msg += f"Database Exception: {repr(orig)}\n"
            
        msg += f"\nTraceback:\n{trace}\n===================================================="
        logger.error(msg)
        
        # Write failure snapshot
        file_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        failure_file = os.path.join(FAILURES_DIR, f"failure_{file_time}.log")
        
        snapshot = msg + "\n\n=== SNAPSHOT DATA ===\n"
        if metrics:
            snapshot += f"Inserted: {metrics.get('inserted', 0)}\n"
            snapshot += f"Updated: {metrics.get('updated', 0)}\n"
            snapshot += f"Deleted: {metrics.get('deleted', 0)}\n"
            snapshot += f"Skipped Invalid: {metrics.get('skipped_invalid', 0)}\n\n"
            
        if records and len(records) > 0:
            snapshot += f"Rows attempting UPSERT: {len(records)}\n"
            sids = [r.get("survey_id") for r in records if "survey_id" in r]
            snapshot += f"First 3 survey_ids: {sids[:3]}\n"
            snapshot += f"Last 3 survey_ids: {sids[-3:]}\n\n"
            snapshot += f"First failing record (preview):\n{records[0]}\n"
            
        with open(failure_file, "w", encoding="utf-8") as f:
            f.write(snapshot)

    def log_refresh_success(self, metrics: dict):
        status = "SUCCESS WITH WARNINGS" if metrics.get("Skipped Invalid", 0) > 0 else "SUCCESS"
        report_msg = ""
        if metrics.get("val_report_path"):
            report_msg = f"\nValidation Report:\n{metrics.get('val_report_path')}\n"
            
        msg = f"""====================================================
REFRESH COMPLETED
====================================================
Status          : {status}
Trigger         : {self.trigger_source}
Total Time      : {metrics.get('Total Refresh Time')}

Rows Read       : {metrics.get('Rows Read')}
Valid Rows      : {metrics.get('Rows Read', 0) - metrics.get('Skipped Invalid', 0)}
Inserted        : {metrics.get('Inserted')}
Updated         : {metrics.get('Updated')}
Unchanged       : {metrics.get('Unchanged')}
Soft Deleted    : {metrics.get('Soft Deleted')}
Skipped Invalid : {metrics.get('Skipped Invalid')}{report_msg}
Google Read Time: {metrics.get('Google Read Time')}
Compilation Time: {metrics.get('Compilation Time')}
Hash Time       : {metrics.get('Hash Time')}
DB Sync Time    : {metrics.get('Database Sync Time')}
Cache Build Time: {metrics.get('Cache Build Time')}
===================================================="""
        logger.info(msg)

    def info(self, msg: str):
        logger.info(msg)

