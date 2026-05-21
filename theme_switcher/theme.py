"""Windows theme and wallpaper switching via registry and system API."""

import ctypes
import logging
import os
import random
import winreg
from pathlib import Path

logger = logging.getLogger(__name__)

REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
KEY_APPS = "AppsUseLightTheme"
KEY_SYSTEM = "SystemUsesLightTheme"

THEME_LIGHT = "light"
THEME_DARK = "dark"

SPI_SETDESKWALLPAPER = 0x0014
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDCHANGE = 0x02



def get_current_theme() -> str:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        apps_value, _ = winreg.QueryValueEx(key, KEY_APPS)
        winreg.CloseKey(key)
        return THEME_LIGHT if apps_value == 1 else THEME_DARK
    except OSError as e:
        logger.error("Failed to read theme registry: %s", e)
        return THEME_DARK


def set_theme(theme: str) -> bool:
    value = 1 if theme == THEME_LIGHT else 0
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, KEY_APPS, 0, winreg.REG_DWORD, value)
        winreg.SetValueEx(key, KEY_SYSTEM, 0, winreg.REG_DWORD, value)
        winreg.CloseKey(key)

        _broadcast_setting_change()
        logger.info("Theme switched to %s", theme)
        return True
    except OSError as e:
        logger.error("Failed to set theme to %s: %s", theme, e)
        return False


def _broadcast_setting_change() -> None:
    HWND_BROADCAST = 0xFFFF
    WM_SETTINGCHANGE = 0x001A
    ctypes.windll.user32.SendNotifyMessageW(
        HWND_BROADCAST,
        WM_SETTINGCHANGE,
        0,
        "ImmersiveColorSet",
    )


def set_wallpaper(wallpaper_dir: str) -> bool:
    """Pick a random image from the directory and set it as desktop wallpaper."""
    dir_path = Path(wallpaper_dir)
    if not dir_path.is_dir():
        logger.error("Wallpaper directory not found: %s", wallpaper_dir)
        return False

    images = _list_images(dir_path)
    if not images:
        logger.warning("No images found in %s", wallpaper_dir)
        return False

    chosen = random.choice(images)
    return _set_wallpaper_file(str(chosen))


def _list_images(directory: Path) -> list:
    extensions = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"}
    result = []
    try:
        for entry in directory.iterdir():
            if entry.is_file() and entry.suffix.lower() in extensions:
                result.append(entry)
    except OSError as e:
        logger.error("Error listing wallpaper directory: %s", e)
    return result


def _set_wallpaper_file(image_path: str) -> bool:
    try:
        result = ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER,
            0,
            image_path,
            SPIF_UPDATEINIFILE | SPIF_SENDCHANGE,
        )
        if result:
            logger.info("Wallpaper set to %s", image_path)
            return True
        else:
            logger.error("SystemParametersInfoW failed for %s", image_path)
            return False
    except Exception as e:
        logger.error("Failed to set wallpaper: %s", e)
        return False
