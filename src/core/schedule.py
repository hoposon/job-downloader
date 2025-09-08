from __future__ import annotations
import platform
import subprocess
from typing import Optional, Tuple

TASK_NAME = "DMW Monthly Export"

def is_windows() -> bool:
    return platform.system().lower().startswith("win")

def _run(cmd: list[str]) -> Tuple[int, str, str]:
    c = subprocess.run(cmd, capture_output=True, text=True)
    return c.returncode, c.stdout.strip(), c.stderr.strip()

def exists() -> bool:
    if not is_windows(): return False
    code, *_ = _run(["schtasks", "/Query", "/TN", TASK_NAME])
    return code == 0

def create_or_update(executable: str, hour: int, minute: int, use_last_day: bool,
                     day_of_month: Optional[int], extra_args: str = "") -> Tuple[int, str, str]:
    """
    Schedules: monthly at HH:MM, on LASTDAY or concrete day.
    """
    if not is_windows():
        return (1, "", "Not on Windows")

    schedule = ["/SC", "MONTHLY", "/ST", f"{hour:02d}:{minute:02d}"]
    if use_last_day:
        schedule += ["/D", "LASTDAY"]
    else:
        schedule += ["/D", str(day_of_month or 1)]

    tr = f'"{executable}" {extra_args}'.strip()
    create = ["schtasks", "/Create", "/TN", TASK_NAME, "/TR", tr, "/RL", "HIGHEST", "/F"] + schedule

    if exists():
        _run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])
    return _run(create)

def delete() -> Tuple[int, str, str]:
    if not is_windows(): return (0, "Not on Windows", "")
    if exists():
        return _run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])
    return (0, "Task not present", "")
