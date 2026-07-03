import sys
sys.path.insert(0,'backend')
from backend.services import google_sheet_reader, summary_engine
import pandas as pd

sheets = google_sheet_reader.get_all_data()
_, df = summary_engine.compile_master_data(sheets)

def print_stats(stage, dataframe):
    print(f"--- Stage: {stage} ---")
    print(f"Rows: {len(dataframe)}")
    if not dataframe.empty:
        print(f"Unique ROs: {len(dataframe.get('RO Name', pd.Series()).dropna().unique())}")
        print(f"Unique PIUs: {len(dataframe.get('PIU Name', pd.Series()).dropna().unique())}")
        print(f"Unique Projects: {len(dataframe.get('Project Name', pd.Series()).dropna().unique())}")
        print(f"Unique UPCs: {len(dataframe.get('UPC Code', pd.Series()).dropna().unique())}")
    else:
        print("Empty DataFrame")
    print()

print_stats("Master DataFrame", df)

zone_df = df[df['Zone'].str.lower() == 'd']
print_stats("Zone Filter (D)", zone_df)

ro_df = zone_df[zone_df['RO Name'].str.lower() == 'bengaluru']
print_stats("RO Filter (Bengaluru)", ro_df)

print(ro_df[['RO Name', 'PIU Name', 'Project Name', 'UPC Code']].head(20))
