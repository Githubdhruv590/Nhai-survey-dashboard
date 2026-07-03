import sys
sys.path.insert(0,'backend')
from backend.services import google_sheet_reader, summary_engine
sheets = google_sheet_reader.get_all_data()

details = None
for k, v in sheets.items():
    if k.lower().strip() == 'project details':
        details = v.copy()
        break

print(details[details['UPC Code'] == 'N/09048/01001/TN'][['UPC Code', 'RO Name']])
