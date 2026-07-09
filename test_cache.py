import pandas as pd
from backend.services.hierarchy_cache import hierarchy_cache

data = {
    "S.NO": ["NORTH ZONE ( Delhi , Haryana )", 1, 2, "WEST ZONE( Gujarat )", 3],
    "STATE": [None, "Chandigarh", None, None, "Gujarat"],
    "RO": [None, "CHANDIGARH", None, None, "GANDHINAGAR"],
    "PIU": [None, "Ambala", "Rohtak", None, "Ahmedabad"]
}

df = pd.DataFrame(data)

hierarchy_cache.build(df)

print(hierarchy_cache.get_ro_for_piu("Rohtak"))
print(hierarchy_cache.get_zone_for_ro("CHANDIGARH"))
print(hierarchy_cache.get_zone_for_ro("GANDHINAGAR"))
