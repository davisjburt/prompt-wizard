"""Start-with-Windows toggle: a shortcut to run_hidden.vbs in the Startup folder."""
import os
import subprocess
from pathlib import Path

from config import ROOT

LINK = (
    Path(os.environ["APPDATA"])
    / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    / "Prompt Wizard.lnk"
)


def is_enabled() -> bool:
    return LINK.exists()


def set_enabled(on: bool):
    if on:
        vbs = ROOT / "run_hidden.vbs"
        ps = (
            f"$s = (New-Object -ComObject WScript.Shell).CreateShortcut('{LINK}'); "
            f"$s.TargetPath = 'wscript.exe'; "
            f"$s.Arguments = '\"{vbs}\"'; "
            f"$s.WorkingDirectory = '{ROOT}'; "
            f"$s.Save()"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            creationflags=subprocess.CREATE_NO_WINDOW,
            check=True,
        )
    else:
        LINK.unlink(missing_ok=True)
