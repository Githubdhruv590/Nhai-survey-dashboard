import logging
from collections import defaultdict
from typing import List, Dict, Tuple, Set

logger = logging.getLogger("nhai_dashboard")

class MetadataRecoveryRule:
    def __init__(self, target_field: str, source_field: str):
        self.target_field = target_field
        self.source_field = source_field

class MetadataRecoveryEngine:
    def __init__(self, rules: List[MetadataRecoveryRule]):
        self.rules = rules

    def recover(self, records: List[dict]) -> List[dict]:
        """
        Applies metadata recovery rules to the given records in-place.
        Returns the modified list of records.
        """
        if not self.rules or not records:
            return records
            
        for rule in self.rules:
            self._apply_rule(rule, records)
            
        return records

    def _apply_rule(self, rule: MetadataRecoveryRule, records: List[dict]):
        # Phase 1: Scan and build mapping
        # Mapping: source_value -> List[target_value]
        # We only consider records that have both the source and target fields populated.
        mapping: Dict[str, List[str]] = defaultdict(list)
        
        for record in records:
            source_val = str(record.get(rule.source_field, "")).strip()
            target_val = str(record.get(rule.target_field, "")).strip()
            
            # If both are present (not blank or nan), add to mapping
            if source_val and target_val and source_val.lower() not in ["nan", "none"] and target_val.lower() not in ["nan", "none"]:
                mapping[source_val].append(target_val)
                
        # Phase 2: Compute reliable recoveries
        # A recovery is safe ONLY if:
        # 1. At least 2 matching records exist for this source_val
        # 2. All matching records agree exactly on the target_val
        safe_recoveries: Dict[str, str] = {}
        
        for source_val, target_vals in mapping.items():
            if len(target_vals) >= 2:
                unique_targets = set(v.lower() for v in target_vals)
                if len(unique_targets) == 1:
                    # 100% agreement and at least 2 records
                    safe_recoveries[source_val] = target_vals[0]
                else:
                    # Conflict! Log it.
                    logger.warning(
                        f"[Metadata Recovery Engine] Conflict detected for rule {rule.source_field}->{rule.target_field}. "
                        f"Source '{source_val}' maps to multiple conflicting targets: {set(target_vals)}. "
                        f"Skipping recovery."
                    )
        
        # Phase 3: Apply safe recoveries to records missing the target field
        for record in records:
            source_val = str(record.get(rule.source_field, "")).strip()
            target_val = str(record.get(rule.target_field, "")).strip()
            
            is_target_missing = not target_val or target_val.lower() in ["nan", "none"]
            is_source_present = source_val and source_val.lower() not in ["nan", "none"]
            
            if is_target_missing and is_source_present:
                if source_val in safe_recoveries:
                    recovered_val = safe_recoveries[source_val]
                    record[rule.target_field] = recovered_val
                    
                    survey_id = record.get("survey_id", "Unknown")
                    logger.info(
                        f"[Metadata Recovery Engine] Recovered {rule.target_field} for Survey '{survey_id}'. "
                        f"{rule.source_field}='{source_val}'. Recovered Value='{recovered_val}'"
                    )
                elif source_val in mapping:
                    # It was in the mapping, but didn't meet confidence criteria
                    if len(set(v.lower() for v in mapping[source_val])) == 1 and len(mapping[source_val]) < 2:
                         logger.warning(
                            f"[Metadata Recovery Engine] Could not safely recover {rule.target_field} for Survey '{record.get('survey_id', 'Unknown')}'. "
                            f"Reason: Only 1 matching record exists for {rule.source_field}='{source_val}'. Confidence not 100%."
                         )
