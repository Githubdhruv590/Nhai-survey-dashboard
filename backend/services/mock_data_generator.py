import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_mock_data():
    """
    Generates a full-featured realistic mock dataset matching NHAI's Google Sheets structure.
    Returns:
        dict: Keys are worksheet names, values are DataFrames.
    """
    np.random.seed(42)
    
    # 1. Generate Project Details
    zones = ["North", "South", "East", "West", "Central"]
    ro_list = ["RO Delhi", "RO Bengaluru", "RO Kolkata", "RO Mumbai", "RO Chandigarh", "RO Lucknow"]
    ro_to_zone = {
        "RO Delhi": "North",
        "RO Chandigarh": "North",
        "RO Lucknow": "North",
        "RO Bengaluru": "South",
        "RO Mumbai": "West",
        "RO Kolkata": "East"
    }
    
    states = {
        "RO Delhi": ["Delhi", "Haryana"],
        "RO Chandigarh": ["Punjab", "Himachal Pradesh"],
        "RO Lucknow": ["Uttar Pradesh"],
        "RO Bengaluru": ["Karnataka", "Tamil Nadu"],
        "RO Mumbai": ["Maharashtra", "Gujarat"],
        "RO Kolkata": ["West Bengal", "Odisha"]
    }
    
    pius = {
        "RO Delhi": ["PIU Ghaziabad", "PIU Faridabad", "PIU Gurugram"],
        "RO Chandigarh": ["PIU Ambala", "PIU Jalandhar", "PIU Shimla"],
        "RO Lucknow": ["PIU Lucknow", "PIU Kanpur", "PIU Varanasi"],
        "RO Bengaluru": ["PIU Bengaluru", "PIU Ramanagara", "PIU Chennai"],
        "RO Mumbai": ["PIU Mumbai", "PIU Pune", "PIU Surat"],
        "RO Kolkata": ["PIU Kolkata", "PIU Kharagpur", "PIU Bhubaneswar"]
    }
    
    providers = ["Highway Analytics Inc.", "RoadInspect Labs", "SurvWay Technologies", "GeoInfra Surveys Ltd."]
    
    projects = []
    upc_counter = 10001
    
    # Let's create about 35 projects
    project_names = [
        # North
        ("Delhi-Meerut Expressway P1", "RO Delhi"),
        ("Delhi-Meerut Expressway P2", "RO Delhi"),
        ("Faridabad-Gurugram Highway", "RO Delhi"),
        ("Ambala-Chandigarh Highway", "RO Chandigarh"),
        ("Jalandhar-Pathankot Bypass", "RO Chandigarh"),
        ("Lucknow-Ayodhya Expressway", "RO Lucknow"),
        ("Kanpur-Allahabad Highway Section", "RO Lucknow"),
        # South
        ("Bangalore-Mysore Expressway Sec-A", "RO Bengaluru"),
        ("Bangalore-Mysore Expressway Sec-B", "RO Bengaluru"),
        ("Chennai-Ennore Port Road", "RO Bengaluru"),
        ("Bengaluru Outer Ring Road Upgrade", "RO Bengaluru"),
        # West
        ("Mumbai-Pune Expressway Upgrades", "RO Mumbai"),
        ("Surat-Dahod Section NH-56", "RO Mumbai"),
        ("Nashik-Pune Corridor Phase 1", "RO Mumbai"),
        # East
        ("Kolkata-Haldia Port Highway", "RO Kolkata"),
        ("Kolkata Airport Bypass Ext", "RO Kolkata"),
        ("Bhubaneswar-Cuttack Expressway", "RO Kolkata")
    ]
    
    # Duplicate/expand project names to reach ~45 projects
    extended_projects = []
    for name, ro in project_names:
        extended_projects.append((name, ro))
        extended_projects.append((f"{name} Phase II", ro))
        
    for i, (name, ro) in enumerate(extended_projects):
        zone = ro_to_zone[ro]
        state = np.random.choice(states[ro])
        piu = np.random.choice(pius[ro])
        upc = upc_counter + i
        rfp = f"RFP/NHAI/Tech/2026/{i+100:03d}"
        nh_num = f"NH-{(i * 7 + 2) % 99 + 1}"
        
        projects.append({
            "Zone": zone,
            "RFP Ref.": rfp,
            "Project Name": name,
            "NH Number": nh_num,
            "UPC Code": upc,
            "State": state,
            "RO Name": ro,
            "PIU Name": piu,
            "Survey Start Date": (datetime(2026, 1, 1) + timedelta(days=i*4)).strftime("%Y-%m-%d")
        })
        
    df_projects = pd.DataFrame(projects)
    
    # 2. Generate RO Sheets
    # We will generate survey records for each project
    # Starting from early June 2026 to late August 2026 (relative to current date July 1, 2026)
    ro_sheets = {ro: [] for ro in ro_list}
    
    base_date = datetime(2026, 6, 1)
    survey_id_counter = 1000
    
    # Generate weekly survey events
    for p in projects:
        ro = p["RO Name"]
        upc = p["UPC Code"]
        name = p["Project Name"]
        zone = p["Zone"]
        piu = p["PIU Name"]
        
        # Each project has 4-8 scheduled surveys (roughly weekly or bi-weekly)
        num_surveys = np.random.randint(4, 9)
        provider = np.random.choice(providers)
        
        for s_idx in range(num_surveys):
            survey_id_counter += 1
            survey_id = f"SRV-{survey_id_counter}"
            
            # Scheduled date
            scheduled_date = base_date + timedelta(weeks=s_idx, days=np.random.randint(-2, 3))
            scheduled_str = scheduled_date.strftime("%Y-%m-%d")
            
            # Determine status based on current simulated time (July 1, 2026)
            is_past = scheduled_date < datetime(2026, 7, 1)
            
            actual_str = ""
            raw_sub_str = ""
            status = "Pending"
            remarks = ""
            comments = ""
            mcw_length = ""
            sr_length = ""
            ir_count = ""
            
            report_sched_str = ""
            report_act_str = ""
            report_status = "Pending"
            delay_d1 = ""
            
            discrepancy_str = ""
            
            final_report_sched_str = ""
            final_report_act_str = ""
            final_report_status = "Pending"
            delay_d2 = ""
            total_delay = ""
            
            defects = ""
            repeated_defects = ""
            precision = ""
            recall = ""
            
            interim_date_str = ""
            validation_date_str = ""
            
            if is_past:
                # 85% completion rate for past surveys
                if np.random.rand() < 0.85:
                    status = "Completed"
                    # actual date: on average same as scheduled or with some delay
                    act_delay = np.random.choice([0, 0, 0, 1, 2, -1, 5])
                    actual_date = scheduled_date + timedelta(days=int(act_delay))
                    actual_str = actual_date.strftime("%Y-%m-%d")
                    
                    raw_sub_date = actual_date + timedelta(days=np.random.randint(1, 4))
                    raw_sub_str = raw_sub_date.strftime("%Y-%m-%d")
                    
                    mcw_length = round(np.random.uniform(5.0, 50.0), 2)
                    sr_length = round(mcw_length * np.random.uniform(0.6, 0.95), 2)
                    ir_count = int(np.random.randint(2, 25))
                    
                    # Report Submission Dates
                    report_sched_date = actual_date + timedelta(days=7)
                    report_sched_str = report_sched_date.strftime("%Y-%m-%d")
                    
                    # Report submission actual date
                    # 75% on time, 25% delayed
                    is_delayed = np.random.rand() < 0.25
                    if is_delayed:
                        rep_delay = np.random.randint(1, 15)
                        report_act_date = report_sched_date + timedelta(days=rep_delay)
                        report_status = "Delayed"
                        delay_d1 = int(rep_delay)
                    else:
                        rep_delay = np.random.randint(-3, 1)
                        report_act_date = report_sched_date + timedelta(days=int(rep_delay))
                        report_status = "Submitted"
                        delay_d1 = 0
                        
                    report_act_str = report_act_date.strftime("%Y-%m-%d")
                    
                    # Discrepancy (20% of completed reports get a discrepancy)
                    has_discrepancy = np.random.rand() < 0.20
                    if has_discrepancy:
                        discrepancy_date = report_act_date + timedelta(days=1)
                        discrepancy_str = discrepancy_date.strftime("%Y-%m-%d")
                        
                        # Final report scheduling
                        final_report_sched_date = discrepancy_date + timedelta(days=7)
                        final_report_sched_str = final_report_sched_date.strftime("%Y-%m-%d")
                        
                        # Resolution (80% resolved for past discrepancies)
                        is_resolved = np.random.rand() < 0.80
                        if is_resolved:
                            final_delay = np.random.randint(-2, 8)
                            final_act_date = final_report_sched_date + timedelta(days=int(final_delay))
                            final_report_act_str = final_act_date.strftime("%Y-%m-%d")
                            final_report_status = "Approved"
                            delay_d2 = max(0, int(final_delay))
                            comments = "Discrepancy resolved after re-submission."
                        else:
                            final_report_status = "Pending"
                            delay_d2 = ""
                            comments = "Discrepancy raised: road boundary lines unclear in video."
                    else:
                        # No discrepancy, final report scheduled directly
                        final_report_sched_date = report_act_date + timedelta(days=5)
                        final_report_sched_str = final_report_sched_date.strftime("%Y-%m-%d")
                        
                        final_act_date = final_report_sched_date + timedelta(days=np.random.randint(-1, 3))
                        final_report_act_str = final_act_date.strftime("%Y-%m-%d")
                        final_report_status = "Approved"
                        delay_d2 = 0
                        comments = "Survey parameters within tolerance."
                    
                    # Calculate Total Delay
                    d1_val = delay_d1 if delay_d1 != "" else 0
                    d2_val = delay_d2 if delay_d2 != "" else 0
                    total_delay = d1_val + d2_val
                    
                    defects = int(np.random.randint(5, 60))
                    repeated_defects = int(defects * np.random.uniform(0.05, 0.25))
                    precision = round(np.random.uniform(0.82, 0.99), 3)
                    recall = round(np.random.uniform(0.80, 0.98), 3)
                    
                    interim_date = (final_act_date if final_report_act_str else final_report_sched_date) + timedelta(days=3)
                    interim_date_str = interim_date.strftime("%Y-%m-%d")
                    
                    validation_date = interim_date + timedelta(days=2)
                    validation_date_str = validation_date.strftime("%Y-%m-%d")
                    remarks = "Quality check passed"
                else:
                    status = "Pending"
                    remarks = "Delayed due to bad weather"
                    comments = "Survey postponed by regional team."
            else:
                # Future surveys: status is Pending or Scheduled
                status = "Scheduled"
                remarks = "Planned survey"
                comments = "Ready for execution."

            ro_sheets[ro].append({
                "Zone": zone,
                "DAS Provider Name": provider,
                "Project Name": name,
                "UPC Code": upc,
                "Survey ID": survey_id,
                "Scheduled Survey Date": scheduled_str,
                "Actual Survey Date": actual_str,
                "Survey Status": status,
                "Remarks": remarks,
                "Raw Data Submission Date": raw_sub_str,
                "MCW Length Surveyed": mcw_length,
                "SR Length Surveyed": sr_length,
                "IR Count": ir_count,
                "Comments": comments,
                "Report Submission Scheduled Date": report_sched_str,
                "Report Submission Actual Date": report_act_str,
                "Delay D1": delay_d1,
                "Report Submission Status": report_status,
                "Discrepancy Date": discrepancy_str,
                "Final Report Submission Scheduled Date": final_report_sched_str,
                "Final Report Submission Actual Date": final_report_act_str,
                "Final Report Submission Status": final_report_status,
                "Delay D2": delay_d2,
                "Total Delay": total_delay,
                "Defects Reported": defects,
                "Repeated Defects": repeated_defects,
                "Precision Score": precision,
                "Recall Score": recall,
                "Interim Acceptance Date": interim_date_str,
                "Validation Date": validation_date_str,
                "Survey Form Link": f"https://docs.google.com/forms/nhai-survey-{survey_id}",
                "Raw Video Link": f"https://drive.google.com/nhai-raw-{survey_id}",
                "Processed Video Link": f"https://drive.google.com/nhai-proc-{survey_id}",
                "Final Survey Report Link": f"https://drive.google.com/nhai-rep-{survey_id}",
                "Assessed Report Link": f"https://drive.google.com/nhai-assess-{survey_id}",
                "PIU Report Link": f"https://drive.google.com/nhai-piu-{survey_id}"
            })
            
    # Convert lists of dicts to DataFrames
    sheets_dict = {"Project Details": df_projects}
    for ro, data in ro_sheets.items():
        sheets_dict[ro] = pd.DataFrame(data)
        
    return sheets_dict
