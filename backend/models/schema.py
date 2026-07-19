from sqlalchemy import Column, Integer, String, Float, DateTime, Date, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from backend.services.db import Base
from datetime import datetime
import uuid

class SurveyMaster(Base):
    __tablename__ = "survey_master"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    survey_id = Column(String, index=True)
    zone = Column(String, index=True)
    ro_name = Column(String, index=True)
    piu_name = Column(String, index=True)
    project_name = Column(String)
    upc_code = Column(String, index=True)
    das_provider = Column(String, index=True)
    survey_status = Column(String, index=True)
    report_status = Column(String, index=True)
    
    # Dates as strings (for easier compatibility with frontend, or Date if parsed)
    scheduled_survey_date = Column(String, index=True)
    actual_survey_date = Column(String)
    raw_data_submission_date = Column(String)
    report_submission_scheduled_date = Column(String)
    report_submission_actual_date = Column(String)
    discrepancy_date = Column(String)
    final_report_submission_scheduled_date = Column(String)
    final_report_submission_actual_date = Column(String)
    interim_acceptance_date = Column(String)
    validation_date = Column(String)
    
    # Metrics
    mcw_length_surveyed = Column(Float, default=0.0)
    sr_length_surveyed = Column(Float, default=0.0)
    delay_d1 = Column(Float, default=0.0)
    delay_d2 = Column(Float, default=0.0)
    total_delay = Column(Float, default=0.0)
    ir_count = Column(Integer, default=0)
    defects_reported = Column(Integer, default=0)
    precision_score = Column(Float, default=0.0)
    recall_score = Column(Float, default=0.0)
    
    # Strings and links
    remarks = Column(Text)
    comments = Column(Text)
    survey_form_link = Column(String)
    raw_video_link = Column(String)
    processed_video_link = Column(String)
    final_survey_report_link = Column(String)
    assessed_report_link = Column(String)
    piu_report_link = Column(String)
    
    # Checksum for incremental sync
    row_hash = Column(String)

class DashboardCache(Base):
    __tablename__ = "dashboard_cache"

    cache_key = Column(String, primary_key=True, index=True)
    payload = Column(JSON)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processing_time_seconds = Column(Float)
    survey_count = Column(Integer)
    refresh_id = Column(String, index=True)
    sheet_version = Column(String)

class RefreshHistory(Base):
    __tablename__ = "refresh_history"

    refresh_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    duration = Column(Float)
    status = Column(String)  # SUCCESS, FAILED
    surveys_processed = Column(Integer, default=0)
    inserted_rows = Column(Integer, default=0)
    updated_rows = Column(Integer, default=0)
    deleted_rows = Column(Integer, default=0)
    skipped_rows = Column(Integer, default=0)
    failed_rows = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    trigger_source = Column(String, default="Manual")
