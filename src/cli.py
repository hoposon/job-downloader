# src/cli.py
from __future__ import annotations
import argparse
from datetime import date
from pathlib import Path

from core.config import load_config
from core.fetcher import DmwClient
from core.transform import to_dataframe
from core.writer import save
from core.log import setup_logging

def main():
    p = argparse.ArgumentParser(description="DMW exporter (headless)")
    p.add_argument("--month", help="YYYY-MM for filename stamp (optional)")
    p.add_argument("--prev-month", action="store_true", help="Use previous month instead of current")
    p.add_argument("--max-pages", type=int, default=None, help="Limit pages (testing)")
    args = p.parse_args()

    # compute previous month if requested
    if args.prev_month:
        y, m = date.today().year, date.today().month
        if m == 1: y, m = y - 1, 12
        args.month = f"{y}-{m:02d}"

    # logs go next to exe or CWD; fine either way
    setup_logging(Path.cwd())
    cfg = load_config(Path.cwd())  # path arg ignored now; loader is robust

    print(f"[cli] month={args.month or 'current'} max_pages={args.max_pages} api_key_set={bool(cfg.get('api_key'))}")

    client = DmwClient(api_base=cfg["api_base"], api_key=cfg.get("api_key", ""))
    rows = client.fetch_all(cfg["jobsite"], max_pages=args.max_pages)
    df = to_dataframe(rows)
    if not df.empty:
        save(df, Path(cfg["output_dir"]), cfg["jobsite"], args.month, cfg.get("formats", ["csv"]))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
