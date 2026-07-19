import sys

path = r"c:\Users\dhruv\OneDrive\Pictures\Down\Desktop\Desktop files\NHAI-Survey-Dashboard\backend\services\refresh_pipeline.py"

with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

out = []
i = 0

# We want to extract the cache block (154-171), and the survey/sync block (173-250), and the dashboard cache (252-275).
# Actually let's just rewrite the whole function from line 150 downwards manually via a python script that replaces the entire process_google_sheet_data remainder.

# Let's see the lines of process_google_sheet_data
start_idx = 0
for i, line in enumerate(lines):
    if "survey_count = len(df_merged)" in line:
        start_idx = i
        break

def extract_block(pattern_start, pattern_end):
    start = -1
    end = -1
    for i, line in enumerate(lines):
        if pattern_start in line:
            start = i
        if start != -1 and pattern_end in line:
            end = i
            break
    if start == -1 or end == -1:
        return []
    return lines[start:end+1]

cache_block = extract_block("# 4. Generate Precomputed Dashboard Caches", "cache_build_time = time.time() - t0")
sync_block = extract_block("# Map merged df to SurveyMaster dictionaries", "raise swap_err")

# Modify cache block to use df_validated
new_cache_block = []
for line in cache_block:
    l = line.replace("df_merged", "df_validated")
    if "# 4." in l:
        l = l.replace("# 4.", "# 7.")
    new_cache_block.append(l)

new_cache_block.insert(1, "        from backend.services.db_queries import DB_TO_PANDAS_MAP\n")
new_cache_block.insert(2, "        import pandas as pd\n")
new_cache_block.insert(3, "        df_validated = pd.DataFrame(valid_records).rename(columns=DB_TO_PANDAS_MAP)\n")

# Modify sync block comments
new_sync_block = []
for line in sync_block:
    l = line.replace("Map merged df", "4. Map merged df")
    new_sync_block.append(l)
    
# Construct new file
new_lines = lines[:start_idx+3] + new_sync_block + ["\n"] + new_cache_block + ["\n"]

# Find what comes after cache_build_time = time.time() - t0 in the original cache_block
post_cache_start = -1
for i, line in enumerate(lines):
    if "raise swap_err" in line:
        post_cache_start = i + 1
        break

new_lines.extend(lines[post_cache_start:])

with open(path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print("Done")
