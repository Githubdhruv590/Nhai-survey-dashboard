import sys
sys.path.insert(0, 'backend')
from backend.services import google_sheet_reader

def peek_ppm():
    sheets = google_sheet_reader.get_all_data(force_refresh=True)
    if 'PPM' in sheets:
        df = sheets['PPM']
        print("PPM columns:", df.columns.tolist())
        print("PPM head:\n", df.head(20))
    else:
        print("PPM sheet not found in sheets. Available sheets:", sheets.keys())

if __name__ == "__main__":
    peek_ppm()
