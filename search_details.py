import pandas as pd
from backend.services import google_sheet_reader

def search_details():
    sheets = google_sheet_reader.get_all_data(force_refresh=False)
    if 'Project Details' in sheets:
        df = sheets['Project Details']
        res = df[df['Project Name'].str.contains("Ring Road|Jammu", case=False, na=False)]
        print(res[['UPC Code', 'PIU Name', 'Project Name', 'RO Name']])

if __name__ == "__main__":
    search_details()
