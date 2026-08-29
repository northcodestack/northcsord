"""
Create NorthCord desktop shortcut
Run once to create a double-clickable shortcut
"""

import os
import sys
from pathlib import Path

def create_windows_shortcut():
    """Create Windows shortcut using PowerShell"""
    try:
        import subprocess
        
        desktop = Path(os.environ["USERPROFILE"]) / "Desktop"
        target = Path(__file__).parent / "launch.bat"
        shortcut = desktop / "NorthCord.lnk"
        
        powershell = f'''
$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut("{shortcut}")
$Shortcut.TargetPath = "{target}"
$Shortcut.WorkingDirectory = "{target.parent}"
$Shortcut.IconLocation = "%SystemRoot%\\System32\\SHELL32.dll, 14"
$Shortcut.Save()
'''
        subprocess.run(["powershell", "-Command", powershell], check=True)
        print(f"✅ Shortcut created on Desktop: {shortcut}")
    except Exception as e:
        print(f"❌ Failed to create shortcut: {e}")

if __name__ == "__main__":
    create_windows_shortcut()
