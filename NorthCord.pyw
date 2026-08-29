# NorthCord.pyw - No console window
import subprocess
import os
import sys
from pathlib import Path

def launch():
    root = Path(__file__).parent
    python = root / "venv" / "Scripts" / "python.exe"
    
    if not python.exists():
        # Check standard launcher venv folder name "venv"
        python = root / "venv" / "Scripts" / "python.exe"
        if not python.exists():
            # Fallback to system python
            python = sys.executable
    
    # Run with hidden console
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    
    subprocess.Popen(
        [str(python), "-m", "northcord"],
        cwd=root,
        startupinfo=startupinfo,
        creationflags=subprocess.CREATE_NO_WINDOW
    )

if __name__ == "__main__":
    launch()
