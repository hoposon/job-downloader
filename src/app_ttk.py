from __future__ import annotations
import os, sys, platform, subprocess, datetime as dt
from pathlib import Path
from typing import Any, Dict

import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

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

def cli_executable_path(base: Path) -> str:
    """
    Return the command Task Scheduler should run.
    - When frozen: dmw-export.exe next to the GUI exe.
    - From source: python cli.py
    """
    if getattr(sys, "frozen", False):
        cli_path = (base / "dmw-export.exe")
        return f'"{cli_path}"'
    else:
        cli_py = (base / "src" / "cli.py").resolve()
        return f'"{sys.executable}" "{cli_py}"'

def open_folder(p: Path):
    p.mkdir(parents=True, exist_ok=True)
    if is_windows():
        os.startfile(p)  # type: ignore
    elif platform.system() == "Darwin":
        subprocess.run(["open", p])
    else:
        subprocess.run(["xdg-open", p])

def run_now(cfg: Dict[str, Any], month_value: str | None, log_cb, max_pages: int | None = None):
    client = DmwClient(api_base=cfg["api_base"], api_key=cfg.get("api_key", ""))
    log_cb("Fetching meta & page 1 …")
    rows = client.fetch_all(cfg["jobsite"], progress=log_cb, max_pages=max_pages)
    df = to_dataframe(rows)
    if df.empty:
        log_cb("No data returned. Nothing to write.")
        return []
    written = save(
        df,
        Path(cfg["output_dir"]),
        cfg["jobsite"],
        month_value,
        normalize_formats(cfg.get("formats", ["csv"]))
    )
    for f in written:
        log_cb(f"Wrote: {f.resolve()}")
    return written

