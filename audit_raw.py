import sys
sys.path.insert(0, 'backend')
from backend.services import google_sheet_reader

sheets = google_sheet_reader.get_all_data()

for sheet_name, df in sheets.items():
    if sheet_name == 'Project Details':
        continue
    # Let's see if any row has missing Scheduled Survey Date but is a valid survey
    # A valid survey has an UPC code and Survey ID
    invalid = df[df.iloc[:, 6].isna() | (df.iloc[:, 6] == '') | (df.iloc[:, 6] == ' ')] # guessing column index 6 is scheduled date
    # Just print the head of the sheet
    if not invalid.empty:
        print(f"Sheet: {sheet_name}")
        print(invalid.head(2))
