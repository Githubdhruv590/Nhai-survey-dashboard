import sys
import pandas as pd
from backend.services.google_sheet_reader import get_all_data

print('Fetching data from Google Sheets...')
sheets = get_all_data(force_refresh=True)

df_list = []
total_rows_before = 0
total_rows_after = 0

print('\n' + '='*100)
print(f'%-40s | %-15s | %-15s' % ('Worksheet Name', 'Shape Before', 'Shape After'))
print('-'*100)

for sheet_name, df in sheets.items():
    shape_before = df.shape
    total_rows_before += df.shape[0]
    
    # Simulate the exact cleaning in compile_master_data
    if sheet_name == 'Project Details':
        continue
        
    df_clean = df.copy()
    
    df_clean['RO Worksheet Name'] = sheet_name
    
    shape_after = df_clean.shape
    total_rows_after += df_clean.shape[0]
    
    print(f'%-40s | %-15s | %-15s' % (sheet_name, str(shape_before), str(shape_after)))
    df_list.append(df_clean)

df_merged = pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()

print('-'*100)
print(f'%-40s | %-15s | %-15s' % ('TOTAL', str(total_rows_before), str(total_rows_after)))
print('='*100)
print(f'Final Merged Shape: {df_merged.shape}')

if 'Zone' not in df_merged.columns:
    print('WARNING: Zone column missing')
else:
    df_merged['Zone'] = df_merged['Zone'].fillna('').astype(str).str.strip()
    blank_zones = df_merged[(df_merged['Zone'] == '') | (df_merged['Zone'].str.lower() == 'nan')]
    print(f'\nFound {len(blank_zones)} rows with Blank Zone.')
    
    if len(blank_zones) > 0:
        print('\nEXACT 490 BLANK ZONE ROWS:')
        cols_to_print = ['Survey ID', 'UPC Code', 'Project Name', 'RO Worksheet Name', 'Scheduled Survey Date', 'Zone']
        available_cols = [c for c in cols_to_print if c in blank_zones.columns]
        
        # Print all of them, don't truncate
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        
        print(blank_zones[available_cols])
