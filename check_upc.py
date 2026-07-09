import pandas as pd
from backend.services import google_sheet_reader

def get_row():
    sheets = google_sheet_reader.get_all_data(force_refresh=False)
    df = sheets['Project Details']
    print(df[df['UPC Code'] == 'N/02007/01001/JK'][['UPC Code', 'PIU Name', 'Project Name']])

if __name__ == "__main__":
    get_row()
