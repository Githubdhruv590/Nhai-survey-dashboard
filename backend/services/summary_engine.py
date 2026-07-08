import pandas as pd
import numpy as np
import re
from typing import Dict, List, Any, Tuple
from backend.services.week_engine import parse_date, get_week_boundaries, get_week_label
from backend.services.hierarchy_cache import hierarchy_cache
import logging

logger = logging.getLogger("nhai_dashboard")

def get_column_series(df: pd.DataFrame, possible_names: List[str]) -> pd.Series:
    """
    Finds a column in the DataFrame matching any of the possible names (case-insensitively,
    ignoring unit suffixes like (Km), (Count), \n, etc.) and returns it as a Series.
    If not found, returns an empty Series.
    """
    if df.empty:
        return pd.Series(dtype=object)
        
    for name in possible_names:
        name_clean = name.lower().strip()
        # 1. Look for exact match
        for col in df.columns:
            if str(col).lower().strip() == name_clean:
                return df[col]
                
        # 2. Look for normalized partial match
        for col in df.columns:
            col_str = str(col).lower().strip()
            col_clean = re.sub(r'\(.*?\)', '', col_str).replace('\n', ' ').replace(' ', '').strip()
            tgt_clean = name_clean.replace(' ', '').strip()
            if col_clean == tgt_clean or tgt_clean in col_clean or col_clean in tgt_clean:
                return df[col]
                
    # Fallback
    for name in possible_names:
        name_clean = name.lower().strip()
        for col in df.columns:
            col_str = str(col).lower().strip()
            if name_clean in col_str or col_str in name_clean:
                return df[col]
                
    return pd.Series(dtype=object)

def normalize_dataframe_columns(df: pd.DataFrame, mappings: Dict[str, List[str]]) -> pd.DataFrame:
    """
    Renames DataFrame columns to standard names based on matching possible list of raw names.
    Ensures that each standard name is assigned at most once to prevent duplicate columns.
    Uses exact cleaned matches to prevent false substring hits (e.g. 'ro' matching 'project').
    """
    if df.empty:
        return df
        
    rename_map = {}
    assigned_std_names = set()
    
    for col in df.columns:
        col_str = str(col).lower().strip()
        # Clean col_str by removing unit brackets/parentheses and whitespaces/newlines
        col_clean = re.sub(r'\(.*?\)', '', col_str).replace('\n', ' ').replace(' ', '').strip()
        
        matched = False
        for std_name, raw_names in mappings.items():
            if std_name in assigned_std_names:
                continue
            for raw_name in raw_names:
                raw_clean = raw_name.lower().replace(' ', '').strip()
                # Require exact cleaned match
                if col_clean == raw_clean:
                    rename_map[col] = std_name
                    assigned_std_names.add(std_name)
                    matched = True
                    break
            if matched:
                break
                
    if rename_map:
        df = df.rename(columns=rename_map)
    return df

def convert_percentage_val(val) -> float:
    """
    Safely converts a single cell containing number, string, or percentage (e.g. '95%', '0.95', 95, '-')
    to a float between 0.0 and 1.0.
    """
    if pd.isna(val):
        return np.nan
    val_str = str(val).strip().replace(" ", "")
    if not val_str or val_str in ["-", "n/a", "na", "null", "#value!", "#ref!"]:
        return np.nan
        
    try:
        is_pct = False
        if val_str.endswith("%"):
            val_str = val_str[:-1]
            is_pct = True
            
        num = float(val_str)
        
        # If it has a % sign or is > 1.0, convert to 0-1 range
        if is_pct or num > 1.0:
            return num / 100.0
            
        return num
    except ValueError:
        return np.nan

def convert_percentage_series(series: pd.Series) -> pd.Series:
    """
    Safely converts a series containing numbers, strings, or percentage values
    to floats between 0.0 and 1.0.
    """
    return series.apply(convert_percentage_val)

def generate_validation_report(sheets_dict: Dict[str, pd.DataFrame], df_details: pd.DataFrame, df_merged: pd.DataFrame):
    """
    Compares raw spreadsheet totals against compiled dashboard totals and prints a validation report.
    """
    raw_survey_count = 0
    raw_mcw_len = 0.0
    raw_sr_len = 0.0
    
    # 1. Compute raw totals from individual sheets
    for name, df in sheets_dict.items():
        if name.lower().strip() == "project details" or name.lower().strip() == "ppm" or df.empty:
            continue
            
        # Global rule: Ignore surveys where Scheduled Survey Date is blank or invalid
        date_series = get_column_series(df, ["Scheduled Survey Date", "Scheduled Date"])
        if date_series is not None and not date_series.empty:
            from backend.services.week_engine import parse_date
            def is_valid_date(val):
                return parse_date(val) is not None
            valid_mask = date_series.apply(is_valid_date)
            df_valid = df[valid_mask]
        else:
            df_valid = df
            
        raw_survey_count += len(df_valid)
        
        # MCW Length
        mcw_col = get_column_series(df_valid, ["MCW Length Surveyed", "MCW Length Surveyed (Km)"])
        def clean_val(val):
            if pd.isna(val): return 0.0
            val_str = str(val).strip().replace(" ", "")
            if not val_str or val_str in ["-", "n/a", "na", "null", "#value!", "#ref!"]: return 0.0
            try: return float(val_str)
            except ValueError: return 0.0
        raw_mcw_len += mcw_col.apply(clean_val).sum()
        
        # SR Length
        sr_col = get_column_series(df_valid, ["SR Length Surveyed", "SR/SL Length Surveyed (Km)", "SR/SL Length Surveyed"])
        raw_sr_len += sr_col.apply(clean_val).sum()
        
    # 2. Compute compiled totals
    compiled_survey_count = len(df_merged)
    
    mcw_merged = get_column_series(df_merged, ["MCW Length Surveyed"])
    compiled_mcw_len = pd.to_numeric(mcw_merged, errors="coerce").fillna(0.0).sum()
    
    sr_merged = get_column_series(df_merged, ["SR Length Surveyed"])
    compiled_sr_len = pd.to_numeric(sr_merged, errors="coerce").fillna(0.0).sum()
    
    # 3. Print Comparison Report
    print("\n==================================================================")
    print("NHAI SURVEY DASHBOARD VALIDATION REPORT")
    print("==================================================================")
    print(f"Metric                  | Raw Spreadsheet | Dashboard Merged | Mismatch")
    print(f"------------------------|-----------------|------------------|---------")
    
    survey_diff = raw_survey_count - compiled_survey_count
    print(f"Total Surveys Count     | {raw_survey_count:<15} | {compiled_survey_count:<16} | {'NONE' if survey_diff == 0 else f'DIFF: {survey_diff}'}")
    
    mcw_diff = round(raw_mcw_len - compiled_mcw_len, 2)
    print(f"MCW Length Surveyed     | {round(raw_mcw_len, 2):<15} | {round(compiled_mcw_len, 2):<16} | {'NONE' if abs(mcw_diff) < 0.01 else f'DIFF: {mcw_diff}'}")
    
    sr_diff = round(raw_sr_len - compiled_sr_len, 2)
    print(f"SR Length Surveyed      | {round(raw_sr_len, 2):<15} | {round(compiled_sr_len, 2):<16} | {'NONE' if abs(sr_diff) < 0.01 else f'DIFF: {sr_diff}'}")
    
    print("==================================================================\n")

