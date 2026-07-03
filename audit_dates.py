import sys
sys.path.insert(0, 'backend')
from backend.services import google_sheet_reader, summary_engine
import pandas as pd

sheets = google_sheet_reader.get_all_data()
_, df = summary_engine.compile_master_data(sheets)

invalid = df[df['Year'] == 0]
for idx, row in invalid.head(2).iterrows():
    print("Row dates:")
    for col, val in row.items():
        if 'date' in col.lower():
            print(f"{col}: {val}")
