import os
import sys
import pandas as pd
from backend.services.google_sheet_reader import get_all_data
from backend.services.summary_engine import compile_master_data, normalize_dataframe_columns

def trace():
    print("=== TRACE START ===")
    sheets = get_all_data(force_refresh=True)
    
    ro_dfs = []
    
    # 1. Print raw worksheet names and shapes
    print("\n--- RAW WORKSHEETS ---")
    for name, df in sheets.items():
        print(f"Worksheet Name: {name} | Shape Before Cleaning: {df.shape}")
        if name.lower().strip() == 'project details':
            continue
            
        df_copy = df.copy()
        df_copy['RO Worksheet Name'] = name
        ro_dfs.append(df_copy)
        
    # 2. Concatenate
    if ro_dfs:
        df_concat = pd.concat(ro_dfs, ignore_index=True)
        print(f"\nShape After Concatenation: {df_concat.shape}")
    else:
        print("\nNo RO worksheets found.")
        return
        
    # 3. Find Blank Zones using the exact compile_master_data pipeline
    print("\n--- RUNNING COMPILE_MASTER_DATA ---")
    df_details, df_merged = compile_master_data(sheets)
    print(f"Compiled Master Data Shape: {df_merged.shape}")
    
    # 4. Find the 490 Blank Zones
    print("\n--- IDENTIFYING BLANK / INVALID ZONES ---")
    zone_series = df_merged['Zone'].astype(str).str.strip()
    blank_zones = df_merged[
        (zone_series == 'Zone') | 
        (zone_series == '') | 
        (zone_series == 'nan') | 
        (zone_series == 'None') | 
        (zone_series == 'Unknown Zone')
    ]
    
    print(f"Total Blank/Invalid Zones found: {len(blank_zones)}")
    
    if len(blank_zones) > 0:
        print("\n=== EXACT ROWS WITH BLANK ZONES ===")
        cols = ['Survey ID', 'UPC Code', 'Project Name', 'RO Worksheet Name', 'Scheduled Survey Date', 'Zone']
        print_cols = [c for c in cols if c in blank_zones.columns]
        pd.set_option('display.max_rows', None)
        print(blank_zones[print_cols])
    else:
        print("\nZERO blank zone rows were produced by compile_master_data() with the current Google Sheet data.")
        
if __name__ == '__main__':
    trace()
