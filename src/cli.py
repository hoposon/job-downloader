from pathlib import Path
from core.config import load_config
from core.fetcher import DmwClient
from core.transform import to_dataframe
from core.writer import save
from core.log import setup_logging
import argparse

def main():
    parser = argparse.ArgumentParser(description="DMW exporter (headless)")
    parser.add_argument("--base", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--month", help="YYYY-MM for filename stamp (optional)")
    parser.add_argument("--max-pages", type=int, default=None)
    args = parser.parse_args()

    base = Path(args.base)
    setup_logging(base)
    cfg = load_config(base)

    client = DmwClient(api_base=cfg["api_base"])
    rows = client.fetch_all(cfg["jobsite"], max_pages=args.max_pages)
    df = to_dataframe(rows)
    if not df.empty:
        save(df, Path(cfg["output_dir"]), cfg["jobsite"], args.month, cfg.get("formats", ["csv"]))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
