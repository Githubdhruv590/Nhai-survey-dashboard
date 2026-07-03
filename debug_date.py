import sys
sys.path.insert(0, 'backend')
from backend.services import google_sheet_reader, summary_engine, week_engine
import pandas as pd

sheets = google_sheet_reader.get_all_data()
_, df = summary_engine.compile_master_data(sheets)

count = 0
for val in df['Scheduled Survey Date']:
    dt = week_engine.parse_date(val)
    if not dt:
        print("UNPARSEABLE DATE:", repr(val))
        count += 1
print(f"Total unparseable: {count}")
