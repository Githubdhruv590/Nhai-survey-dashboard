import os
import time
import re
import logging
import threading
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from urllib.parse import quote
import pandas as pd
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request as AuthRequest
from backend.config.config import settings

logger = logging.getLogger("nhai_dashboard")

class SheetDataCache:
    """
    Thread-safe memory cache. Caches metadata, worksheets individually, and compiled master DataFrames.
    """
    def __init__(self):
        self.lock = threading.Lock()
        
        # Spreadsheet Metadata
        self.spreadsheet_name: str = "Not Configured"
        self.sheet_names: List[str] = []
        self.metadata_fetch_time: float = 0.0
        self.last_sync_time: str = ""
        
        # Worksheets Cache: sheet_name -> DataFrame
        self.worksheets: Dict[str, pd.DataFrame] = {}
        # Worksheets Fetch Times: sheet_name -> timestamp
        self.fetch_times: Dict[str, float] = {}
        
        # Compiled Master Cache
        self.master_df_details: Optional[pd.DataFrame] = None
        self.master_df_surveys: Optional[pd.DataFrame] = None
        
        # Connection status
        self.status: str = "Not Connected"
        self.error_message: str = ""

    def clear(self):
        with self.lock:
            self.spreadsheet_name = "Not Configured"
            self.sheet_names = []
            self.metadata_fetch_time = 0.0
            self.last_sync_time = ""
            self.worksheets.clear()
            self.fetch_times.clear()
            self.master_df_details = None
            self.master_df_surveys = None
            self.status = "Not Connected"
            self.error_message = ""
            logger.info("In-memory Google Sheets cache cleared.")

    def get_compiled_data(self, force_refresh: bool = False) -> Tuple[pd.DataFrame, pd.DataFrame]:
        expiry = settings.CACHE_EXPIRY_SECONDS
        now = time.time()
        
        with self.lock:
            if not force_refresh and self.master_df_details is not None and self.master_df_surveys is not None:
                if now - self.metadata_fetch_time < expiry:
                    logger.info("Serving compiled master dataframes from cache")
                    return self.master_df_details, self.master_df_surveys

        # Otherwise, load ALL worksheets and compile once
        from backend.services.summary_engine import compile_master_data
        
        logger.info("Loading all worksheets from Google Sheets for compiled cache...")
        spreadsheet_name, sheet_names = self.get_metadata(force_refresh)
        
        data_dict = {}
        for name in sheet_names:
            df = self.get_worksheet(name, force_refresh)
            data_dict[name] = df
            
        df_details, df_surveys = compile_master_data(data_dict)
        
        with self.lock:
            self.master_df_details = df_details
            self.master_df_surveys = df_surveys
            self.metadata_fetch_time = now
            self.last_sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.status = "Connected"
            self.error_message = ""
            
        return df_details, df_surveys

    def set_error(self, message: str):
        with self.lock:
            self.status = "Spreadsheet Not Connected"
            self.error_message = message

    def get_metadata(self, force_refresh: bool = False) -> Tuple[str, List[str]]:
        expiry = settings.CACHE_EXPIRY_SECONDS
        now = time.time()
        
        with self.lock:
            if not force_refresh and self.sheet_names and (now - self.metadata_fetch_time < expiry):
                return self.spreadsheet_name, self.sheet_names

        # Fetch fresh metadata
        spreadsheet_name, sheet_names = fetch_metadata_api()
        
        with self.lock:
            self.spreadsheet_name = spreadsheet_name
            self.sheet_names = sheet_names
            self.metadata_fetch_time = now
            self.last_sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.status = "Connected"
            self.error_message = ""
            
        return spreadsheet_name, sheet_names

    def get_worksheet(self, sheet_name: str, force_refresh: bool = False) -> pd.DataFrame:
        expiry = settings.CACHE_EXPIRY_SECONDS
        now = time.time()
        
        with self.lock:
            if not force_refresh and sheet_name in self.worksheets and (now - self.fetch_times.get(sheet_name, 0.0) < expiry):
                logger.info(f"Serving worksheet '{sheet_name}' from cache")
                return self.worksheets[sheet_name]

        # Fetch fresh worksheet DataFrame
        df = fetch_worksheet_api(sheet_name)
        
        with self.lock:
            self.worksheets[sheet_name] = df
            self.fetch_times[sheet_name] = now
            self.last_sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.status = "Connected"
            self.error_message = ""
            
        return df

