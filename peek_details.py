import pandas as pd
from backend.services import google_sheet_reader

def peek_details():
    sheets = google_sheet_reader.get_all_data(force_refresh=False)
    if 'Project Details' in sheets:
        df = sheets['Project Details']
        jammu_upcs = [
            "N/02006/03001/JK",
            "N/02006/04007/JK",
            "N/02006/07001/JK",
            "N/02006/06001/JK",
            "N/02006/05001/JK"
        ]
        res = df[df['UPC Code'].isin(jammu_upcs)][['UPC Code', 'PIU Name', 'RO Name', 'Zone']]
        print("Project Details for Jammu UPCs:\n", res)

if __name__ == "__main__":
    peek_details()
