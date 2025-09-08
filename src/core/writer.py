from __future__ import annotations
from pathlib import Path
from typing import List
import csv
import pandas as pd
import datetime as dt

def month_stamp_for_filename(value: str | None) -> dt.date:
    # value: 'YYYY-MM' or None → current month
    if value:
        return dt.datetime.strptime(value, "%Y-%m").date().replace(day=1)
    return dt.date.today().replace(day=1)

def save(df: pd.DataFrame, output_dir: Path, jobsite: str, month_yyyy_mm: str | None, formats: List[str]) -> List[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp_date = month_stamp_for_filename(month_yyyy_mm)
    stamp = stamp_date.strftime("%Y-%m")
    safe_jobsite = jobsite.replace(" ", "-")
    base = output_dir / f"approved-job-orders_{safe_jobsite}_{stamp}"

    written: List[Path] = []
    if "csv" in formats:
        p = base.with_suffix(".csv")
        df.to_csv(p, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
        written.append(p)
    if "xlsx" in formats:
        p = base.with_suffix(".xlsx")
        df.to_excel(p, index=False)
        written.append(p)
    return written