# Global cache instance
_cache = SheetDataCache()

# Global sheets service / auth token cache
_auth_token = None
_auth_token_expiry = 0.0
_auth_lock = threading.Lock()

def check_for_rate_limit(e: Exception) -> bool:
    """
    Checks if the exception is an HTTP 429 Rate Limit / Quota Exceeded error.
    """
    err_str = str(e).lower()
    return "429" in err_str or "rate limit" in err_str or "quota" in err_str

def get_auth_headers_and_params(creds_file: Optional[str] = None, api_key: Optional[str] = None) -> Tuple[dict, dict, str]:
    """
    Resolves headers, query parameters, and auth method name based on credentials priority.
    Authentication priority: Credentials file (if exists) -> API Key -> Error
    """
    global _auth_token, _auth_token_expiry
    
    c_file = creds_file if creds_file is not None else settings.GOOGLE_CREDENTIALS_FILE
    a_key = api_key if api_key is not None else settings.GOOGLE_API_KEY
    
    # Normalize values
    c_file = str(c_file).strip() if c_file else ""
    a_key = str(a_key).strip() if a_key else ""
    
    # 1. Try Service Account if credentials file exists on disk
    if c_file and os.path.exists(c_file):
        try:
            with _auth_lock:
                now = time.time()
                # Use cached token if still valid (tokens expire in 3600 seconds, check 5 mins buffer)
                if _auth_token is not None and now < _auth_token_expiry - 300:
                    return {"Authorization": f"Bearer {_auth_token}"}, {}, "Service Account"
                    
                scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
                creds = service_account.Credentials.from_service_account_file(c_file, scopes=scopes)
                creds.refresh(AuthRequest())
                _auth_token = creds.token
                _auth_token_expiry = now + 3600
                return {"Authorization": f"Bearer {_auth_token}"}, {}, "Service Account"
        except Exception as e:
            logger.error(f"Service account auth failed: {e}")
            raise ValueError(f"Service Account credentials error: {e}")
            
    # 2. Try API Key
    elif a_key:
        return {}, {"key": a_key}, "API Key"
        
    # 3. Raise configuration error
    else:
        raise ValueError("Google authentication is not configured. Please configure a valid credentials.json file path or a GOOGLE_API_KEY.")

def make_google_sheets_request(url: str, creds_file: Optional[str] = None, api_key: Optional[str] = None) -> dict:
    """
    Makes a GET request to the Google Sheets REST API with retry logic and error mapping.
    """
    retries = 3
    delay = 1.0
    
    for attempt in range(retries + 1):
        try:
            headers, params, auth_method = get_auth_headers_and_params(creds_file, api_key)
            response = requests.get(url, headers=headers, params=params, timeout=15)
            
            # Quota exceeded check
            if response.status_code == 429:
                logger.error("Google Sheets API quota exceeded (HTTP 429). Aborting retries.")
                raise ValueError("Google Sheets API quota exceeded. Please wait approximately one minute before retrying.")
                
            # Permission denied check
            if response.status_code == 403:
                raise ValueError(f"Permission denied: {response.text}")
                
            # Not found check
            if response.status_code == 404:
                raise ValueError(f"Spreadsheet not found: {response.text}")
                
            # Success check
            if response.status_code == 200:
                return response.json()
                
            # Retry on 500/503/504 errors
            if response.status_code >= 500:
                if attempt == retries:
                    raise ValueError(f"Google API unavailable (HTTP {response.status_code}): {response.text}")
                logger.warning(f"Google API HTTP {response.status_code} retry {attempt + 1}/3 in {delay:.1f}s")
                time.sleep(delay)
                delay *= 2.0
                continue
                
            # Other errors
            raise ValueError(f"HTTP Error {response.status_code}: {response.text}")
            
        except requests.exceptions.RequestException as e:
            if attempt == retries:
                logger.error(f"Network error after {retries} retries: {e}")
                raise ValueError(f"Google API unavailable: {e}")
            logger.warning(f"Google API network retry {attempt + 1}/3 in {delay:.1f}s due to error: {e}")
            time.sleep(delay)
            delay *= 2.0

