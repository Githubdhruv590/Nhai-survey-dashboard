import pandas as pd
from backend.services import google_sheet_reader

def peek():
    sheets = google_sheet_reader.get_all_data(force_refresh=False)
    if 'RO Jammu' in sheets:
        df = sheets['RO Jammu']
        print("RO Jammu total rows:", len(df))
        print(df[['Project Name', 'UPC Code']])

if __name__ == "__main__":
    peek()
