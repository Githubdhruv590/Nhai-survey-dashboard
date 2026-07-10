import re

with open(r'c:\Users\dhruv\OneDrive\Pictures\Down\Desktop\Desktop files\NHAI-Survey-Dashboard\backend\services\google_sheet_reader.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Mock metadata
mock_metadata = '''def fetch_metadata_api():
    return "NHAI Survey Spreadsheet", ["Project Details", "Zone A", "Zone B"]'''

content = re.sub(r'def fetch_metadata_api\(\).*?return spreadsheet_name, sheet_names', mock_metadata, content, flags=re.DOTALL)

# Mock worksheet
mock_worksheet = '''def fetch_worksheet_api(sheet_name: str):
    import pandas as pd
    if sheet_name == "Project Details":
        return pd.DataFrame([["UPC1", "Project 1", "Zone A", "RO 1", "PIU 1"]], columns=["UPC Code", "Project Name", "Zone", "RO Name", "PIU Name"])
    return pd.DataFrame([["UPC1", "Project 1", "Zone A", "RO 1", "PIU 1", "S1", "Scheduled", "Pending", "2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04", "2023-01-05", "2023-01-06", "2023-01-07", "2023-01-08", "2023-01-09", "2023-01-10", 1.0, 1.0, 1.0, 1.0, 1.0, 1, 1, 1.0, 1.0, "remarks", "comments", "link1", "link2", "link3", "link4", "link5", "link6", "hash"]], columns=["UPC Code", "Project Name", "Zone", "RO Name", "PIU Name", "Survey ID", "Survey Status", "Report Submission Status", "Scheduled Survey Date", "Actual Survey Date", "Raw Data Submission Date", "Report Submission Scheduled Date", "Report Submission Actual Date", "Discrepancy Date", "Final Survey Report Submission Scheduled Date", "Final Survey Report Submission Actual Date", "Interim Acceptance Date", "Validation Date", "MCW Length Surveyed", "SR Length Surveyed", "Delay (D1)", "Delay (D2)", "Total Delay", "IR Count", "Total Defects Reported", "Precision Score", "Recall Score", "Remarks", "Comments", "Survey Form Link", "Raw Video Link", "Processed Video Link", "Final Survey Report Link", "Assessed Report Link", "PIU Report Link", "row_hash"])'''

content = re.sub(r'def fetch_worksheet_api\(sheet_name: str\).*?return parse_sheet_values\(values\)', mock_worksheet, content, flags=re.DOTALL)

with open(r'c:\Users\dhruv\OneDrive\Pictures\Down\Desktop\Desktop files\NHAI-Survey-Dashboard\backend\services\google_sheet_reader.py', 'w', encoding='utf-8') as f:
    f.write(content)
