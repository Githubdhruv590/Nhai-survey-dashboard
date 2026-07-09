import pandas as pd
from backend.services.summary_engine import compile_master_data
from backend.services.hierarchy_cache import build as build_cache

build_cache()
df = compile_master_data()

print("\n--- df_merged[['Zone','RO Name','PIU Name']].head(20) ---")
print(df[["Zone", "RO Name", "PIU Name"]].head(20))

print("\n--- value_counts of Zone ---")
print(df["Zone"].value_counts(dropna=False))

print("\n--- value_counts of RO Name ---")
print(df["RO Name"].value_counts(dropna=False))

print("\n--- value_counts of PIU Name ---")
print(df["PIU Name"].value_counts(dropna=False))
