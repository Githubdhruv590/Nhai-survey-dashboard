import pandas as pd
import numpy as np
from typing import List, Dict, Any
from backend.services.week_engine import get_week_boundaries, get_week_label, parse_date
from backend.services.summary_engine import get_column_series
import logging

logger = logging.getLogger("nhai_dashboard")

def get_completion_pie_data(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Returns data for Completion Pie Chart (Completed vs Pending).
    """
    if df.empty:
        return [
            {"name": "Completed", "value": 0, "color": "#003366"},
            {"name": "Pending", "value": 0, "color": "#F26A36"}
        ]
        
    status_series = get_column_series(df, ["Survey Status", "status"])
    status_lower = status_series.astype(str).str.lower().str.strip()
    completed = int((status_lower == "completed").sum())
    pending = int((status_lower != "completed").sum())
    
    return [
        {"name": "Completed", "value": completed, "color": "#003366"},
        {"name": "Pending", "value": pending, "color": "#F26A36"}
    ]

def get_zone_comparison_data(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Returns data for Zone Comparison Bar Chart (Scheduled vs Completed per Zone).
    """
    if df.empty:
        return []
        
    zone_groups = df.groupby("Zone", dropna=False)
    chart_data = []
    
    for zone_name, group in zone_groups:
        zone_label = str(zone_name) if not pd.isna(zone_name) else "Unknown"
        status_series = get_column_series(group, ["Survey Status", "status"])
        status_lower = status_series.astype(str).str.lower().str.strip()
        
        scheduled = len(group)
        completed = int((status_lower == "completed").sum())
        
        chart_data.append({
            "zone": zone_label,
            "scheduled": scheduled,
            "completed": completed
        })
        
    chart_data.sort(key=lambda x: x["scheduled"], reverse=True)
    return chart_data

def get_weekly_trend_data(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Returns data for Weekly Trend (Scheduled and Completed surveys over time).
    Groups records by their week starting date.
    """
    if df.empty:
        return []
        
    # Extract week label and start date for each record
    dates_and_indices = []
    for idx, val in enumerate(df["Scheduled Survey Date"]):
        dt = parse_date(val)
        if dt:
            monday, sunday = get_week_boundaries(dt)
            dates_and_indices.append({
                "index": idx,
                "monday": monday,
                "label": get_week_label(monday, sunday)
            })
            
    if not dates_and_indices:
        return []
        
    df_weeks = pd.DataFrame(dates_and_indices)
    unique_weeks = df_weeks.groupby(["monday", "label"]).groups
    
    trend_data = []
    for (monday, label), indices in unique_weeks.items():
        sub_df = df.iloc[indices]
        status_series = get_column_series(sub_df, ["Survey Status", "status"])
        status_lower = status_series.astype(str).str.lower().str.strip()
        
        scheduled = len(sub_df)
        completed = int((status_lower == "completed").sum())
        completion_rate = round((completed / scheduled * 100), 2) if scheduled > 0 else 0.0
        
        trend_data.append({
            "monday": monday.strftime("%Y-%m-%d"),
            "week_label": label,
            "scheduled": scheduled,
            "completed": completed,
            "completion_rate": completion_rate
        })
        
    # Sort chronologically by Monday
    trend_data.sort(key=lambda x: x["monday"])
    return trend_data

def get_delay_distribution_data(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Returns data for Delay Distribution (histogram buckets of delay).
    """
    # Exclude pending and future scheduled surveys. We only care about completed surveys delays.
    status_series = get_column_series(df, ["Survey Status", "status"])
    status_lower = status_series.astype(str).str.lower().str.strip()
    completed_df = df[status_lower == "completed"]
    
    if completed_df.empty:
        return [
            {"range": "On Time", "count": 0},
            {"range": "1-3 Days", "count": 0},
            {"range": "4-7 Days", "count": 0},
            {"range": "8-14 Days", "count": 0},
            {"range": "15+ Days", "count": 0}
        ]
        
    delay_series = get_column_series(completed_df, ["Total Delay", "Total Delay \nD1 + D2 (Days)", "Total Delay (Days)"])
    delays = pd.to_numeric(delay_series, errors="coerce").fillna(0.0)
    
    on_time = int((delays <= 0).sum())
    d1_3 = int(((delays > 0) & (delays <= 3)).sum())
    d4_7 = int(((delays > 3) & (delays <= 7)).sum())
    d8_14 = int(((delays > 7) & (delays <= 14)).sum())
    d15_plus = int((delays > 14).sum())
    
    return [
        {"range": "On Time", "count": on_time},
        {"range": "1-3 Days", "count": d1_3},
        {"range": "4-7 Days", "count": d4_7},
        {"range": "8-14 Days", "count": d8_14},
        {"range": "15+ Days", "count": d15_plus}
    ]

def get_provider_performance_data(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Returns data for Provider Performance.
    DAS Provider Name -> Avg Precision, Avg Recall, Completion Rate, Surveys Scheduled.
    """
    # Exclude empty provider names
    prov_series = get_column_series(df, ["DAS Provider Name", "Provider Name"])
    valid_prov_df = df[prov_series.astype(str).str.strip() != ""]
    
    if valid_prov_df.empty:
        return []
        
    prov_groups = valid_prov_df.groupby("DAS Provider Name", dropna=False)
    chart_data = []
    
    for prov_name, group in prov_groups:
        prov_label = str(prov_name) if not pd.isna(prov_name) else "Unknown Provider"
        
        status_series = get_column_series(group, ["Survey Status", "status"])
        status_lower = status_series.astype(str).str.lower().str.strip()
        scheduled = len(group)
        completed = int((status_lower == "completed").sum())
        comp_rate = round((completed / scheduled * 100), 2) if scheduled > 0 else 0.0
        
        precision_series = get_column_series(group, ["Precision Score", "Precision Score (%)"])
        precision = pd.to_numeric(precision_series, errors="coerce")
        recall_series = get_column_series(group, ["Recall Score", "Recall Score (%)"])
        recall = pd.to_numeric(recall_series, errors="coerce")
        
        avg_prec = round(float(precision.mean()), 3) if precision.notna().sum() > 0 else 0.0
        avg_rec = round(float(recall.mean()), 3) if recall.notna().sum() > 0 else 0.0
        
        chart_data.append({
            "provider": prov_label,
            "scheduled": scheduled,
            "completed": completed,
            "completion_rate": comp_rate,
            "precision": avg_prec,
            "recall": avg_rec
        })
        
    chart_data.sort(key=lambda x: x["scheduled"], reverse=True)
    return chart_data
