from __future__ import annotations
import os, sys, platform, subprocess
from pathlib import Path
import datetime as dt
from typing import Any, Dict, List

import PySimpleGUI as sg
from core.config import load_config, save_config, normalize_formats
from core.fetcher import DmwClient
from core.transform import to_dataframe
from core.writer import save
from core.schedule import is_windows, create_or_update, delete as delete_task
from core.log import setup_logging

APP_TITLE = "DMW Job Orders Exporter"

def base_dir() -> Path:
    # project root if running from source; exe directory when frozen
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]

def open_folder(p: Path):
    p.mkdir(parents=True, exist_ok=True)
    if is_windows():
        os.startfile(p)  # type: ignore
    elif platform.system() == "Darwin":
        subprocess.run(["open", p])
    else:
        subprocess.run(["xdg-open", p])

def run_now(cfg: Dict[str, Any], month_value: str | None, log_cb):
    client = DmwClient(api_base=cfg["api_base"])
    log_cb("Fetching meta & page 1 …")
    rows = client.fetch_all(cfg["jobsite"], progress=log_cb)
    df = to_dataframe(rows)
    if df.empty:
        log_cb("No data returned. Nothing to write.")
        return []
    written = save(df, Path(cfg["output_dir"]), cfg["jobsite"], month_value, normalize_formats(cfg.get("formats",["csv"])))
    for f in written:
        log_cb(f"Wrote: {f.resolve()}")
    return written

def main():
    base = base_dir()
    setup_logging(base)
    cfg = load_config(base)

    sg.theme("SystemDefault")
    general_tab = [
        [sg.Text("API base:"), sg.Input(cfg.get("api_base",""), key="-API-", size=(60,1))],
        [sg.Text("Jobsite:"), sg.Input(cfg.get("jobsite",""), key="-JOBSITE-", size=(40,1))],
        [sg.Text("Output folder:"), sg.Input(cfg.get("output_dir",""), key="-OUTDIR-", size=(40,1)), sg.FolderBrowse()],
        [sg.Text("Formats:"), sg.Checkbox("CSV", key="-CSV-", default=("csv" in cfg.get("formats",["csv"]))),
                              sg.Checkbox("XLSX", key="-XLSX-", default=("xlsx" in cfg.get("formats",[])))],
        [sg.Text("Month stamp (YYYY-MM) for filename (optional):"),
         sg.Input("", key="-MONTH-", size=(10,1)), sg.Text("(leave empty for current month)")],
        [sg.Button("Save Config"), sg.Button("Run Now"), sg.Button("Open Output Folder")]
    ]

    sched_disabled = not is_windows()
    schedule_tab = [
        [sg.Text("Windows Task Scheduler controls" + (" — disabled on this OS" if sched_disabled else ""))],
        [sg.Text("Run time:"), sg.Spin([f"{i:02d}" for i in range(24)], "23", key="-H-"),
         sg.Text(":"), sg.Spin([f"{i:02d}" for i in range(60)], "55", key="-M-")],
        [sg.Checkbox("Run on LAST day of month", True, key="-LAST-"),
         sg.Text("…or day:"), sg.Spin([str(i) for i in range(1,28)], "1", key="-DOM-")],
        [sg.Text("Extra args (optional):"), sg.Input("--month %DATE:~0,4%-%DATE:~5,2%", key="-ARGS-", size=(36,1))],
        [sg.Button("Create/Update Schedule", disabled=sched_disabled),
         sg.Button("Delete Schedule", disabled=sched_disabled),
         sg.Text("", size=(60,1), key="-TASKSTATE-")]
    ]

    layout = [[sg.TabGroup([[sg.Tab("General", general_tab), sg.Tab("Schedule", schedule_tab)]])],
              [sg.Multiline(size=(100,16), key="-LOG-", autoscroll=True, disabled=True)]]

    win = sg.Window(APP_TITLE, layout, finalize=True)
    logbox = win["-LOG-"]
    def log(msg: str):
        logbox.update(value=(logbox.get() + msg + "\n"))

    while True:
        ev, v = win.read()
        if ev in (sg.WINDOW_CLOSED, None):
            break

        if ev == "Save Config":
            new_cfg = {
                "api_base": v["-API-"].strip(),
                "jobsite": v["-JOBSITE-"].strip(),
                "output_dir": v["-OUTDIR-"].strip(),
                "formats": normalize_formats([fmt for fmt, flag in (("csv", v["-CSV-"]),("xlsx", v["-XLSX-"])) if flag])
            }
            save_config(base, new_cfg)
            log("Config saved.")

        elif ev == "Run Now":
            # Reload config (in case user edited paths)
            cfg = load_config(base)
            month = v["-MONTH-"].strip() or None
            # quick validation
            if month:
                try:
                    dt.datetime.strptime(month, "%Y-%m")
                except ValueError:
                    log("Invalid month format. Use YYYY-MM.")
                    continue
            log(f"Starting run: jobsite={cfg['jobsite']} → {cfg['output_dir']} (formats={cfg.get('formats')}) month={month or 'current'}")
            try:
                run_now(cfg, month, log)
            except Exception as e:
                log(f"ERROR: {e}")

        elif ev == "Open Output Folder":
            outdir = Path(load_config(base)["output_dir"])
            open_folder(outdir)

        elif ev == "Create/Update Schedule":
            if not is_windows(): continue
            hour = int(v["-H-"]); minute = int(v["-M-"])
            last = bool(v["-LAST-"]); dom = int(v["-DOM-"])
            args = v["-ARGS-"].strip()
            # Resolve executable path (packaged .exe when frozen, otherwise current Python with cli.py)
            if getattr(sys, "frozen", False):
                exe = sys.executable + ' --headless-run'  # our PyInstaller exe supports this flag via Inno/Task
            else:
                exe = f'{sys.executable} "{(base / "src" / "cli.py").resolve()}"'
            code, out, err = create_or_update(exe, hour, minute, last, dom, args)
            win["-TASKSTATE-"].update("OK" if code == 0 else f"ERROR {code}")
            if out: log(out)
            if err: log(err)

        elif ev == "Delete Schedule":
            if not is_windows(): continue
            code, out, err = delete_task()
            win["-TASKSTATE-"].update("Deleted" if code == 0 else f"ERROR {code}")
            if out: log(out)
            if err: log(err)

    win.close()

if __name__ == "__main__":
    main()
