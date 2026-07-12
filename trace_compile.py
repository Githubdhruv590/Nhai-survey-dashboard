import sys
import pandas as pd
from backend.services.google_sheet_reader import get_all_data
from backend.services.summary_engine import compile_master_data

print('Fetching data from Google Sheets...')
sheets = get_all_data(force_refresh=True)

df_details, df_merged = compile_master_data(sheets)

print('\n' + '='*100)
print(f'Final Merged Shape: {df_merged.shape}')
print('='*100)

blank_zones = df_merged[df_merged['Zone'].isin(['', 'Unknown Zone', 'Zone', 'nan', 'None']) | df_merged['Zone'].isna()]
print(f'\nFound {len(blank_zones)} rows with Blank Zone (or "Unknown Zone" or "Zone").')

if len(blank_zones) > 0:
    print('\nEXACT BLANK ZONE ROWS:')
    cols_to_print = ['Survey ID', 'UPC Code', 'Project Name', 'RO Worksheet Name', 'Scheduled Survey Date', 'Zone', 'PIU Name', 'RO Name']
    available_cols = [c for c in cols_to_print if c in blank_zones.columns]
    
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    
    print(blank_zones[available_cols])
