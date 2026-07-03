import pandas as pd
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict
import logging

logger = logging.getLogger("nhai_dashboard")

def parse_date(val) -> Optional[datetime]:
    """
    Robustly parses dates of multiple formats (e.g., YYYY-MM-DD, DD/MM/YYYY, etc.) 
    into a datetime object. Returns None if invalid or empty.
    """
    if pd.isna(val) or val is None:
        print("UNPARSEABLE DATE:", repr(val))
        return None
        
    # Handle actual datetime or Timestamp objects
    if isinstance(val, datetime):
        return val
    if hasattr(val, "to_pydatetime"):
        return val.to_pydatetime()
        
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ['nan', 'nat', 'none', 'unknown']:
        print("UNPARSEABLE DATE:", repr(val))
        return None
        
    # Handle Excel numeric dates
    try:
        num = float(val)
        if num > 10000: # Typical excel date range
            # Excel dates are days since 1899-12-30
            return (datetime(1899, 12, 30) + timedelta(days=num))
    except ValueError:
        pass
        
    # Try different formats
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d %b %Y", "%d-%b-%Y", "%d.%m.%Y", "%d.%m.%y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(val_str, fmt)
        except ValueError:
            continue
            
    # Try generic pandas conversion as last resort
    try:
        ts = pd.to_datetime(val_str, dayfirst=True, format='mixed', errors='coerce')
        if pd.isna(ts):
            print("UNPARSEABLE DATE:", repr(val))
            return None
        return ts.to_pydatetime()
    except Exception:
        print("UNPARSEABLE DATE:", repr(val))
        return None

def get_week_boundaries(dt: datetime) -> Tuple[datetime, datetime]:
    """
    Returns (Monday, Sunday) boundaries for a given datetime object.
    Monday is weekday 0, Sunday is weekday 6.
    """
    monday = dt - timedelta(days=dt.weekday())
    # Strip time details to keep dates pure
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return monday, sunday

def get_week_label(monday: datetime, sunday: datetime) -> str:
    """
    Generates label in the format: '23 Jun - 29 Jun' (day + abbreviated month).
    If it spans across years, optionally appends year.
    """
    if monday.year != sunday.year:
        return f"{monday.strftime('%d %b %Y')} - {sunday.strftime('%d %b %Y')}"
    return f"{monday.strftime('%d %b')} - {sunday.strftime('%d %b')}"

def get_unique_weeks(df: pd.DataFrame, date_column: str = "Scheduled Survey Date") -> List[Dict[str, str]]:
    """
    Extracts all unique weekly ranges based on a date column.
    Returns:
        List[Dict[str, str]]: e.g., [{"label": "23 Jun - 29 Jun", "start": "2026-06-23", "end": "2026-06-29"}]
        Sorted chronologically.
    """
    if df.empty or date_column not in df.columns:
        return []
        
    # Get all non-null parsed dates
    dates = []
    for val in df[date_column]:
        dt = parse_date(val)
        if dt:
            dates.append(dt)
            
    if not dates:
        return []
        
    # Find unique (Monday, Sunday) boundaries
    week_ranges = set()
    for dt in dates:
        monday, sunday = get_week_boundaries(dt)
        week_ranges.add((monday, sunday))
        
    # Sort chronologically
    sorted_weeks = sorted(list(week_ranges), key=lambda w: w[0])
    
    weeks_list = []
    for mon, sun in sorted_weeks:
        weeks_list.append({
            "label": get_week_label(mon, sun),
            "start": mon.strftime("%Y-%m-%d"),
            "end": sun.strftime("%Y-%m-%d")
        })
        
    return weeks_list

def filter_by_week(df: pd.DataFrame, week_start_str: str, week_end_str: str, date_column: str = "Scheduled Survey Date") -> pd.DataFrame:
    """
    Filters DataFrame rows where the date_column is within the week boundaries [start, end] inclusive.
    """
    if df.empty or date_column not in df.columns:
        return df
        
    try:
        start_date = datetime.strptime(week_start_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(week_end_str, "%Y-%m-%d").date()
    except ValueError as e:
        logger.error(f"Invalid week date strings passed to filter: {week_start_str}, {week_end_str}: {e}")
        return df
        
    def date_in_range(val) -> bool:
        dt = parse_date(val)
        if not dt:
            return False
        return start_date <= dt.date() <= end_date
        
    mask = df[date_column].apply(date_in_range)
    return df[mask]
