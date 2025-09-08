from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Dict, List

DEFAULT_CONFIG: Dict[str, Any] = {
    "api_base": "https://master-api.dmw.gov.ph/api/v1/public/approved-job-orders/filter",
    "api_key": "",
    "jobsite": "Czech republic",
    "output_dir": "./output",
    "formats": ["csv"],               # or ["csv","xlsx"]
    "timezone": "Europe/Prague"
}

def config_path(base: Path) -> Path:
    return (base / "config.json")

def load_config(base: Path) -> Dict[str, Any]:
    path = config_path(base)
    cfg = DEFAULT_CONFIG.copy()
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    # Optional: allow override via env var if needed in CI or testing
    if os.getenv("DMW_API_BASE"):
        cfg["api_base"] = os.environ["DMW_API_BASE"]
    return cfg

def save_config(base: Path, cfg: Dict[str, Any]) -> None:
    path = config_path(base)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def normalize_formats(vals: List[str]) -> List[str]:
    uniq = []
    for v in vals:
        v = v.lower().strip()
        if v in ("csv","xlsx") and v not in uniq:
            uniq.append(v)
    return uniq or ["csv"]
