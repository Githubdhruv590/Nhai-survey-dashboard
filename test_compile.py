import pandas as pd
from backend.services import google_sheet_reader
from backend.services.summary_engine import compile_master_data

def test():
    print("Testing compile_master_data fallback...")
    sheets = google_sheet_reader.get_all_data(force_refresh=False)
    df_details, df_merged = compile_master_data(sheets)
    
    from backend.services.hierarchy_cache import hierarchy_cache
    print("\n--- Cache Keys ---")
    print("RO to Zone:")
    for k, v in list(hierarchy_cache.ro_to_zone.items())[:5]:
        print(f"'{k}' -> '{v}'")
    print("PIU to RO:")
    for k, v in list(hierarchy_cache.piu_to_ro.items())[:5]:
        print(f"'{k}' -> '{v}'")

    print("\n--- df_merged sample ---")
    print(df_merged[["PIU Name", "RO Name", "Zone"]].head(5))
if __name__ == "__main__":
    test()