def map_exception_to_friendly_error(e: Exception) -> str:
    """
    Maps exceptions to clean, user-friendly error messages.
    """
    err_str = str(e).lower()
    if "quota exceeded" in err_str or "429" in err_str:
        return "Google Sheets API quota exceeded. Please wait approximately one minute before retrying."
    if "credentials" in err_str or "service account credentials error" in err_str:
        return "Credentials file missing or invalid."
    if "permission denied" in err_str or "403" in err_str:
        return "Spreadsheet permission denied."
    if "not found" in err_str or "404" in err_str:
        return "Spreadsheet not found or invalid URL."
    if "key is invalid" in err_str or "api key" in err_str:
        return "Google API key is invalid."
    if "unavailable" in err_str or "connection" in err_str or "timeout" in err_str:
        return "Google API unavailable."
    return f"Access error: {str(e)}"

def extract_spreadsheet_id(url: str) -> str:
    """
    Extracts the spreadsheet ID from a Google Sheets URL.
    """
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    if match:
        return match.group(1)
    return url

def fetch_metadata_api() -> Tuple[str, List[str]]:
    spreadsheet_id = settings.spreadsheet_id
    if not spreadsheet_id:
        raise ValueError("GOOGLE_SHEET_URL is missing. Please configure your spreadsheet.")
        
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
    try:
        sheet_metadata = make_google_sheets_request(url)
    except Exception as e:
        friendly = map_exception_to_friendly_error(e)
        raise ValueError(friendly)

    spreadsheet_name = sheet_metadata.get("properties", {}).get("title", "NHAI Survey Spreadsheet")
    sheets = sheet_metadata.get("sheets", [])
    sheet_names = [s.get("properties", {}).get("title") for s in sheets if s.get("properties", {}).get("title")]
    return spreadsheet_name, sheet_names

def fetch_worksheet_api(sheet_name: str) -> pd.DataFrame:
    spreadsheet_id = settings.spreadsheet_id
    if not spreadsheet_id:
        raise ValueError("GOOGLE_SHEET_URL is missing. Please configure your spreadsheet.")
        
    encoded_sheet_name = quote(sheet_name)
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{encoded_sheet_name}"
    
    try:
        result = make_google_sheets_request(url)
    except Exception as e:
        friendly = map_exception_to_friendly_error(e)
        raise ValueError(f"Error fetching worksheet '{sheet_name}': {friendly}")
        
    values = result.get("values", [])
    return parse_sheet_values(values)

def parse_sheet_values(values: List[List]) -> pd.DataFrame:
    """
    Converts list of rows into a padded DataFrame with deduplicated headers,
    dynamically skipping empty or metadata rows at the top.
    """
    if not values:
        return pd.DataFrame()
    
    # Find the actual header row (the first row with at least 3 non-empty cells)
    header_idx = 0
    for idx, row in enumerate(values):
        clean_row = [str(cell).strip() for cell in row if str(cell).strip()]
        if len(clean_row) > 2:
            header_idx = idx
            break
            
    header_row = values[header_idx]
    raw_headers = [str(h).strip() for h in header_row]
    
    # Deduplicate headers to avoid pandas duplicate column bugs
    seen = {}
    headers = []
    for h in raw_headers:
        if not h:
            h = "UnnamedCol"
        if h in seen:
            seen[h] += 1
            headers.append(f"{h}_{seen[h]}")
        else:
            seen[h] = 0
            headers.append(h)
            
    rows = values[header_idx + 1:]
    
    padded_rows = []
    for row in rows:
        if len(row) < len(headers):
            row = list(row) + [""] * (len(headers) - len(row))
        elif len(row) > len(headers):
            row = list(row)[:len(headers)]
        padded_rows.append(row)
        
    df = pd.DataFrame(padded_rows, columns=headers)
    for i in range(df.shape[1]):
        series = df.iloc[:, i]
        if series.dtype == object:
            df.iloc[:, i] = series.astype(str).str.strip()
            
    # Remove phantom empty rows (padding rows in Google Sheets)
    # Match columns loosely as they may contain newlines or slight variations
    def get_col(candidates):
        for col in df.columns:
            col_lower = col.lower().replace('\n', '').replace(' ', '')
            if any(c in col_lower for c in candidates):
                return col
        return None
        
    upc_col = get_col(["upccode", "upc"])
    proj_col = get_col(["projectname"])
    sid_col = get_col(["surveyid"])
    sched_col = get_col(["scheduledsurvey", "scheduleddate"])
    actual_col = get_col(["actualsurvey", "actualdate"])
    
    # If this is a survey sheet (has these 3 core columns)
    if upc_col and proj_col and sid_col:
        # Check if all these key columns are effectively blank
        def is_blank(col_name):
            return df[col_name].isna() | (df[col_name].astype(str).str.strip() == "") | (df[col_name].astype(str).str.lower() == "nan")
            
        mask = is_blank(upc_col) & is_blank(proj_col) & is_blank(sid_col)
        if sched_col:
            mask = mask & is_blank(sched_col)
        if actual_col:
            mask = mask & is_blank(actual_col)
            
        df = df[~mask].copy()
        
    return df

