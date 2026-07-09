import sys
sys.path.insert(0, 'backend')
from backend.services import google_sheet_reader, summary_engine
import pandas as pd

sheets = google_sheet_reader.get_all_data()
_, df_merged = summary_engine.compile_master_data(sheets)

print("RO Chandigarh Zones:", df_merged[df_merged["RO Worksheet Name"] == "RO Chandigarh"]["Zone"].unique())
print("RO Hyderabad Zones:", df_merged[df_merged["RO Worksheet Name"] == "RO Hyderabad"]["Zone"].unique())
