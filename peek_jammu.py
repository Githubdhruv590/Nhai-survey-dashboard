import pandas as pd
from backend.services import google_sheet_reader

def peek_raw():
    sheets = google_sheet_reader.get_all_data(force_refresh=False)
    if 'RO Jammu' in sheets:
        df = sheets['RO Jammu']
        print("RO Jammu columns:", df.columns.tolist())
        print("RO Jammu sample:\n", df[['Project Name', 'PIU Name', 'UPC Code']].head() if 'PIU Name' in df.columns else df[['Project Name', 'UPC Code']].head())

if __name__ == "__main__":
    peek_raw()
