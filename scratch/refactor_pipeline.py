import re

def refactor():
    path = r"c:\Users\dhruv\OneDrive\Pictures\Down\Desktop\Desktop files\NHAI-Survey-Dashboard\backend\services\refresh_pipeline.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the cache generation block
    cache_pattern = r"(        # 4\. Generate Precomputed Dashboard Caches.*?cache_build_time = time\.time\(\) - t0\n)"
    cache_match = re.search(cache_pattern, content, re.DOTALL)
    
    # Find the survey mapping and sync block
    sync_pattern = r"(        # Map merged df to SurveyMaster dictionaries.*?            raise swap_err\n)"
    sync_match = re.search(sync_pattern, content, re.DOTALL)
    
    if not cache_match or not sync_match:
        print("Blocks not found!")
        return
        
    cache_block = cache_match.group(1)
    sync_block = sync_match.group(1)
    
    # We replace cache_block with sync_block + modified cache_block
    # Wait, the modified cache block uses df_validated instead of df_merged
    
    new_cache_block = cache_block.replace("df_merged", "df_validated")
    new_cache_block = new_cache_block.replace(
        "# 4. Generate Precomputed Dashboard Caches",
        "# 7. Generate Precomputed Dashboard Caches\n        from backend.services.db_queries import DB_TO_PANDAS_MAP\n        df_validated = pd.DataFrame(valid_records).rename(columns=DB_TO_PANDAS_MAP)"
    )
    
    # Fix the comments in sync_block
    sync_block = sync_block.replace("Map merged df", "4. Map merged df")
    sync_block = sync_block.replace("# 5. Business Key Validation", "# 5. Business Key Validation")
    sync_block = sync_block.replace("# 6. Populate Temporary Table", "# 6. Populate Temporary Table")
    
    # Now replace the original content
    content = content.replace(cache_block, sync_block + "\n" + new_cache_block)
    
    # Finally, remove the original sync_block since it was moved
    # But string replacement might be tricky if it's the exact same string.
    # Let's just slice it.
    
    # Actually, replacing the original sync_block with "" will work because we concatenated it above.
    # Wait, let's just do a clean split.
    
    start_cache = cache_match.start()
    end_cache = cache_match.end()
    
    start_sync = sync_match.start()
    end_sync = sync_match.end()
    
    # Assuming cache comes before sync
    if start_cache < start_sync:
        new_content = content[:start_cache] + sync_block + "\n" + new_cache_block + content[end_cache:start_sync] + content[end_sync:]
    
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("Refactored successfully.")
    else:
        print("Unexpected order")
        
refactor()
