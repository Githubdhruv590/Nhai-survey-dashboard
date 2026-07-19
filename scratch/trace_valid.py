import sys, logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
from backend.services import google_sheet_reader
from backend.services.summary_engine import compile_master_data
from backend.services.business_validation import validate_business_keys
from backend.utils.refresh_logger import RefreshLogger
import time

sheets = google_sheet_reader.get_all_data(force_refresh=False)
df_details, df_merged = compile_master_data(sheets)

df_merged = df_merged.fillna('')
survey_records = []
def safe_float(v):
    try: return float(str(v).strip().replace('%', ''))
    except: return 0.0
def safe_int(v):
    try: return int(float(str(v).strip().replace('%', '')))
    except: return 0

for _, row in df_merged.iterrows():
    survey_records.append({
        'survey_id': str(row.get('Survey ID', '')),
        'zone': str(row.get('Zone', '')),
        'ro_name': str(row.get('RO Name', '')),
        'piu_name': str(row.get('PIU Name', '')),
        'project_name': str(row.get('Project Name', '')),
        'upc_code': str(row.get('UPC Code', '')),
        'das_provider': str(row.get('DAS Provider Name', '')),
        'survey_status': str(row.get('Survey Status', '')),
        'scheduled_survey_date': str(row.get('Scheduled Survey Date', '')),
        'actual_survey_date': str(row.get('Actual Survey Date', '')),
        'total_delay': safe_float(row.get('Total Delay (Days)')),
        'ir_count': safe_int(row.get('IR Count')),
    })

logger = RefreshLogger('test', 'test', time.time())
valid_records, all_business_keys, val_metrics = validate_business_keys(survey_records, logger)

print(f'\nTotal Input Rows: {len(survey_records)}')
print(f'Total Valid Rows: {len(valid_records)}')
print(f'Total Invalid Rows: {val_metrics.get("invalid_rows", 0)}')
print(f'Total Business Keys: {len(all_business_keys)}')

invalid = [r for r in survey_records if r not in valid_records]
print('\nInvalid Reasons:')
reasons = {}
for r in invalid:
    r_key = r.get('_validation_reason', 'Unknown/Filtered')
    reasons[r_key] = reasons.get(r_key, 0) + 1
for k, v in reasons.items():
    print(f'{v} - {k}')