def main():
    base = base_dir()
    setup_logging(base)
    cfg = load_config(base)

    app = tb.Window(title=APP_TITLE, themename="cosmo")
    app.geometry("820x560")

    # ---- widgets helpers ----
    def log(msg: str):
        logbox.configure(state="normal")
        logbox.insert("end", msg + "\n")
        logbox.see("end")
        logbox.configure(state="disabled")

    # ---- Tabs ----
    nb = tb.Notebook(app)
    tab_general = tb.Frame(nb, padding=10)
    tab_schedule = tb.Frame(nb, padding=10)
    nb.add(tab_general, text="General")
    nb.add(tab_schedule, text="Schedule")
    nb.pack(fill=BOTH, expand=YES, padx=10, pady=10)

    # -------- General tab --------
    # API base
    tb.Label(tab_general, text="API base:").grid(row=0, column=0, sticky=W, pady=5)
    api_var = tb.StringVar(value=cfg.get("api_base", ""))
    api_entry = tb.Entry(tab_general, textvariable=api_var, width=70)
    api_entry.grid(row=0, column=1, columnspan=3, sticky=EW, pady=5)

    # API key
    tb.Label(tab_general, text="API key:").grid(row=1, column=0, sticky=W, pady=5)
    api_key_var = tb.StringVar(value=cfg.get("api_key", ""))
    api_key_entry = tb.Entry(tab_general, textvariable=api_key_var, width=70)
    api_key_entry.grid(row=1, column=1, columnspan=3, sticky=EW, pady=5)

    # Jobsite
    tb.Label(tab_general, text="Jobsite:").grid(row=2, column=0, sticky=W, pady=5)
    jobsite_var = tb.StringVar(value=cfg.get("jobsite", ""))
    jobsite_entry = tb.Entry(tab_general, textvariable=jobsite_var, width=40)
    jobsite_entry.grid(row=2, column=1, sticky=W, pady=5)

    # Output folder
    tb.Label(tab_general, text="Output folder:").grid(row=3, column=0, sticky=W, pady=5)
    outdir_var = tb.StringVar(value=cfg.get("output_dir", ""))
    outdir_entry = tb.Entry(tab_general, textvariable=outdir_var, width=50)
    outdir_entry.grid(row=3, column=1, sticky=EW, pady=5)
    def pick_folder():
        initial = outdir_var.get() or str(base)
        folder = filedialog.askdirectory(initialdir=initial)
        if folder:
            outdir_var.set(folder)
    tb.Button(tab_general, text="Browse…", command=pick_folder, bootstyle=SECONDARY).grid(row=3, column=2, sticky=W, padx=8)

    # Formats
    tb.Label(tab_general, text="Formats:").grid(row=4, column=0, sticky=W, pady=5)
    csv_var = tb.BooleanVar(value=("csv" in cfg.get("formats", ["csv"])))
    xlsx_var = tb.BooleanVar(value=("xlsx" in cfg.get("formats", [])))
    tb.Checkbutton(tab_general, text="CSV", variable=csv_var).grid(row=4, column=1, sticky=W)
    tb.Checkbutton(tab_general, text="XLSX", variable=xlsx_var).grid(row=4, column=2, sticky=W)

    # Month stamp
    tb.Label(tab_general, text="Month stamp (YYYY-MM):").grid(row=5, column=0, sticky=W, pady=5)
    month_var = tb.StringVar(value="")
    tb.Entry(tab_general, textvariable=month_var, width=12).grid(row=5, column=1, sticky=W)

    # --- Test-only: Limit pages ---
    limit_pages_var = tb.BooleanVar(value=False)
    tb.Checkbutton(tab_general, text="Limit pages (testing)", variable=limit_pages_var)\
    .grid(row=6, column=0, sticky=W, pady=(8, 0))

    tb.Label(tab_general, text="Max pages:").grid(row=6, column=1, sticky=E, pady=(8, 0))
    max_pages_var = tb.StringVar(value="3")
    max_pages_widget = tb.Spinbox(
        tab_general, from_=1, to=999, width=6, textvariable=max_pages_var, state=DISABLED
    )
    max_pages_widget.grid(row=6, column=2, sticky=W, pady=(8, 0))

    def on_limit_pages_toggle(*_):
        max_pages_widget.configure(state=(NORMAL if limit_pages_var.get() else DISABLED))

    limit_pages_var.trace_add("write", on_limit_pages_toggle)

    # Buttons
    def on_save_config():
        formats = []
        if csv_var.get(): formats.append("csv")
        if xlsx_var.get(): formats.append("xlsx")
        new_cfg = {
            "api_base": api_var.get().strip(),
            "api_key": api_key_var.get().strip(),
            "jobsite": jobsite_var.get().strip(),
            "output_dir": outdir_var.get().strip(),
            "formats": normalize_formats(formats),
        }
        save_config(base, new_cfg)
        log("Config saved.")

    def on_run_now():
        # quick validation for month
        m = month_var.get().strip() or None
        if m:
            try:
                dt.datetime.strptime(m, "%Y-%m")
            except ValueError:
                messagebox.showerror("Invalid month", "Use YYYY-MM format (e.g. 2025-09).")
                return

        # reload config (user could have edited paths)
        current = load_config(base)
        current["api_base"] = api_var.get().strip()
        current["api_key"] = api_key_var.get().strip()
        current["jobsite"] = jobsite_var.get().strip()
        current["output_dir"] = outdir_var.get().strip()
        current["formats"] = normalize_formats(
            ["csv"] * int(csv_var.get()) + ["xlsx"] * int(xlsx_var.get())
        )

        # read test-only limit-pages controls
        max_pages = None
        if limit_pages_var.get():
            try:
                mp = int(max_pages_var.get())
                if mp < 1 or mp > 999:
                    raise ValueError
                max_pages = mp
            except ValueError:
                messagebox.showerror("Invalid value", "Max pages must be an integer between 1 and 999.")
                return

        log(f"Starting run: jobsite={current['jobsite']} → {current['output_dir']} "
            f"(formats={current['formats']}) month={m or 'current'} "
            f"{'(limit: ' + str(max_pages) + ' pages)' if max_pages else ''}")

        try:
            run_now(current, m, log, max_pages=max_pages)
        except Exception as e:
            messagebox.showerror("Run failed", str(e))
            log(f"ERROR: {e}")

    def on_open_output():
        outdir = Path(outdir_var.get() or load_config(base)["output_dir"])
        open_folder(outdir)

    btn_row = tb.Frame(tab_general)
    btn_row.grid(row=7, column=0, columnspan=4, pady=10, sticky=W)
    tb.Button(btn_row, text="Save Config", command=on_save_config, bootstyle=PRIMARY).pack(side=LEFT, padx=4)
    tb.Button(btn_row, text="Run Now", command=on_run_now, bootstyle=SUCCESS).pack(side=LEFT, padx=4)
    tb.Button(btn_row, text="Open Output Folder", command=on_open_output, bootstyle=SECONDARY).pack(side=LEFT, padx=4)

    # column stretch
    tab_general.columnconfigure(1, weight=1)

    # -------- Schedule tab (simple: Day X at HH:MM) --------
    sched_note = "Windows Task Scheduler (run on a specific day and time)"
    if not is_windows():
        sched_note += " — disabled on this OS"

    tb.Label(tab_schedule, text=sched_note).grid(row=0, column=0, columnspan=4, sticky=W, pady=(0,8))

    tb.Label(tab_schedule, text="Run time:").grid(row=1, column=0, sticky=W)
    hour_var = tb.StringVar(value="23")
    min_var  = tb.StringVar(value="55")
    hour_widget = tb.Spinbox(tab_schedule, values=[f"{i:02d}" for i in range(24)], textvariable=hour_var, width=5)
    hour_widget.grid(row=1, column=1, sticky=W)
    tb.Label(tab_schedule, text=":").grid(row=1, column=2, sticky=W)
    min_widget  = tb.Spinbox(tab_schedule, values=[f"{i:02d}" for i in range(60)], textvariable=min_var,  width=5)
    min_widget.grid(row=1, column=3, sticky=W)

    tb.Label(tab_schedule, text="Day of month (1–28):").grid(row=2, column=0, sticky=W, pady=6)
    dom_var = tb.StringVar(value="28")
    dom_widget = tb.Spinbox(tab_schedule, values=[str(i) for i in range(1,29)], textvariable=dom_var, width=5)  # 1–28 is safest across all months
    dom_widget.grid(row=2, column=1, sticky=W, pady=6)

    taskstate_var = tb.StringVar(value="")
    tb.Label(tab_schedule, textvariable=taskstate_var).grid(row=3, column=0, columnspan=4, sticky=W, pady=(0,6))

    def on_create_update_schedule():
        if not is_windows():
            return
        try:
            hour = int(hour_var.get()); minute = int(min_var.get()); dom = int(dom_var.get())
            if not (0 <= hour <= 23 and 0 <= minute <= 59): raise ValueError("Invalid time")
            if not (1 <= dom <= 28): raise ValueError("Day must be 1–28")
        except Exception as e:
            messagebox.showerror("Invalid input", str(e))
            return

        exe_cmd = cli_executable_path(base)
        # No "last day" mapping, no extra args — exactly what user set
        code, out, err = create_or_update(exe_cmd, hour, minute, False, dom, "")
        taskstate_var.set("OK" if code == 0 else f"ERROR {code}")
        if out: log(out)
        if err: log(err)

    def on_delete_schedule():
        if not is_windows(): return
        code, out, err = delete_task()
        taskstate_var.set("Deleted" if code == 0 else f"ERROR {code}")
        if out: log(out)
        if err: log(err)

    def on_run_task_now():
        if not is_windows(): return
        try:
            cp = subprocess.run(["schtasks", "/Run", "/TN", "DMW Monthly Export"], capture_output=True, text=True)
            if cp.returncode == 0:
                taskstate_var.set("Triggered")
                log(cp.stdout or "Task triggered.")
            else:
                taskstate_var.set(f"ERROR {cp.returncode}")
                log(cp.stderr or cp.stdout or "Failed to run task.")
        except Exception as e:
            taskstate_var.set("ERROR")
            log(str(e))

    tb.Button(tab_schedule, text="Create/Update Schedule",
            command=on_create_update_schedule,
            bootstyle=PRIMARY, state=(NORMAL if is_windows() else DISABLED)).grid(row=4, column=0, pady=8, sticky=W)

    tb.Button(tab_schedule, text="Run Scheduled Task Now",
            command=on_run_task_now,
            bootstyle=SECONDARY, state=(NORMAL if is_windows() else DISABLED)).grid(row=4, column=1, pady=8, sticky=W)

    tb.Button(tab_schedule, text="Delete Schedule",
            command=on_delete_schedule,
            bootstyle=DANGER, state=(NORMAL if is_windows() else DISABLED)).grid(row=4, column=2, pady=8, sticky=W)


    # -------- Log area (shared) --------
    logbox = ScrolledText(app, height=12, wrap="word")
    logbox.pack(fill=BOTH, expand=YES, padx=10, pady=(0,10))
    logbox.configure(state="disabled")

    app.mainloop()

if __name__ == "__main__":
    main()
