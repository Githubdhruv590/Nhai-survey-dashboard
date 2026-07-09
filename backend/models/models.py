from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# --- KPIs and Summaries ---
class KPIMetrics(BaseModel):
    # Section 1: Survey Monitoring
    total_surveys_scheduled: int = Field(..., description="Completed + Pending + Scheduled + Cancelled")
    completed: int = Field(..., description="Number of completed surveys")
    pending: int = Field(..., description="Number of pending surveys")
    scheduled: int = Field(..., description="Number of scheduled surveys")
    cancelled: int = Field(..., description="Number of cancelled surveys")
    completion_rate: float = Field(..., description="Completion percentage")
    
    # Section 2: Report Submission
    completed_surveys: int = Field(..., description="Equivalent to completed surveys")
    reports_expected: int = Field(..., description="Equivalent to completed surveys")
    reports_received: int = Field(..., description="Number of reports received")
    reports_on_time: int = Field(..., description="Number of reports on-time")
    reports_delayed: int = Field(..., description="Number of reports delayed")
    
    # Section 3: Defect Section
    defects_total: Optional[int] = Field(None, description="Total defects reported")
    
    # Section 4: Quality Section
    average_precision: Optional[float] = Field(None, description="Average precision")
    average_recall: Optional[float] = Field(None, description="Average recall")
    
    # Section 5: Report Validation Section
    reports_validated: Optional[int] = Field(None, description="Validated reports")
    reports_pending_validation: Optional[int] = Field(None, description="Reports pending validation")
    piu_communication_completed: Optional[int] = Field(None, description="PIU communication completed")
    
    # Section 6: Discrepancy Section
    discrepancies_raised: Optional[int] = Field(None, description="Discrepancies raised")
    discrepancies_resolved: Optional[int] = Field(None, description="Discrepancies resolved")
    discrepancies_pending: Optional[int] = Field(None, description="Discrepancies pending")

    # Legacy Fallbacks
    total_scheduled: int = Field(0, description="Legacy Total Surveys")
    on_time_reports: int = Field(0, description="Legacy On Time Reports")
    delayed_reports: int = Field(0, description="Legacy Delayed Reports")
    pending_reports: int = Field(0, description="Legacy Pending Reports")
    average_delay: float = Field(0.0, description="Legacy Avg Delay")
    maximum_delay: float = Field(0.0, description="Legacy Max Delay")
    total_surveyed_length: float = Field(0.0, description="Legacy Surveyed Length")

# --- Table Rows ---
class ZoneTableRow(BaseModel):
    zone: str
    scheduled: int
    completed: int
    pending: int
    completion_rate: float
    reports_received: int
    on_time: int
    delayed: int
    reports_validated: Optional[int] = None
    pending_validation: Optional[int] = None
    discrepancies: Optional[int] = None
    resolved: Optional[int] = None
    pending_discrepancies: Optional[int] = None
    average_delay: float

class ROTableRow(BaseModel):
    ro_name: str
    zone: str
    scheduled: int
    completed: int
    pending: int
    completion_rate: float
    reports_received: int
    on_time: int
    delayed: int
    reports_validated: Optional[int] = None
    pending_validation: Optional[int] = None
    discrepancies: Optional[int] = None
    resolved: Optional[int] = None
    pending_discrepancies: Optional[int] = None
    average_delay: float

class PIUTableRow(BaseModel):
    piu_name: str
    ro_name: str
    zone: str
    scheduled: int
    completed: int
    pending: int
    completion_rate: float
    reports_received: int
    on_time: int
    delayed: int
    reports_validated: Optional[int] = None
    pending_validation: Optional[int] = None
    discrepancies: Optional[int] = None
    resolved: Optional[int] = None
    pending_discrepancies: Optional[int] = None
    average_delay: float

