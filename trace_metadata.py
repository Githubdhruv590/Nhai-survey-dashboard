import logging
import sys

# Minimal tracing script
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
from backend.services.metadata_recovery import MetadataRecoveryEngine, MetadataRecoveryRule

def trace():
    # Simulate a single row that is missing Zone
    records = [
        {"survey_id": "1", "piu_name": "Delhi PIU", "zone": "North"},
        {"survey_id": "2", "piu_name": "Delhi PIU", "zone": "North"},
        {"survey_id": "3", "piu_name": "Delhi PIU", "zone": ""},
    ]
    
    print("Stage 1: Before Validation")
    print(f"Record 3 zone: '{records[2]['zone']}'")
    
    engine = MetadataRecoveryEngine(rules=[MetadataRecoveryRule(target_field="zone", source_field="piu_name")])
    valid_records = engine.recover(records)
    
    print("\nStage 2: After Metadata Recovery (in validate_business_keys)")
    print(f"Record 3 zone: '{valid_records[2]['zone']}'")
    
    print("\nStage 3: Cache Generation (Happens BEFORE validate_business_keys in refresh_pipeline.py)")
    print("df_merged still has the original empty zone, because df_merged is NEVER updated by the recovery engine!")
    
    print("\nStage 4: Database UPSERT (Happens AFTER validate_business_keys)")
    print(f"valid_records sent to sync_to_database has zone='{valid_records[2]['zone']}'")
    print("Therefore, the database is correctly populated, but the DashboardCache is completely stale.")
    print("\nRoot Cause identified: Cache generation occurs before business validation.")

if __name__ == '__main__':
    trace()
