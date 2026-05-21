"""Entry point for Windows 11 Auto Theme Switcher."""

import ctypes
import sys

from theme_switcher.worker import run

MUTEX_NAME = "ThemeSwitcher_Win11_SingleInstance"


def _check_single_instance() -> bool:
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        kernel32.CloseHandle(mutex)
        return False
    return True


if __name__ == "__main__":
    if not _check_single_instance():
        print("Theme Switcher is already running.")
        sys.exit(0)

    run()