class ProjectTableRow(BaseModel):
    upc_code: str
    project_name: str
    ro_name: str
    piu_name: str
    scheduled: int
    completed: int
    pending: int
    completion_rate: float
    reports_received: int
    on_time: int
    delayed: int
    reports_validated: Optional[int] = None
    pending_validation: Optional[int] = None
    discrepancies: Optional[int] = None
    resolved: Optional[int] = None
    pending_discrepancies: Optional[int] = None
    average_delay: float
    precision: Optional[float] = None
    recall: Optional[float] = None

# --- Charts ---
class PieChartItem(BaseModel):
    name: str
    value: int
    color: str

class ZoneBarChartItem(BaseModel):
    zone: str
    scheduled: int
    completed: int

class WeeklyTrendItem(BaseModel):
    monday: str
    week_label: str
    scheduled: int
    completed: int
    completion_rate: float

class DelayDistributionItem(BaseModel):
    range: str
    count: int

class ProviderPerformanceItem(BaseModel):
    provider: str
    scheduled: int
    completed: int
    completion_rate: float
    precision: float
    recall: float

class ChartData(BaseModel):
    completion_pie: List[PieChartItem]
    zone_comparison: List[ZoneBarChartItem]
    weekly_trend: List[WeeklyTrendItem]
    delay_distribution: List[DelayDistributionItem]
    provider_performance: List[ProviderPerformanceItem]

# --- Global Dashboard Response ---
class DashboardResponse(BaseModel):
    kpis: KPIMetrics
    zone_table: List[ZoneTableRow]
    charts: ChartData

# --- Filter Options ---
class WeekOption(BaseModel):
    label: str
    start: str
    end: str
    year: int
    month: str

class FilterOptions(BaseModel):
    years: List[int]
    months: List[str]
    weeks: List[WeekOption]
    zones: List[str]
    ros: List[str]
    pius: List[str]
    statuses: List[str]

# --- Detailed Survey Records ---
class SurveyRecordDetail(BaseModel):
    zone: str
    ro_name: str
    piu_name: Optional[str] = "Unknown"
    project_name: str
    upc_code: str
    survey_id: str
    scheduled_survey_date: str
    actual_survey_date: Optional[str] = ""
    survey_status: str
    remarks: Optional[str] = ""
    raw_data_submission_date: Optional[str] = ""
    mcw_length_surveyed: Optional[float] = 0.0
    sr_length_surveyed: Optional[float] = 0.0
    ir_count: Optional[int] = 0
    comments: Optional[str] = ""
    report_submission_scheduled_date: Optional[str] = ""
    report_submission_actual_date: Optional[str] = ""
    delay_d1: Optional[float] = 0.0
    report_submission_status: Optional[str] = ""
    discrepancy_date: Optional[str] = ""
    final_report_submission_scheduled_date: Optional[str] = ""
    final_report_submission_actual_date: Optional[str] = ""
    final_report_submission_status: Optional[str] = ""
    delay_d2: Optional[float] = 0.0
    total_delay: Optional[float] = 0.0
    defects_reported: Optional[int] = 0
    precision_score: Optional[float] = 0.0
    recall_score: Optional[float] = 0.0
    interim_acceptance_date: Optional[str] = ""
    validation_date: Optional[str] = ""
    survey_form_link: Optional[str] = ""
    raw_video_link: Optional[str] = ""
    processed_video_link: Optional[str] = ""
    final_survey_report_link: Optional[str] = ""
    assessed_report_link: Optional[str] = ""
    piu_report_link: Optional[str] = ""

# --- Settings ---
class SettingsResponse(BaseModel):
    google_sheet_url: Optional[str] = None
    google_credentials_file: Optional[str] = ""
    google_api_key: Optional[str] = None
    cache_expiry_seconds: int = 300

class SettingsUpdateRequest(BaseModel):
    google_sheet_url: str
    google_credentials_file: Optional[str] = ""
    google_api_key: Optional[str] = None
    cache_expiry_seconds: int = 300

class ConnectionTestRequest(BaseModel):
    google_sheet_url: str
    google_credentials_file: Optional[str] = ""
    google_api_key: Optional[str] = None

class ConnectionTestResponse(BaseModel):
    status: str
    spreadsheet_name: str
    worksheets_count: int
    sheet_names: List[str]
