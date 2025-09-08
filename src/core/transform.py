from __future__ import annotations
from typing import Dict, List
import pandas as pd

def to_dataframe(rows: List[Dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    df = pd.json_normalize(rows, sep=".")
    # Sort columns for stable output
    return df.reindex(sorted(df.columns), axis=1)
