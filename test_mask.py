import sys, os
import pandas as pd
sys.path.append(os.getcwd())
from backend.services import google_sheet_reader

df = google_sheet_reader.get_worksheet_data('RO Vijayawada', force_refresh=True)
print(f"Total rows before filter: {len(df)}")

def get_col(candidates):
    for col in df.columns:
        col_lower = col.lower().replace('\n', '').replace(' ', '')
        if any(c in col_lower for c in candidates):
            return col
    return None

upc_col = get_col(["upccode", "upc"])
proj_col = get_col(["projectname"])
sid_col = get_col(["surveyid"])
sched_col = get_col(["scheduledsurvey", "scheduleddate"])
actual_col = get_col(["actualsurvey", "actualdate"])

print("Cols:", upc_col, proj_col, sid_col, sched_col, actual_col)

if upc_col and proj_col and sid_col:
    def is_blank(col_name):
        return df[col_name].isna() | (df[col_name].astype(str).str.strip() == "") | (df[col_name].astype(str).str.lower() == "nan")
        
    mask = is_blank(upc_col) & is_blank(proj_col) & is_blank(sid_col)
    
    print("Blank UPC:", sum(is_blank(upc_col)))
    print("Blank Proj:", sum(is_blank(proj_col)))
    print("Blank SID:", sum(is_blank(sid_col)))
    
    print("Mask matches:", sum(mask))