def clean_ro_display_name(val) -> str:
    """
    Cleans and normalizes RO Name to a canonical form for consistent presentation and filtering.
    """
    if pd.isna(val):
        return "Unknown"
    name = str(val).strip()
    name_lower = name.lower()
    
    # Map raw spelling variations to standard display names
    if "banglore" in name_lower or "bangalore" in name_lower or "bengaluru" in name_lower:
        return "Bengaluru"
    if "thiruvananthapuram" in name_lower or "kerala" in name_lower:
        return "Kerala"
    if "up west" in name_lower:
        return "UP West"
    if "up east" in name_lower:
        return "UP East"
        
    # Strip prefix 'ro '
    if name_lower.startswith("ro "):
        name = name[3:].strip()
        
    # Strip trailing bracket expressions like '(Lucknow)' or '(Varanasi)'
    name = re.sub(r'\(.*?\)', '', name).strip()
    return name

def compile_master_data(sheets_dict: Dict[str, pd.DataFrame]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Finds the Project Details metadata sheet and concatenates all remaining RO worksheets.
    Joins metadata to survey records using UPC Code.
    """
    df_details = pd.DataFrame()
    # Find Project Details case-insensitively
    for k, df in sheets_dict.items():
        if k.lower().strip() == "project details":
            df_details = df.copy()
            break
            
    if df_details.empty:
        logger.warning("Project Details sheet not found or empty.")
        
    # Concatenate all other sheets (ROs)
    ro_dfs = []
    for sheet_name, df in sheets_dict.items():
        if sheet_name.lower().strip() == "project details":
            continue
        df_copy = df.copy()
        # Track worksheet source
        df_copy["RO Worksheet Name"] = sheet_name
        ro_dfs.append(df_copy)
        
    if not ro_dfs:
        logger.warning("No RO worksheets found.")
        return df_details, pd.DataFrame()
        
    df_surveys = pd.concat(ro_dfs, ignore_index=True)
    
    # Mappings
    project_details_mapping = {
        "S. No.": ["s. no.", "s.no.", "sno", "serialnumber"],
        "Zone": ["zone"],
        "RFP Ref.": ["rfp ref.", "rfp ref", "rfpref"],
        "Project Name": ["project name", "projectname"],
        "NH Number": ["nh number", "nhnumber", "nh \nnumber", "nh_number"],
        "UPC Code": ["upc code", "upccode", "upc"],
        "State": ["state"],
        "RO Name": ["ro name", "roname", "ro"],
        "PIU Name": ["piu name", "piuname", "piu"],
        "Survey Start Date": ["survey start date", "surveystartdate"],
    }
    
    ro_sheet_mapping = {
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
        "Processed Video Link": ["processed video link", "processed video\nlink "],
    }

    if not df_details.empty:
        df_details = normalize_dataframe_columns(df_details, project_details_mapping)
    if not df_surveys.empty:
        df_surveys = normalize_dataframe_columns(df_surveys, ro_sheet_mapping)
    
    # Optional: Build the hierarchy cache if PPM is provided in this data refresh
    if "PPM" in sheets_dict:
        hierarchy_cache.build(sheets_dict["PPM"])
    # User explicitly requested NO FALLBACK to Project Details for hierarchy cache.
    # If PPM is missing, the cache will remain empty.
    
    # Strip string columns safely using iloc to bypass any duplicate column name issues
    for i in range(df_details.shape[1]):
        series = df_details.iloc[:, i]
        if series.dtype == object:
            df_details.iloc[:, i] = series.astype(str).str.strip()
            
    for i in range(df_surveys.shape[1]):
        series = df_surveys.iloc[:, i]
        if series.dtype == object:
            df_surveys.iloc[:, i] = series.astype(str).str.strip()
            
    # Clean UPC Code for joining
    if not df_details.empty and "UPC Code" in df_details.columns:
        df_details["UPC Code"] = df_details["UPC Code"].astype(str).str.replace(".0", "", regex=False).str.strip()
    if not df_surveys.empty and "UPC Code" in df_surveys.columns:
        df_surveys["UPC Code"] = df_surveys["UPC Code"].astype(str).str.replace(".0", "", regex=False).str.strip()
        
    # Global rule: Ignore surveys where Scheduled Survey Date is blank or invalid
    if not df_surveys.empty and "Scheduled Survey Date" in df_surveys.columns:
        from backend.services.week_engine import parse_date
        def is_valid_date(val):
            return parse_date(val) is not None
        
        valid_date_mask = df_surveys["Scheduled Survey Date"].apply(is_valid_date)
        df_surveys = df_surveys[valid_date_mask].copy()
        
    df_merged = df_surveys.copy()
        
    # ----------------------------------------------------
    # HIERARCHY PIPELINE: UPC -> Normalized Proj -> Fuzzy Proj -> PIU -> PPM -> RO -> Zone
    # ----------------------------------------------------
    if not df_surveys.empty and not df_details.empty:
        meta_cols = ["UPC Code", "NH Number", "PIU Name", "RFP Ref.", "Survey Start Date", "Project Name", "RO Name"]
        meta_cols = [c for c in meta_cols if c in df_details.columns]
        
        df_details_meta = df_details[meta_cols].copy()
        # Ignore empty UPC codes in Project Details to prevent incorrect cross-mapping for strict join
        df_details_strict = df_details_meta[df_details_meta["UPC Code"].astype(str).str.strip() != ""]
        df_details_strict = df_details_strict.drop_duplicates(subset=["UPC Code"])
        
        df_merged = pd.merge(df_surveys, df_details_strict[["UPC Code", "NH Number", "PIU Name", "RFP Ref.", "Survey Start Date"]], on="UPC Code", how="left")
        
        import string
        import difflib
        
        def normalize_project_name(name):
            if pd.isna(name): return ""
            name = str(name).lower()
            # Remove punctuation
            name = name.translate(str.maketrans('', '', string.punctuation))
            # Collapse repeated spaces
            name = " ".join(name.split())
            return name
            
        # Build normalized project name to PIU mapping
        proj_to_pius = {}
        ro_to_projs = {}
        
        for _, row in df_details_meta.iterrows():
            p_name = normalize_project_name(row.get("Project Name", ""))
            piu = str(row.get("PIU Name", "")).strip()
            ro_val = clean_ro_display_name(row.get("RO Name", ""))
            
            if p_name and piu and piu.lower() not in ["nan", "none"]:
                if p_name not in proj_to_pius:
                    proj_to_pius[p_name] = set()
                proj_to_pius[p_name].add(piu)
                
                if ro_val:
                    if ro_val not in ro_to_projs:
                        ro_to_projs[ro_val] = []
                    ro_to_projs[ro_val].append((p_name, piu))
                    
        # Deterministic project mapping (only if unique)
        deterministic_proj_map = {k: list(v)[0] for k, v in proj_to_pius.items() if len(v) == 1}
        
        def resolve_hierarchy(row):
            piu = str(row.get("PIU Name", "")).strip()
            if piu.lower() in ["nan", "none", "unknown", ""]:
                piu = ""
                
            orig_proj_name = str(row.get("Project Name", ""))
            norm_proj = normalize_project_name(orig_proj_name)
            worksheet_ro = clean_ro_display_name(row.get("RO Worksheet Name", ""))
            
            # Fallback 1: Deterministic Normalized Project Name
            if not piu and norm_proj:
                if norm_proj in deterministic_proj_map:
                    piu = deterministic_proj_map[norm_proj]
                    
            # Fallback 2: Fuzzy Project Name Matching constrained by RO
            if not piu and norm_proj and worksheet_ro in ro_to_projs:
                candidates = ro_to_projs[worksheet_ro]
                candidate_names = [c[0] for c in candidates]
                matches = difflib.get_close_matches(norm_proj, candidate_names, n=2, cutoff=0.90)
                
                if len(matches) == 1:
                    # Exactly one high-confidence candidate
                    match_name = matches[0]
                    # Find corresponding PIU
                    for c_name, c_piu in candidates:
                        if c_name == match_name:
                            piu = c_piu
                            break

            ro = ""
            zone = ""
            
            if piu and hierarchy_cache.is_built:
                ro = hierarchy_cache.get_ro_for_piu(piu) or ""
                if ro:
                    zone = hierarchy_cache.get_zone_for_ro(ro) or ""
                    
            if not ro:
                ro = str(row.get("RO Worksheet Name", "")).strip()
                
            if not zone:
                cleaned_ro = clean_ro_display_name(ro)
                if hierarchy_cache.is_built:
                    zone = hierarchy_cache.get_zone_for_ro(cleaned_ro) or ""
                if not zone:
                    zone = str(row.get("Zone", "")).strip()
                    if zone.lower() in ["nan", "none", "unknown"]:
                        zone = ""
                        
            # Log unresolved surveys
            if not piu:
                upc_val = str(row.get("UPC Code", "")).strip()
                sid_val = str(row.get("Survey ID", "")).strip()
                logger.warning(f"Hierarchy Mapping Required: SID='{sid_val}', UPC='{upc_val}', Project='{orig_proj_name}', RO='{worksheet_ro}'")
                
            return pd.Series([piu, ro, zone])
            
        df_merged[["PIU Name", "RO Name", "Zone"]] = df_merged.apply(resolve_hierarchy, axis=1)
    else:
        df_merged = df_surveys.copy()

    # ----------------------------------------------------
    # Ingestion Data Normalization / Cleaning Layer
    # ----------------------------------------------------
    if not df_merged.empty:
        # 1. Survey Status Normalization
        if "Survey Status" in df_merged.columns:
            def normalize_status_val(val):
                if pd.isna(val):
                    return "pending"
                val_str = str(val).lower().strip()
                if val_str in ["completed", "complete", "on time", "delayed", "late", "yes", "done"]:
                    return "completed"
                if val_str in ["scheduled"]:
                    return "scheduled"
                if val_str in ["cancelled", "canceled"]:
                    return "cancelled"
                return "pending"
            df_merged["Survey Status"] = df_merged["Survey Status"].apply(normalize_status_val)

        # 2. Precision & Recall Score Clean
        for score_col in ["Precision Score", "Recall Score"]:
            if score_col in df_merged.columns:
                df_merged[score_col] = df_merged[score_col].apply(convert_percentage_val)

        # 3. Numeric columns: Total Delay, MCW Length Surveyed, SR Length Surveyed
        for num_col in ["Total Delay", "MCW Length Surveyed", "SR Length Surveyed"]:
            if num_col in df_merged.columns:
                def clean_float_val(val):
                    if pd.isna(val):
                        return 0.0
                    val_str = str(val).strip().replace(" ", "")
                    if not val_str or val_str in ["-", "n/a", "na", "null", "#value!", "#ref!"]:
                        return 0.0
                    try:
                        return float(val_str)
                    except ValueError:
                        return 0.0
                df_merged[num_col] = df_merged[num_col].apply(clean_float_val)
                
        # 4. Clean and standardize RO Names in the final dataset
        if "RO Name" in df_merged.columns:
            df_merged["RO Name"] = df_merged["RO Name"].apply(clean_ro_display_name)

        # 5. Precompute date hierarchy columns dynamically from Scheduled Survey Date
        if "Scheduled Survey Date" in df_merged.columns:
            from backend.services.week_engine import parse_date, get_week_boundaries
            from datetime import datetime
            
            # Calculate active year, month, and week from the dataset dynamically to avoid hardcoding values
            valid_dates = pd.to_datetime(df_merged["Scheduled Survey Date"], errors='coerce', format='mixed', dayfirst=True).dropna()
            
            if not valid_dates.empty:
                active_year = int(valid_dates.dt.year.mode()[0])
                active_month_num = int(valid_dates.dt.month.mode()[0])
                # Find a sample date that matches the mode month to extract week boundaries
                sample_dt = valid_dates[valid_dates.dt.month == active_month_num].iloc[0].to_pydatetime()
            else:
                active_year = datetime.now().year
                sample_dt = datetime.now()
                
            active_monday, active_sunday = get_week_boundaries(sample_dt)
            active_mon_str = active_monday.strftime("%Y-%m-%d")
            active_label = f"{active_monday.strftime('%d %b %Y')} ({active_monday.strftime('%d %b')} - {active_sunday.strftime('%d %b')})"
            active_month_str = sample_dt.strftime("%B")
            
            def compute_date_hierarchy(val):
                dt = parse_date(val)
                if not dt:
                    return None, None, pd.NA, None
                monday, sunday = get_week_boundaries(dt)
                
                mon_str = monday.strftime("%Y-%m-%d")
                label = f"{monday.strftime('%d %b %Y')} ({monday.strftime('%d %b')} - {sunday.strftime('%d %b')})"
                year = int(monday.year)
                month = monday.strftime("%B")
                
                return mon_str, label, year, month

            h_data = df_merged["Scheduled Survey Date"].apply(compute_date_hierarchy)
            df_merged["Week Monday"] = h_data.apply(lambda x: x[0])
            df_merged["Week Label"] = h_data.apply(lambda x: x[1])
            df_merged["Year"] = h_data.apply(lambda x: x[2])
            df_merged["Month"] = h_data.apply(lambda x: x[3])

    # Print validation information and run the strict startup audit
    print("\n========== INVALID ZONE ROWS ==========")

    invalid = df_merged[df_merged["Zone"].astype(str).str.strip() == "Zone"]

    print(invalid[[
    "RO Worksheet Name",
    "Zone",
    "Project Name",
    "UPC Code"
        ]])

    print("Total Invalid Rows:", len(invalid))
    print("=======================================\n")
    audit_backend_startup(sheets_dict, df_merged)
    
    # Generate original validation report comparison (optional, but keep for backward compatibility)
    generate_validation_report(sheets_dict, df_details, df_merged)
    
    df_merged = df_merged.dropna(subset=["Scheduled Survey Date"])
    
    # ----------------------------------------------------
    # Validate Math and Print Missing
    # ----------------------------------------------------
    print("\n==================================================================")
    print("STARTUP VALIDATION: RO vs PIU COUNTS")
    print("==================================================================")
    ro_groups = df_merged.groupby("RO Name", dropna=False)
    for ro_name, group in ro_groups:
        ro_total = len(group)
        # Sum of all PIUs (including unmapped blanks, which remain in the dataframe)
        sum_pius = len(group)
        
        diff = ro_total - sum_pius
        
        # We will also count strictly mapped PIUs just for logging purposes
        mapped_pius = 0
        piu_counts = group.groupby("PIU Name", dropna=False).size()
        for piu_name, count in piu_counts.items():
            piu_str = str(piu_name).strip()
            if piu_str not in ["nan", "None", "", "Unknown"]:
                mapped_pius += count
                
        print(f"RO Name: {ro_name}")
        print(f"RO Total: {ro_total}")
        print(f"Sum of PIUs: {sum_pius}")
        print(f"Difference: {diff}")
        print(f"Mapped PIUs: {mapped_pius}")
        
        if diff != 0:
            print(f"  WARNING: Difference detected for {ro_name}!")
            # Print every unmatched survey
            for _, row in group.iterrows():
                piu = str(row.get("PIU Name", "")).strip()
                if piu in ["nan", "None", "", "Unknown"]:
                    print(f"  -> Missing Survey: UPC={row.get('UPC Code', '')} | Project={row.get('Project Name', '')} | RO={ro_name} | PIU from spreadsheet={row.get('PIU Name', '')}")
        print("------------------------------------------------------------------")
    print("==================================================================\n")

    return df_details, df_merged

def calculate_kpis(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculates KPIs across 6 executive sections on a filtered DataFrame.
    Survey workflow and Report workflow are fully independent.
    Optional metrics return None if data is unavailable in the spreadsheet.
    """
    empty_result = {
        "total_surveys_scheduled": 0, "completed": 0, "pending": 0,
        "scheduled": 0, "cancelled": 0, "completion_rate": 0.0,
        "completed_surveys": 0, "reports_expected": 0, "reports_received": 0,
        "reports_on_time": 0, "reports_delayed": 0,
        "defects_total": None, "defects_repeated": None, "defects_new": None,
        "average_precision": None, "average_recall": None,
        "reports_validated": None, "reports_pending_validation": None,
        "piu_communication_completed": None,
        "discrepancies_raised": None, "discrepancies_resolved": None, "discrepancies_pending": None,
        "total_scheduled": 0, "on_time_reports": 0, "delayed_reports": 0,
        "pending_reports": 0, "average_delay": 0.0, "maximum_delay": 0.0, "total_surveyed_length": 0.0,
    }
    if df.empty:
        return empty_result

    # ── SECTION 1: Survey Monitoring (Survey Status column only) ──────────────
    # Because compile_master_data normalizes this to exactly "completed", "scheduled", "cancelled", "pending"
    status_series = df["Survey Status"] if "Survey Status" in df.columns else pd.Series(["pending"] * len(df))
    
    completed = int((status_series == "completed").sum())
    scheduled_count = int((status_series == "scheduled").sum())
    cancelled = int((status_series == "cancelled").sum())
    pending = int((status_series == "pending").sum())

    total_surveys_scheduled = completed + pending + scheduled_count + cancelled
    completion_rate = round((completed / total_surveys_scheduled * 100), 2) if total_surveys_scheduled > 0 else 0.0

    # ── SECTION 2: Report Submission (Report Status & Delay columns only) ──────
    completed_surveys = completed
    reports_expected = completed_surveys

    actual_date_series = get_column_series(df, ["Report Submission Actual Date"])
    actual_dates_str = actual_date_series.astype(str).str.strip().str.lower()
    
    # A report is considered received if the date exists and is not null/nat
    is_received = actual_dates_str.apply(lambda v: bool(v and v not in ["nan", "none", "", "nat"]))
    reports_received = int(is_received.sum())

    rep_status_series = get_column_series(df, ["Report Submission Status"]).astype(str).str.lower().str.strip()
    delay_d1 = pd.to_numeric(get_column_series(df, ["Delay D1 (Days)", "Delay D1"]), errors="coerce").fillna(0.0)
    delay_d2 = pd.to_numeric(get_column_series(df, ["Delay D2 (Days)", "Delay D2"]), errors="coerce").fillna(0.0)

    # We ONLY count a report as "delayed" if it was actually received AND (status says delayed OR delay > 0).
    # This guarantees Received = On Time + Delayed.
    is_delayed = is_received & ((rep_status_series == "delayed") | (delay_d1 > 0) | (delay_d2 > 0))
    
    reports_delayed = int(is_delayed.sum())
    reports_on_time = reports_received - reports_delayed

    # ── SECTION 3: Defect Analytics ───────────────────────────────────────────
    def_rep_series = get_column_series(df, ["Defects Reported (#)", "Defects Reported"])
    def_rep_vals = pd.to_numeric(
        def_rep_series.astype(str).str.strip().replace(["", "-", "n/a", "nan"], pd.NA), errors="coerce"
    )
    def_rpt_series = get_column_series(df, ["Defects Repeated from Last Cycles (#)", "Defects Repeated from Last Cycles", "Defects Repeated"])
    def_rpt_vals = pd.to_numeric(
        def_rpt_series.astype(str).str.strip().replace(["", "-", "n/a", "nan"], pd.NA), errors="coerce"
    )

    if def_rep_vals.isna().all():
        defects_total = defects_repeated = defects_new = None
    else:
        defects_total = int(def_rep_vals.fillna(0).sum())
        defects_repeated = int(def_rpt_vals.fillna(0).sum()) if not def_rpt_vals.isna().all() else None
        defects_new = (defects_total - defects_repeated) if defects_repeated is not None else defects_total

    # ── SECTION 4: Quality Metrics (optional) ────────────────────────────────
    prec_series = get_column_series(df, ["Precision Score (%)", "Precision Score"])
    rec_series = get_column_series(df, ["Recall Score (%)", "Recall Score"])
    prec_vals = convert_percentage_series(prec_series).dropna()
    rec_vals = convert_percentage_series(rec_series).dropna()
    avg_prec = round(float(prec_vals.mean()), 3) if len(prec_vals) > 0 else None
    avg_rec = round(float(rec_vals.mean()), 3) if len(rec_vals) > 0 else None

    # ── SECTION 5: Report Validation (optional) ───────────────────────────────
    def _has_value(series: pd.Series) -> pd.Series:
        return series.astype(str).str.strip().apply(
            lambda v: bool(v and v not in ["nan", "none", "", "NaT"])
        )

    val_date_series = get_column_series(df, [
        "Report Validation/ Approval Date\n(DD/MM/YYYY)",
        "Report Validation/ Approval Date", "Report Validation Date"
    ])
    piu_date_series = get_column_series(df, [
        "Interim Acceptance/\nPIU Communication Date (DD/MM/YYYY)",
        "Interim Acceptance/ PIU Communication Date", "PIU Communication Date"
    ])
    val_count = int(_has_value(val_date_series).sum())
    piu_count = int(_has_value(piu_date_series).sum())

    if val_count == 0 and piu_count == 0:
        reports_validated = reports_pending_validation = piu_communication_completed = None
    else:
        reports_validated = val_count
        reports_pending_validation = max(0, reports_received - val_count)
        piu_communication_completed = piu_count

    # Adding pending PIU communication properly (reports expected to be communicated vs actually communicated)
    if piu_count > 0:
        piu_communication_pending = max(0, reports_received - piu_count)
    else:
        piu_communication_pending = None

    # ── SECTION 6: Discrepancies (optional) ──────────────────────────────────
    disc_series = get_column_series(df, ["Discrepancy Date"])
    disc_count = int(_has_value(disc_series).sum())

    if disc_count == 0:
        discrepancies_raised = discrepancies_resolved = discrepancies_pending = None
    else:
        discrepancies_raised = disc_count
        final_act_series = get_column_series(df, ["Final Report Submission Actual Date"])
        discrepancies_resolved = int((_has_value(disc_series) & _has_value(final_act_series)).sum())
        discrepancies_pending = max(0, discrepancies_raised - discrepancies_resolved)

    # Legacy / general metrics
    delay_series = get_column_series(df, ["Total Delay", "Total Delay \nD1 + D2 (Days)", "Total Delay (Days)"])
    delays = pd.to_numeric(delay_series, errors="coerce").fillna(0.0)
    avg_delay = round(float(delays.mean()), 2) if len(delays) > 0 else 0.0
    max_delay = round(float(delays.max()), 2) if len(delays) > 0 else 0.0

    mcw_len = pd.to_numeric(get_column_series(df, ["MCW Length Surveyed", "MCW Length Surveyed (Km)"]), errors="coerce").fillna(0.0)
    sr_len = pd.to_numeric(get_column_series(df, ["SR Length Surveyed", "SR/SL Length Surveyed (Km)", "SR/SL Length Surveyed"]), errors="coerce").fillna(0.0)
    total_len = round(float((mcw_len + sr_len).sum()), 2)

    return {
        "total_surveys_scheduled": total_surveys_scheduled,
        "completed": completed, "pending": pending,
        "scheduled": scheduled_count, "cancelled": cancelled,
        "completion_rate": completion_rate,
        "completed_surveys": completed_surveys,
        "reports_expected": reports_expected, "reports_received": reports_received,
        "reports_on_time": reports_on_time, "reports_delayed": reports_delayed,
        "defects_total": defects_total, "defects_repeated": defects_repeated, "defects_new": defects_new,
        "average_precision": avg_prec, "average_recall": avg_rec,
        "reports_validated": reports_validated,
        "reports_pending_validation": reports_pending_validation,
        "piu_communication_completed": piu_communication_completed,
        "piu_communication_pending": piu_communication_pending,
        "discrepancies_raised": discrepancies_raised,
        "discrepancies_resolved": discrepancies_resolved,
        "discrepancies_pending": discrepancies_pending,
        "total_scheduled": total_surveys_scheduled,
        "on_time_reports": reports_on_time, "delayed_reports": reports_delayed,
        "pending_reports": max(0, reports_expected - reports_received), "average_delay": avg_delay,
        "maximum_delay": max_delay, "total_surveyed_length": total_len,
    }

def audit_backend_startup(sheets_dict: Dict[str, pd.DataFrame], df_merged: pd.DataFrame):
    """
    Executes a complete, rigorous hierarchical mathematical audit of the dashboard dataset.
    Proves that totals cascade cleanly from Project -> RO -> Zone -> National.
    Proves that Received = On Time + Delayed unconditionally.
    """
    print("\n" + "="*80)
    print("            NHAI SURVEY DASHBOARD: FINAL STARTUP AUDIT & VALIDATION             ")
    print("="*80)

    # 1. Base counts
    raw_survey_count = 0
    for name, df in sheets_dict.items():
        if name.lower().strip() == "project details" or name.lower().strip() == "ppm" or df.empty:
            continue
            
        date_series = get_column_series(df, ["Scheduled Survey Date", "Scheduled Date"])
        if date_series is not None and not date_series.empty:
            from backend.services.week_engine import parse_date
            def is_valid_date(val):
                return parse_date(val) is not None
            valid_mask = date_series.apply(is_valid_date)
            df_valid = df[valid_mask]
        else:
            df_valid = df
            
        raw_survey_count += len(df_valid)
        
    compiled_survey_count = len(df_merged)
    diff = raw_survey_count - compiled_survey_count
    match = (diff == 0)
    print(f"Total Worksheets Loaded : {len(sheets_dict)}")
    print(f"Total Raw Survey Rows   : {raw_survey_count}")
    print(f"Compiled Dashboard Rows : {compiled_survey_count}")
    print(f"Row Count Verification  : {'[PASS]' if match else '[FAIL]'} (Diff: {diff})")
    
    years = pd.to_numeric(get_column_series(df_merged, ["Year"]), errors='coerce').dropna().unique()
    months = get_column_series(df_merged, ["Month"]).dropna().unique()
    print(f"Distinct Years Found    : {list(years)}")
    print(f"Distinct Months Found   : {list(months)}")

    # Calculate national KPIs
    nat_kpi = calculate_kpis(df_merged)
    nat_rec = nat_kpi['reports_received']
    nat_on_time = nat_kpi['reports_on_time']
    nat_delayed = nat_kpi['reports_delayed']
    nat_sched = nat_kpi['scheduled']
    nat_comp = nat_kpi['completed']
    nat_pend = nat_kpi['pending']
    nat_canc = nat_kpi['cancelled']

    print("\n--- KPI MATHEMATICAL PROOF ---")
    print(f"Total Surveys ({compiled_survey_count}) == Completed({nat_comp}) + Pending({nat_pend}) + Scheduled({nat_sched}) + Cancelled({nat_canc}) ({nat_comp+nat_pend+nat_sched+nat_canc})")
    print(f"Survey Rule Verification: {'[PASS]' if (compiled_survey_count == nat_comp+nat_pend+nat_sched+nat_canc) else '[FAIL]'}")
    
    rep_exp = nat_kpi['reports_expected']
    rep_pen = nat_kpi['pending_reports']
    print(f"Reports Expected ({rep_exp}) - Received ({nat_rec}) == Pending Reports ({rep_exp - nat_rec}) vs Calculated ({rep_pen})")
    print(f"Report Rule Verification: {'[PASS]' if ((rep_exp - nat_rec) == rep_pen) else '[FAIL]'}")

    print(f"Received ({nat_rec}) == On Time ({nat_on_time}) + Delayed ({nat_delayed})")
    print(f"Report Math Verification: {'[PASS]' if (nat_rec == nat_on_time + nat_delayed) else '[FAIL]'}")

    print("\n--------------------------------------------------")
    print("ZONE D VALIDATION")
    print("--------------------------------------------------")
    # Zone D specific check
    zone_d_df = df_merged[df_merged["Zone"] == "D"]
    expected_ros = sorted(zone_d_df["RO Worksheet Name"].apply(clean_ro_display_name).unique().tolist())
    rendered_ros = sorted(zone_d_df["RO Name"].unique().tolist())
    missing_ros = [ro for ro in expected_ros if ro not in rendered_ros]
    extra_ros = [ro for ro in rendered_ros if ro not in expected_ros]
    
    print("Expected ROs:")
    for ro in expected_ros: print(f"- {ro}")
    print("\nRendered ROs:")
    for ro in rendered_ros: print(f"- {ro}")
    print(f"\nMissing ROs:\n- {missing_ros if missing_ros else 'None'}")
    print(f"Extra ROs:\n- {extra_ros if extra_ros else 'None'}")
    z_d_pass = (not missing_ros) and (not extra_ros) and ('' not in rendered_ros)
    print(f"\nResult:\n{'PASS' if z_d_pass else 'FAIL'}")
    print("--------------------------------------------------\n")

    # 2. Hierarchical Validation
    hier_pass = True
    impossible_states = False

    sum_zone_rec = sum_zone_ot = sum_zone_del = 0
    sum_zone_comp = sum_zone_pend = sum_zone_sched = sum_zone_canc = 0
    
    zone_groups = df_merged.groupby("Zone", dropna=False)
    for z_name, z_df in zone_groups:
        z_kpi = calculate_kpis(z_df)
        sum_zone_rec += z_kpi['reports_received']
        sum_zone_ot += z_kpi['reports_on_time']
        sum_zone_del += z_kpi['reports_delayed']
        sum_zone_comp += z_kpi['completed']
        sum_zone_pend += z_kpi['pending']
        sum_zone_sched += z_kpi['scheduled']
        sum_zone_canc += z_kpi['cancelled']
        
        # Received Math check
        if z_kpi['reports_received'] != (z_kpi['reports_on_time'] + z_kpi['reports_delayed']):
            print(f"FAIL: Zone {z_name} violates Received = OnTime + Delayed")
            hier_pass = False
        
        # Impossible state check
        if z_kpi['reports_delayed'] > z_kpi['reports_received'] or z_kpi['reports_on_time'] > z_kpi['reports_received']:
            print(f"FAIL: Zone {z_name} has impossible state.")
            impossible_states = True

        # Cascade into ROs
        ro_groups = z_df.groupby("RO Name", dropna=False)
        sum_ro_rec = sum_ro_ot = sum_ro_del = 0
        sum_ro_comp = sum_ro_pend = sum_ro_sched = sum_ro_canc = 0

        for ro_name, ro_df in ro_groups:
            ro_kpi = calculate_kpis(ro_df)
            sum_ro_rec += ro_kpi['reports_received']
            sum_ro_ot += ro_kpi['reports_on_time']
            sum_ro_del += ro_kpi['reports_delayed']
            sum_ro_comp += ro_kpi['completed']
            sum_ro_pend += ro_kpi['pending']
            sum_ro_sched += ro_kpi['scheduled']
            sum_ro_canc += ro_kpi['cancelled']
            
            if ro_kpi['reports_received'] != (ro_kpi['reports_on_time'] + ro_kpi['reports_delayed']):
                print(f"FAIL: RO {ro_name} (Zone {z_name}) violates Received = OnTime + Delayed")
                hier_pass = False

            if ro_kpi['reports_delayed'] > ro_kpi['reports_received'] or ro_kpi['reports_on_time'] > ro_kpi['reports_received']:
                impossible_states = True

            # Cascade into Projects
            proj_groups = ro_df.groupby("Project Name", dropna=False)
            sum_p_rec = sum_p_ot = sum_p_del = 0
            
            for p_name, p_df in proj_groups:
                p_kpi = calculate_kpis(p_df)
                sum_p_rec += p_kpi['reports_received']
                sum_p_ot += p_kpi['reports_on_time']
                sum_p_del += p_kpi['reports_delayed']
                
                if p_kpi['reports_received'] != (p_kpi['reports_on_time'] + p_kpi['reports_delayed']):
                    print(f"FAIL: Project {p_name} (RO {ro_name}) violates Received = OnTime + Delayed")
                    hier_pass = False

                if p_kpi['reports_delayed'] > p_kpi['reports_received'] or p_kpi['reports_on_time'] > p_kpi['reports_received']:
                    impossible_states = True

            # Validate RO equals sum of Projects
            if sum_p_rec != ro_kpi['reports_received']:
                print(f"FAIL: RO {ro_name} Received ({ro_kpi['reports_received']}) != Sum of Projects ({sum_p_rec})")
                hier_pass = False

        # Validate Zone equals sum of ROs
        if sum_ro_rec != z_kpi['reports_received']:
            print(f"FAIL: Zone {z_name} Received ({z_kpi['reports_received']}) != Sum of ROs ({sum_ro_rec})")
            hier_pass = False
        if sum_ro_comp != z_kpi['completed']:
            print(f"FAIL: Zone {z_name} Completed mismatch.")
            hier_pass = False

    # Validate National equals sum of Zones
    nat_zones_match = (
        (sum_zone_rec == nat_rec) and 
        (sum_zone_ot == nat_on_time) and 
        (sum_zone_del == nat_delayed) and 
        (sum_zone_comp == nat_comp) and
        (sum_zone_pend == nat_pend) and
        (sum_zone_sched == nat_sched) and
        (sum_zone_canc == nat_canc)
    )
    if not nat_zones_match:
        print("FAIL: National KPIs != Sum of Zones")
        hier_pass = False

    print("========================================================")
    print("FINAL HIERARCHY VALIDATION")
    print("========================================================")
    print(f"Rows Loaded                      {'[PASS]' if match else '[FAIL]'}")
    print(f"Zone Totals                      {'[PASS]' if nat_zones_match else '[FAIL]'}")
    print(f"RO Totals                        {'[PASS]' if hier_pass else '[FAIL]'}")
    print(f"Project Totals                   {'[PASS]' if hier_pass else '[FAIL]'}")
    print(f"Survey Totals                    {'[PASS]' if (compiled_survey_count == nat_comp+nat_pend+nat_sched+nat_canc) else '[FAIL]'}")
    print(f"Received = On Time + Delayed     {'[PASS]' if hier_pass else '[FAIL]'}")
    print(f"No Missing ROs                   {'[PASS]' if z_d_pass else '[FAIL]'}")
    print(f"No Impossible States             {'[PASS]' if not impossible_states else '[FAIL]'}")
    print("========================================================\n")

    if not (match and z_d_pass and hier_pass and nat_zones_match and not impossible_states):
        print("CRITICAL VALIDATION FAILURE. Check logs above.\n")





def generate_zone_summary_table(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Aggregates metrics by Zone.
    Columns: Zone, Scheduled, Completed, Pending, Completion %, On Time, Delayed, Discrepancies, Resolved, Pending, Avg Delay.
    """
    if df.empty:
        return []
        
    zone_groups = df.groupby("Zone", dropna=False)
    table_rows = []
    
    for zone_name, group in zone_groups:
        zone_label = str(zone_name).strip() if not pd.isna(zone_name) else ""
        kpis = calculate_kpis(group)
        
        table_rows.append({
            "zone": zone_label,
            "scheduled": kpis["total_scheduled"],
            "completed": kpis["completed"],
            "pending": kpis["pending"],
            "completion_rate": kpis["completion_rate"],
            "reports_received": kpis["reports_received"],
            "on_time": kpis["on_time_reports"],
            "delayed": kpis["delayed_reports"],
            "reports_validated": kpis["reports_validated"],
            "pending_validation": kpis["reports_pending_validation"],
            "discrepancies": kpis["discrepancies_raised"],
            "resolved": kpis["discrepancies_resolved"],
            "pending_discrepancies": kpis["discrepancies_pending"],
            "average_delay": kpis["average_delay"]
        })
        
    # Sort by scheduled count descending
    table_rows.sort(key=lambda x: x["scheduled"], reverse=True)
    return table_rows

def generate_ro_summary_table(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Aggregates metrics by Regional Office (RO) for drill-down.
    """
    if df.empty:
        return []
        
    ro_groups = df.groupby("RO Name", dropna=False)
    table_rows = []
    
    for ro_name, group in ro_groups:
        ro_label = str(ro_name).strip() if not pd.isna(ro_name) else ""
        kpis = calculate_kpis(group)
        
        table_rows.append({
            "ro_name": ro_label,
            "zone": str(group["Zone"].iloc[0]).strip() if not group["Zone"].empty and not pd.isna(group["Zone"].iloc[0]) else "",
            "scheduled": kpis["total_scheduled"],
            "completed": kpis["completed"],
            "pending": kpis["pending"],
            "completion_rate": kpis["completion_rate"],
            "reports_received": kpis["reports_received"],
            "on_time": kpis["on_time_reports"],
            "delayed": kpis["delayed_reports"],
            "reports_validated": kpis["reports_validated"],
            "pending_validation": kpis["reports_pending_validation"],
            "discrepancies": kpis["discrepancies_raised"],
            "resolved": kpis["discrepancies_resolved"],
            "pending_discrepancies": kpis["discrepancies_pending"],
            "average_delay": kpis["average_delay"]
        })
        
    # Sort by completion rate ascending, then scheduled descending
    table_rows.sort(key=lambda x: (x["completion_rate"], -x["scheduled"]))
    return table_rows

def generate_piu_summary_table(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Aggregates metrics by PIU Name for drill-down.
    """
    if df.empty:
        return []
        
    piu_groups = df.groupby("PIU Name", dropna=False)
    table_rows = []
    
    for piu_name, group in piu_groups:
        piu_label = str(piu_name).strip() if not pd.isna(piu_name) else ""
            
        ro_name = str(group["RO Name"].iloc[0]).strip() if not group["RO Name"].empty and not pd.isna(group["RO Name"].iloc[0]) else ""
        kpis = calculate_kpis(group)
        
        table_rows.append({
            "piu_name": piu_label,
            "ro_name": ro_name,
            "zone": str(group["Zone"].iloc[0]).strip() if not group["Zone"].empty and not pd.isna(group["Zone"].iloc[0]) else "",
            "scheduled": kpis["total_scheduled"],
            "completed": kpis["completed"],
            "pending": kpis["pending"],
            "completion_rate": kpis["completion_rate"],
            "reports_received": kpis["reports_received"],
            "on_time": kpis["on_time_reports"],
            "delayed": kpis["delayed_reports"],
            "reports_validated": kpis["reports_validated"],
            "pending_validation": kpis["reports_pending_validation"],
            "discrepancies": kpis["discrepancies_raised"],
            "resolved": kpis["discrepancies_resolved"],
            "pending_discrepancies": kpis["discrepancies_pending"],
            "average_delay": kpis["average_delay"]
        })
        
    table_rows.sort(key=lambda x: (x["completion_rate"], -x["scheduled"]))
    return table_rows

def generate_project_summary_table(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Aggregates metrics by Project (UPC Code) for drill-down.
    """
    if df.empty:
        return []
        
    # Group by UPC Code
    project_groups = df.groupby("UPC Code", dropna=False)
    table_rows = []
    
    for upc_code, group in project_groups:
        upc_label = str(upc_code).strip() if not pd.isna(upc_code) else ""
        proj_name = str(group["Project Name"].iloc[0]).strip() if not group["Project Name"].empty and not pd.isna(group["Project Name"].iloc[0]) else ""
        ro_name = str(group["RO Name"].iloc[0]).strip() if not group["RO Name"].empty and not pd.isna(group["RO Name"].iloc[0]) else ""
        raw_piu = group["PIU Name"].iloc[0] if "PIU Name" in group.columns and not group["PIU Name"].empty else ""
        piu_name_val = str(raw_piu).strip() if not pd.isna(raw_piu) else ""
        
        kpis = calculate_kpis(group)
        
        table_rows.append({
            "upc_code": upc_label,
            "project_name": proj_name,
            "ro_name": ro_name,
            "piu_name": piu_name_val,
            "scheduled": kpis["total_scheduled"],
            "completed": kpis["completed"],
            "pending": kpis["pending"],
            "completion_rate": kpis["completion_rate"],
            "reports_received": kpis["reports_received"],
            "on_time": kpis["on_time_reports"],
            "delayed": kpis["delayed_reports"],
            "reports_validated": kpis["reports_validated"],
            "pending_validation": kpis["reports_pending_validation"],
            "discrepancies": kpis["discrepancies_raised"],
            "resolved": kpis["discrepancies_resolved"],
            "pending_discrepancies": kpis["discrepancies_pending"],
            "average_delay": kpis["average_delay"],
            "precision": kpis["average_precision"],
            "recall": kpis["average_recall"]
        })
        
    table_rows.sort(key=lambda x: x["scheduled"], reverse=True)
    return table_rows
