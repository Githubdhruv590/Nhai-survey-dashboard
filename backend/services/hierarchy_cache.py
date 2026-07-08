import pandas as pd
import logging

logger = logging.getLogger(__name__)

class HierarchyCache:
    def __init__(self):
        self.piu_to_ro = {}
        self.ro_to_zone = {}
        
        self.total_zones = 0
        self.total_ros = 0
        self.total_pius = 0
        self.duplicate_entries = 0
        self.blank_pius = 0
        self.blank_ros = 0
        self.is_built = False

    def build(self, ppm_df: pd.DataFrame):
        logger.info("Building PPM hierarchy cache...")
        self.piu_to_ro.clear()
        self.ro_to_zone.clear()
        
        self.total_zones = 0
        self.total_ros = 0
        self.total_pius = 0
        self.duplicate_entries = 0
        self.blank_pius = 0
        self.blank_ros = 0
        
        if ppm_df.empty:
            self.is_built = True
            return
            
        # Create a copy to avoid SettingWithCopyWarning
        df = ppm_df.copy()
        
        # Forward fill RO to handle merged cells vertically
        if "RO" in df.columns:
            df["RO_ffill"] = df["RO"].ffill()
        else:
            df["RO_ffill"] = None
            
        current_zone = "Unknown Zone"
        
        for idx, row in df.iterrows():
            row_str = " ".join([str(x) for x in row.values if pd.notna(x)]).upper()
            
            # Check for Zone row
            if "ZONE" in row_str and "TOTAL" not in row_str:
                zone_parts = row_str.split("ZONE")
                current_zone = (zone_parts[0] + "ZONE").strip().title()
                # Some cleanups like "North Zone ("
                if "(" in current_zone:
                    current_zone = current_zone.split("(")[0].strip()
                self.total_zones += 1
                continue
                
            # Data row extraction
            piu = str(row.get("PIU", "")).strip() if "PIU" in row else ""
            if piu == "nan" or piu == "None": piu = ""
                
            ro = str(row.get("RO_ffill", "")).strip() if "RO_ffill" in row else ""
            if ro == "nan" or ro == "None": ro = ""
            
            if not piu and not ro:
                continue
                
            if not piu:
                self.blank_pius += 1
            else:
                if piu in self.piu_to_ro:
                    self.duplicate_entries += 1
                self.piu_to_ro[piu] = ro
                
            if not ro:
                self.blank_ros += 1
            else:
                self.ro_to_zone[ro] = current_zone
                
        self.total_ros = len(self.ro_to_zone)
        self.total_pius = len(self.piu_to_ro)
        
        print("\n==================================================================")
        print("PPM sheet loaded successfully.")
        print(f"Total Zones: {self.total_zones}")
        print(f"Total ROs: {self.total_ros}")
        print(f"Total PIUs: {self.total_pius}")
        print(f"Total hierarchy entries: {self.total_ros + self.total_pius}")
        print(f"Duplicate entries: {self.duplicate_entries}")
        print(f"Blank PIUs: {self.blank_pius}")
        print(f"Blank ROs: {self.blank_ros}")
        print("Cache built successfully.")
        print("==================================================================\n")
        
        self.is_built = True
        
    def build_from_details(self, details_df: pd.DataFrame):
        logger.info("Building hierarchy cache from Project Details (PPM fallback)...")
        self.piu_to_ro.clear()
        self.ro_to_zone.clear()
        
        if details_df.empty:
            self.is_built = True
            return
            
        for _, row in details_df.iterrows():
            zone = str(row.get("Zone", "")).strip()
            ro = str(row.get("RO Name", "")).strip()
            piu = str(row.get("PIU Name", "")).strip()
            
            if zone and zone.lower() not in ["nan", "none"] and ro and ro.lower() not in ["nan", "none"]:
                self.ro_to_zone[ro] = zone
            
            if piu and piu.lower() not in ["nan", "none"] and ro and ro.lower() not in ["nan", "none"]:
                self.piu_to_ro[piu] = ro
                
        self.is_built = True
        
    def get_zone_for_ro(self, ro_name: str) -> str:
        if not ro_name:
            return ""
        # Handle case insensitivity if needed, but for now exact match or similar
        return self.ro_to_zone.get(ro_name, "")
        
    def get_ro_for_piu(self, piu_name: str) -> str:
        if not piu_name:
            return ""
        return self.piu_to_ro.get(piu_name, "")

# Global singleton instance
hierarchy_cache = HierarchyCache()