def get_spreadsheet_metadata(force_refresh: bool = False) -> Tuple[str, List[str]]:
    """
    Lazy wrapper for spreadsheet title and sheet list.
    """
    return _cache.get_metadata(force_refresh)

def get_worksheet_data(sheet_name: str, force_refresh: bool = False) -> pd.DataFrame:
    """
    Lazy wrapper for single sheet DataFrame.
    """
    return _cache.get_worksheet(sheet_name, force_refresh)

def get_all_data(force_refresh: bool = False) -> Dict[str, pd.DataFrame]:
    """
    Legacy wrapper. Automatically fetches and returns all worksheets from cache.
    """
    _, sheet_names = get_spreadsheet_metadata(force_refresh)
    data_dict = {}
    for name in sheet_names:
        data_dict[name] = get_worksheet_data(name, force_refresh)
    return data_dict

def get_compiled_data(force_refresh: bool = False) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Wrapper for retrieving cleaned, compiled master DataFrames.
    """
    return _cache.get_compiled_data(force_refresh)

def get_connection_status() -> dict:
    """
    Returns connection status details.
    """
    return {
        "status": _cache.status,
        "spreadsheet_name": _cache.spreadsheet_name,
        "worksheets_count": len(_cache.sheet_names),
        "last_sync_time": _cache.last_sync_time,
        "error_message": _cache.error_message
    }

def test_connection_params(url: str, creds_file: Optional[str], api_key: Optional[str]) -> dict:
    """
    Validates spreadsheet connectivity using official REST API.
    """
    if not url:
        raise ValueError("Google Sheet URL is missing.")

    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    spreadsheet_id = match.group(1) if match else url
    
    api_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
    
    try:
        _, _, auth_method = get_auth_headers_and_params(creds_file, api_key)
        sheet_metadata = make_google_sheets_request(api_url, creds_file=creds_file, api_key=api_key)
    except Exception as e:
        friendly = map_exception_to_friendly_error(e)
        raise ValueError(f"Connection test failed: {friendly}")

    spreadsheet_name = sheet_metadata.get("properties", {}).get("title", "Valid Spreadsheet")
    sheets = sheet_metadata.get("sheets", [])
    sheet_names = [s.get("properties", {}).get("title") for s in sheets if s.get("properties", {}).get("title")]

    if not any(name.lower().strip() == "project details" for name in sheet_names):
        raise KeyError("Project Details worksheet missing in the spreadsheet.")

    return {
        "status": "Success",
        "spreadsheet_name": spreadsheet_name,
        "worksheets_count": len(sheet_names),
        "sheet_names": sheet_names,
        "auth_method": auth_method
    }

def clear_cache():
    """
    Clears cache and resets the service client cache.
    """
    global _auth_token, _auth_token_expiry
    _cache.clear()
    with _auth_lock:
        _auth_token = None
        _auth_token_expiry = 0.0
