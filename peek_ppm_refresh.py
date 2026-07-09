import pandas as pd
from backend.services import google_sheet_reader
from backend.services.hierarchy_cache import hierarchy_cache
from backend.services import summary_engine

def refresh_and_peek():
    print("Force refreshing sheets...")
    sheets = google_sheet_reader.get_all_data(force_refresh=True)
    if 'PPM' in sheets:
        print("PPM sheet found! Rows:", len(sheets['PPM']))
        print(sheets['PPM'].head())
    else:
        print("Still no PPM sheet.")

if __name__ == "__main__":
    refresh_and_peek()
