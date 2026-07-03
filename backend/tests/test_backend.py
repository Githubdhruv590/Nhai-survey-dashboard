import pytest
import pandas as pd
from datetime import datetime
from backend.services import week_engine, summary_engine, mock_data_generator

def test_parse_date():
    assert week_engine.parse_date("2026-07-01") == datetime(2026, 7, 1)
    assert week_engine.parse_date("01/07/2026") == datetime(2026, 7, 1)
    assert week_engine.parse_date("invalid-date") is None
    assert week_engine.parse_date(None) is None

def test_week_boundaries():
    # July 1, 2026 is a Wednesday
    dt = datetime(2026, 7, 1)
    monday, sunday = week_engine.get_week_boundaries(dt)
    
    assert monday.strftime("%Y-%m-%d") == "2026-06-29" # Previous Monday
    assert sunday.strftime("%Y-%m-%d") == "2026-07-05"  # Next Sunday

def test_week_label():
    monday = datetime(2026, 6, 29)
    sunday = datetime(2026, 7, 5)
    assert week_engine.get_week_label(monday, sunday) == "29 Jun - 05 Jul"

def test_mock_data_generation():
    sheets = mock_data_generator.generate_mock_data()
    assert "Project Details" in sheets
    assert len(sheets.keys()) > 3 # Multiple RO sheets
    
    df_details = sheets["Project Details"]
    assert "UPC Code" in df_details.columns
    assert "Zone" in df_details.columns

def test_calculate_kpis():
    # Create simple dataframe matching structure
    data = [
        {
            "Survey Status": "Completed",
            "MCW Length Surveyed": 10.0,
            "SR Length Surveyed": 5.0,
            "Total Delay": 2,
            "Precision Score": 0.95,
            "Recall Score": 0.90,
            "Report Submission Scheduled Date": "2026-06-20",
            "Report Submission Actual Date": "2026-06-22",
            "Discrepancy Date": "",
            "Final Report Submission Scheduled Date": "",
            "Final Report Submission Actual Date": ""
        },
        {
            "Survey Status": "Pending",
            "MCW Length Surveyed": 0,
            "SR Length Surveyed": 0,
            "Total Delay": 0,
            "Precision Score": "",
            "Recall Score": "",
            "Report Submission Scheduled Date": "",
            "Report Submission Actual Date": "",
            "Discrepancy Date": "",
            "Final Report Submission Scheduled Date": "",
            "Final Report Submission Actual Date": ""
        }
    ]
    df = pd.DataFrame(data)
    kpis = summary_engine.calculate_kpis(df)
    
    assert kpis["total_scheduled"] == 2
    assert kpis["completed"] == 1
    assert kpis["pending"] == 1
    assert kpis["completion_rate"] == 50.0
    assert kpis["total_surveyed_length"] == 15.0
    assert kpis["average_precision"] == 0.95
    assert kpis["average_recall"] == 0.90
    assert kpis["average_delay"] == 1.0 # (2 + 0) / 2
    assert kpis["maximum_delay"] == 2.0

def test_auth_priority():
    from backend.services import google_sheet_reader
    from backend.config.config import settings
    
    # Save original settings
    orig_creds = settings.GOOGLE_CREDENTIALS_FILE
    orig_key = settings.GOOGLE_API_KEY
    
    try:
        # Case 1: credentials file path is blank/None and key is set -> API Key
        settings.GOOGLE_CREDENTIALS_FILE = ""
        settings.GOOGLE_API_KEY = "dummy-api-key"
        headers, params, method = google_sheet_reader.get_auth_headers_and_params()
        assert method == "API Key"
        assert params == {"key": "dummy-api-key"}
        assert headers == {}
        
        # Case 2: credentials file path is non-existent -> immediately use key
        settings.GOOGLE_CREDENTIALS_FILE = "non_existent_file.json"
        settings.GOOGLE_API_KEY = "another-key"
        headers, params, method = google_sheet_reader.get_auth_headers_and_params()
        assert method == "API Key"
        assert params == {"key": "another-key"}
        
        # Case 3: both are missing -> raise ValueError
        settings.GOOGLE_CREDENTIALS_FILE = ""
        settings.GOOGLE_API_KEY = ""
        with pytest.raises(ValueError, match="Google authentication is not configured"):
            google_sheet_reader.get_auth_headers_and_params()
            
    finally:
        # Restore settings
        settings.GOOGLE_CREDENTIALS_FILE = orig_creds
        settings.GOOGLE_API_KEY = orig_key

def test_audited_kpis():
    # Construct a test DataFrame with mixed and missing workflows
    data = [
        {
            # Row 1: Completed survey status, on-time report, precision/recall missing
            "Survey Status": "Complete",
            "Report Submission Status": "On Time",
            "Delay D1": "",
            "Delay D2": 0,
            "Precision Score": "",
            "Recall Score": "",
            "Discrepancy Date": "",
            "MCW Length Surveyed": 5.0,
            "SR Length Surveyed": 0.0,
            "Total Delay": 0
        },
        {
            # Row 2: Pending survey status, delayed report via Delay D1, recall set
            "Survey Status": "Pending",
            "Report Submission Status": "",
            "Delay D1": 2,
            "Delay D2": "",
            "Precision Score": "",
            "Recall Score": "0.92",
            "Discrepancy Date": "",
            "MCW Length Surveyed": 0.0,
            "SR Length Surveyed": 0.0,
            "Total Delay": 2
        },
        {
            # Row 3: Scheduled survey status, delayed report via status, precision set
            "Survey Status": "Scheduled",
            "Report Submission Status": "Delayed",
            "Delay D1": 0,
            "Delay D2": 0,
            "Precision Score": "0.95",
            "Recall Score": "",
            "Discrepancy Date": "",
            "MCW Length Surveyed": 0.0,
            "SR Length Surveyed": 0.0,
            "Total Delay": 0
        }
    ]
    df = pd.DataFrame(data)
    kpis = summary_engine.calculate_kpis(df)
    
    # 1. Survey status metrics
    assert kpis["completed"] == 1
    assert kpis["pending"] == 1
    assert kpis["scheduled"] == 1
    assert kpis["total_scheduled"] == 3 # Completed + Pending + Scheduled
    
    # 2. Report submission delay metrics
    # Row 1: On-Time
    # Row 2: Delay D1 > 0 -> Delayed
    # Row 3: Report Status == "Delayed" -> Delayed
    assert kpis["delayed_reports"] == 2
    assert kpis["on_time_reports"] == 1
    
    # 3. Optional Quality metrics (precision/recall average when some valid exist)
    assert kpis["average_precision"] == 0.95
    assert kpis["average_recall"] == 0.92
    
    # 4. Discrepancy metric (None if entirely missing)
    assert kpis["discrepancies_raised"] is None
    assert kpis["discrepancies_resolved"] is None
    assert kpis["discrepancies_pending"] is None
    
    # 5. Null metrics return None when completely blank
    df_empty_metrics = pd.DataFrame([
        {
            "Survey Status": "Complete",
            "Report Submission Status": "",
            "Delay D1": "",
            "Delay D2": "",
            "Precision Score": "",
            "Recall Score": "",
            "Discrepancy Date": "",
            "MCW Length Surveyed": 0,
            "SR Length Surveyed": 0,
            "Total Delay": 0
        }
    ])
    kpis_empty = summary_engine.calculate_kpis(df_empty_metrics)
    assert kpis_empty["average_precision"] is None
    assert kpis_empty["average_recall"] is None
    assert kpis_empty["discrepancies_raised"] is None

