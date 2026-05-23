"""One-click installer for Windows 11 Auto Theme Switcher.

Installs dependencies, creates startup shortcut.
Double-click this file or run: python install.py
"""

import os
import sys
import subprocess
from pathlib import Path


def main():
    print("\n" + "=" * 50)
    print("  Windows 11 Auto Theme Switcher - Installer")
    print("=" * 50 + "\n")

    project_dir = Path(__file__).parent.resolve()

    # Step 1: Install dependencies
    print("[1/3] Installing dependencies...")
    req_path = project_dir / "requirements.txt"
    if req_path.exists():
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"Warning: pip install had errors:\n{result.stderr}")
        else:
            print("  Dependencies installed.")
    else:
        print("  requirements.txt not found, skipping.")

    # Step 2: Create startup shortcut
    print("[2/3] Creating startup shortcut...")
    startup_dir = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    startup_dir.mkdir(parents=True, exist_ok=True)

    vbs_path = startup_dir / "ThemeSwitcher.vbs"

    main_script = project_dir / "main.py"

    # Find py.exe launcher - use full path because user PATH may not be
    # available when Startup folder items execute at logon
    py_launcher = Path(sys.exec_prefix).parent / "Launcher" / "py.exe"
    if not py_launcher.exists():
        py_launcher = "py"

    vbs_content = f'CreateObject("WScript.Shell").Run "{py_launcher} -3.13 ""{main_script}""", 0, False\n'

    vbs_path.write_text(vbs_content, encoding="utf-8")
    print(f"  Startup shortcut created: {vbs_path}")

    # Step 3: Run first-time setup and launch
    print("[3/3] Starting Theme Switcher...")
    subprocess.Popen(
        [python_exe, str(main_script)],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    print("  Theme Switcher is now running!")
    print("\n" + "=" * 50)
    print("  Installation complete!")
    print("  Look for the tray icon in your taskbar.")
    print("  Right-click the icon to access settings.")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
