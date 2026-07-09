import pandas as pd
from backend.services import google_sheet_reader

def peek():
    sheets = google_sheet_reader.get_all_data(force_refresh=False)
    if 'Project Details' in sheets:
        df = sheets['Project Details']
        res = df[df['UPC Code'].isin(["N/02006/01001/JK", "N/02006/02001/JK"])]
        print(res[['UPC Code', 'PIU Name']])

if __name__ == "__main__":
    peek()
