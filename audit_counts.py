import sys
import pandas as pd
import numpy as np

sys.path.insert(0, 'backend')
from backend.services import google_sheet_reader, summary_engine
from backend.services.week_engine import parse_date, get_week_boundaries

def run_audit():
    sheets = google_sheet_reader.get_all_data()
    
    # 1. Get total raw surveys by concatenating all RO sheets
    raw_surveys = []
    for sheet_name, df in sheets.items():
        if sheet_name.lower().strip() == "project details":
            continue
        df_copy = df.copy()
        df_copy["RO Worksheet Name"] = sheet_name
        raw_surveys.append(df_copy)
    
    df_raw = pd.concat(raw_surveys, ignore_index=True)
    ro_mapping = {
        "Zone": ["zone"],
        "DAS Provider Name": ["das provider name", "provider name", "dasprovidername", "provider"],
        "Project Name": ["project name", "projectname"],
        "UPC Code": ["upc code", "upccode", "upc"],
        "Survey ID": ["survey id", "surveyid"],
        "Scheduled Survey Date": ["scheduled survey date", "scheduled \nsurvey date", "scheduled_survey_date", "scheduleddate"],
        "Actual Survey Date": ["actual survey date", "actual \nsurvey date", "actual_survey_date", "actualdate"],
        "Survey Status": ["survey status", "surveystatus", "status"],
        "MCW Length Surveyed": ["mcw length surveyed", "mcw_length_surveyed", "mcw length surveyed (km)", "mcw length surveyed (km) "],
        "SR Length Surveyed": ["sr length surveyed", "sr_length_surveyed", "sr length surveyed (km)", "sr/sl length surveyed (km)", "sr/sl length surveyed"],
        "Total Delay": ["total delay", "total_delay", "total delay (days)", "total delay \nd1 + d2 (days)", "delay"],
        "Precision Score": ["precision score", "precision_score", "precision score (%)", "precision", "precision %", "average precision", "ai precision"],
        "Recall Score": ["recall score", "recall_score", "recall score (%)", "recall", "recall %", "average recall", "ai recall"],
        "Report Submission Scheduled Date": ["report submission scheduled date", "report submission scheduled date (dd/mm/yyyy)"],
        "Report Submission Actual Date": ["report submission actual date", "report submission actual date (dd/mm/yyyy)"],
        "Report Submission Status": ["report submission status"],
        "Discrepancy Date": ["discrepancy date", "discrepancy date (dd/mm/yyyy)"],
        "Final Report Submission Scheduled Date": ["final report submission scheduled date", "final report\nsubmission\nscheduled date \n(dd/mm/yyyy)"],
        "Final Report Submission Actual Date": ["final report submission actual date", "final report\nsubmission\nactual date \n(dd/mm/yyyy)"],
        "Final Report Submission Status": ["final report submission status"],
        "Survey Form Link": ["survey form link", "survey form\nlink"],
        "Raw Video Link": ["raw video link", "raw video\nlink"],
        "Processed Video Link": ["processed video link", "processed video\nlink "]
    }
    df_raw = summary_engine.normalize_dataframe_columns(df_raw, ro_mapping)
    
    for i in range(df_raw.shape[1]):
        if df_raw.iloc[:, i].dtype == object:
            df_raw.iloc[:, i] = df_raw.iloc[:, i].astype(str).str.strip()
            
    df_details, df_merged = summary_engine.compile_master_data(sheets)
    
    print("\n==================================================================")
    print("RO VALIDATION")
    print("==================================================================")
    
    # Group raw by RO Worksheet Name (since RO Name might not be in raw, or we use Zone/RO Name mapping)
    # The user says "For every RO". We will group by RO Worksheet Name because that maps 1-1 with the spreadsheet ROs.
    
    ro_raw_counts = df_raw.groupby("RO Worksheet Name").size().to_dict()
    ro_dash_counts = df_merged.groupby("RO Worksheet Name").size().to_dict()
    
    print(f"{'RO Name':<25} | {'Raw':<5} | {'Dash':<5} | {'Diff':<5}")
    print("-" * 50)
    for ro in set(list(ro_raw_counts.keys()) + list(ro_dash_counts.keys())):
        raw_c = ro_raw_counts.get(ro, 0)
        dash_c = ro_dash_counts.get(ro, 0)
        diff = raw_c - dash_c
        print(f"{ro:<25} | {raw_c:<5} | {dash_c:<5} | {diff:<5}")
        if diff != 0:
            print(f"  --> MISMATCH in {ro}")
            # Find which survey IDs are missing
            raw_ids = set(df_raw[df_raw["RO Worksheet Name"] == ro]["Survey ID"].dropna().unique())
            dash_ids = set(df_merged[df_merged["RO Worksheet Name"] == ro]["Survey ID"].dropna().unique())
            print(f"      Missing in dash: {raw_ids - dash_ids}")
            
    print("\n==================================================================")
    print("WEEK VALIDATION")
    print("==================================================================")
    
    # In raw, count weeks manually based on valid dates
    raw_weeks = {}
    for _, row in df_raw.iterrows():
        val = row.get("Scheduled Survey Date", "")
        dt = parse_date(val)
        if dt:
            mon, sun = get_week_boundaries(dt)
            label = f"{mon.strftime('%d %b %Y')} ({mon.strftime('%d %b')} - {sun.strftime('%d %b')})"
            raw_weeks[label] = raw_weeks.get(label, 0) + 1
            
    dash_weeks = df_merged.groupby("Week Label").size().to_dict()
    # Filter out empty Week Label
    dash_weeks = {k: v for k, v in dash_weeks.items() if str(k) not in ["nan", "None", "", "<NA>"]}
    
    print(f"{'Week Label':<35} | {'Raw':<5} | {'Dash':<5} | {'Diff':<5}")
    print("-" * 60)
    for w in set(list(raw_weeks.keys()) + list(dash_weeks.keys())):
        raw_c = raw_weeks.get(w, 0)
        dash_c = dash_weeks.get(w, 0)
        diff = raw_c - dash_c
        print(f"{w:<35} | {raw_c:<5} | {dash_c:<5} | {diff:<5}")
        if diff != 0:
            print(f"  --> MISMATCH in {w}")
            
    print("\n==================================================================")
    print("PIU VALIDATION")
    print("==================================================================")
    # The raw PIU comes from joining df_raw with df_details manually
    if "PIU Name" in df_details.columns and "UPC Code" in df_details.columns:
        df_details["UPC Code"] = df_details["UPC Code"].astype(str).str.replace(".0", "", regex=False).str.strip()
        df_raw["UPC Code"] = df_raw["UPC Code"].astype(str).str.replace(".0", "", regex=False).str.strip()
        df_raw_merged = pd.merge(df_raw, df_details[["UPC Code", "PIU Name"]].drop_duplicates("UPC Code"), on="UPC Code", how="left")
    else:
        df_raw_merged = df_raw.copy()
        
    raw_pius = df_raw_merged.groupby("PIU Name").size().to_dict() if "PIU Name" in df_raw_merged.columns else {}
    dash_pius = df_merged.groupby("PIU Name").size().to_dict()
    
    print(f"{'PIU Name':<40} | {'Raw':<5} | {'Dash':<5} | {'Diff':<5}")
    print("-" * 65)
    for p in set(list(raw_pius.keys()) + list(dash_pius.keys())):
        p_str = str(p)
        raw_c = raw_pius.get(p, 0)
        dash_c = dash_pius.get(p, 0)
        diff = raw_c - dash_c
        print(f"{p_str:<40} | {raw_c:<5} | {dash_c:<5} | {diff:<5}")

if __name__ == "__main__":
    run_audit()
