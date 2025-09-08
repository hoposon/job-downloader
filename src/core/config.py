# core/config.py
from __future__ import annotations
import json, os, sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

DEFAULT_CONFIG: Dict[str, Any] = {
    "api_base": "https://master-api.dmw.gov.ph/api/v1/public/approved-job-orders/filter",
    "api_key": "",
    "jobsite": "Czech republic",
    "output_dir": "./output",
    "formats": ["csv"],
    "timezone": "Europe/Prague",
}

def _exe_dir() -> Path:
    # Where the running binary/script lives
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # this file is src/core/config.py → project root is parents[2]
    return Path(__file__).resolve().parents[2]

def _meipass_dir() -> Path | None:
    # PyInstaller one-file extraction dir
    mp = getattr(sys, "_MEIPASS", None)
    return Path(mp) if mp else None

def find_config_paths() -> Tuple[Path, Path | None]:
    """Returns (external_path, bundled_path or None)"""
    ext = _exe_dir() / "config.json"
    bun = (_meipass_dir() / "config.json") if _meipass_dir() else None
    return ext, bun

def load_config(_) -> Dict[str, Any]:
    # `_` kept for backward compat; ignored now
    cfg = DEFAULT_CONFIG.copy()
    external, bundled = find_config_paths()

    if external.exists():
        with external.open("r", encoding="utf-8") as f:
            cfg.update(json.load(f))
        source = f"external:{external}"
    elif bundled and bundled.exists():
        with bundled.open("r", encoding="utf-8") as f:
            cfg.update(json.load(f))
        source = f"bundled:{bundled}"
    else:
        source = "defaults"

    # Allow env override for CI/secrets
    if os.getenv("DMW_API_KEY"):
        cfg["api_key"] = os.environ["DMW_API_KEY"]

    # Make output_dir absolute; if relative, anchor to exe dir
    out = Path(cfg.get("output_dir", "./output"))
    if not out.is_absolute():
        out = (_exe_dir() / out).resolve()
        cfg["output_dir"] = str(out)

    # Optional: quick trace to logs/stdout
    print(f"[config] loaded from {source}; output_dir={cfg['output_dir']}")
    return cfg

def save_config(_, cfg: Dict[str, Any]) -> None:
    external, _ = find_config_paths()
    external.parent.mkdir(parents=True, exist_ok=True)
    with external.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def normalize_formats(vals: List[str]) -> List[str]:
    uniq: List[str] = []
    for v in vals:
        v = v.lower().strip()
        if v in ("csv", "xlsx") and v not in uniq:
            uniq.append(v)
    return uniq or ["csv"]
