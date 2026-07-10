import re

with open(r'c:\Users\dhruv\OneDrive\Pictures\Down\Desktop\Desktop files\NHAI-Survey-Dashboard\backend\services\google_sheet_reader.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Strip the class SheetDataCache down to fetch_metadata_api
content = re.sub(r'class SheetDataCache.*?def get_metadata\(', 'def fetch_metadata_api(', content, flags=re.DOTALL)

# 2. Fix indentation
lines = content.split('\n')
new_lines = []
inside_cache = False

for line in lines:
    if line.startswith('    def get_metadata('):
        inside_cache = True
        new_lines.append('def get_spreadsheet_metadata(force_refresh: bool = False):\n    return fetch_metadata_api()\n')
        continue
    
    if inside_cache and line.startswith('def map_exception_to_friendly_error'):
        inside_cache = False
        
    if not inside_cache:
        new_lines.append(line)

content = '\n'.join(new_lines)

# 3. Replace wrappers at bottom
wrapper_replacements = """def get_spreadsheet_metadata(force_refresh: bool = False):
    return fetch_metadata_api()

def get_all_data(force_refresh: bool = False):
    _, sheet_names = get_spreadsheet_metadata()
    data_dict = {}
    for name in sheet_names:
        data_dict[name] = fetch_worksheet_api(name)
    return data_dict

def get_connection_status() -> dict:
    try:
        spreadsheet_name, sheet_names = get_spreadsheet_metadata()
        return {
            "status": "Connected",
            "spreadsheet_name": spreadsheet_name,
            "worksheets_count": len(sheet_names),
            "sheet_names": sheet_names
        }
    except Exception as e:
        return {
            "status": "Error",
            "spreadsheet_name": "N/A",
            "worksheets_count": 0,
            "sheet_names": [],
            "error_message": str(e)
        }
"""

content = re.sub(r'def get_spreadsheet_metadata.*', wrapper_replacements, content, flags=re.DOTALL)
content = content.replace('_cache = SheetDataCache()', '')
content = content.replace('def fetch_metadata_api(self, force_refresh: bool = False)', 'def fetch_metadata_api()')
content = content.replace('spreadsheet_id = settings.spreadsheet_id', 'spreadsheet_id = extract_spreadsheet_id(settings.GOOGLE_SHEET_URL)')
content = content.replace('def map_exception_to_friendly_error(e: Exception) -> str:', '''def extract_spreadsheet_id(url: str) -> str:
    if not url: return ""
    import re
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
    return match.group(1) if match else url

def map_exception_to_friendly_error(e: Exception) -> str:''')

with open(r'c:\Users\dhruv\OneDrive\Pictures\Down\Desktop\Desktop files\NHAI-Survey-Dashboard\backend\services\google_sheet_reader.py', 'w', encoding='utf-8') as f:
    f.write(content)
