"""Central coordinator — wires config, theme, scheduler, and tray together."""

import logging
import sys
from pathlib import Path

from theme_switcher.config import Config, first_run_wizard, load, save
from theme_switcher.scheduler import Scheduler
from theme_switcher.theme import THEME_DARK, THEME_LIGHT, get_current_theme, set_theme, set_wallpaper
from theme_switcher.tray import TrayManager

logger = logging.getLogger(__name__)

_config: Config = None
_tray: TrayManager = None
_scheduler: Scheduler = None


def run() -> None:
    global _config

    _config = load()
    if _config is None:
        _config = first_run_wizard()
        if _config is None:
            print("Setup cancelled. Exiting.")
            sys.exit(0)

    _setup_logging()
    logger.info("Theme Switcher v1.0.0 starting")

    _apply_initial_theme()
    _start_scheduler()
    _start_tray()


def _setup_logging() -> None:
    import os
    from logging.handlers import TimedRotatingFileHandler

    log_dir = Path(os.environ["LOCALAPPDATA"]) / "ThemeSwitcher" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()

    handler = TimedRotatingFileHandler(
        log_dir / "theme-switcher.log",
        when="midnight",
        backupCount=30,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    root_logger.addHandler(handler)


def get_config() -> Config:
    return _config


def get_status_text() -> str:
    config = get_config()
    current = get_current_theme()
    mode = "Auto" if config.auto_switch_enabled and not config.manual_override else "Manual"
    override = " (override)" if config.manual_override else ""
    return f"{mode}{override}: {current.capitalize()} theme"


def _do_switch(theme: str) -> None:
    set_theme(theme)
    if _config.enable_wallpaper_switch:
        wp_dir = _config.light_wallpaper_dir if theme == THEME_LIGHT else _config.dark_wallpaper_dir
        if wp_dir:
            set_wallpaper(wp_dir)


def _apply_initial_theme() -> None:
    if not _config.auto_switch_enabled:
        return

    from theme_switcher.solar import get_theme_for_now
    target = get_theme_for_now(_config)
    if target is None:
        return

    current = get_current_theme()
    if current != target:
        logger.info("Initial sync: switching to %s", target)
        _do_switch(target)


def _start_scheduler() -> None:
    global _scheduler
    _scheduler = Scheduler(on_switch=_on_scheduled_switch, get_config=get_config)
    _scheduler.start()


def _start_tray() -> None:
    global _tray
    _tray = TrayManager(
        on_action=_on_tray_action,
        get_config=get_config,
        get_status_text=get_status_text,
    )
    _tray.start()


def _on_scheduled_switch(theme: str) -> None:
    _do_switch(theme)
    if _tray:
        _tray.update_icon()
        _tray.update_menu()


def _on_tray_action(action: str) -> None:
    global _config

    if action == "switch_dark":
        _do_switch(THEME_DARK)
        _config.manual_override = True
        _config.forced_theme = THEME_DARK
        _config.manual_override_until = None
        save(_config)
        if _tray:
            _tray.update_icon()
            _tray.update_menu()

    elif action == "switch_light":
        _do_switch(THEME_LIGHT)
        _config.manual_override = True
        _config.forced_theme = THEME_LIGHT
        _config.manual_override_until = None
        save(_config)
        if _tray:
            _tray.update_icon()
            _tray.update_menu()

    elif action == "toggle_auto":
        _config.auto_switch_enabled = not _config.auto_switch_enabled
        if _config.auto_switch_enabled:
            _config.manual_override = False
            _config.manual_override_until = None
            _config.forced_theme = ""
            save(_config)
            _apply_initial_theme()
            if _scheduler:
                _scheduler.recalculate()
        else:
            save(_config)
        if _tray:
            _tray.update_icon()
            _tray.update_menu()

    elif action == "cancel_override":
        _config.manual_override = False
        _config.manual_override_until = None
        _config.forced_theme = ""
        save(_config)
        _apply_initial_theme()
        if _scheduler:
            _scheduler.recalculate()
        if _tray:
            _tray.update_icon()
            _tray.update_menu()

    elif action == "override_until_next":
        from datetime import datetime
        from theme_switcher.solar import calculate_next_transition

        current = get_current_theme()
        opposite = THEME_DARK if current == THEME_LIGHT else THEME_LIGHT
        _do_switch(opposite)

        transition = calculate_next_transition(_config)
        if transition:
            _, until = transition
            _config.manual_override = True
            _config.forced_theme = opposite
            _config.manual_override_until = until.isoformat()
        else:
            _config.manual_override = True
            _config.forced_theme = opposite
            _config.manual_override_until = None
        save(_config)
        if _tray:
            _tray.update_icon()
            _tray.update_menu()

    elif action == "redetect_location":
        from theme_switcher.config import auto_detect_location, save as cfg_save
        loc = auto_detect_location()
        if loc:
            _config.latitude = loc["latitude"]
            _config.longitude = loc["longitude"]
            _config.timezone = loc["timezone"]
            _config.city_name = loc["city_name"]
            cfg_save(_config)
            if _scheduler:
                _scheduler.recalculate()
            _apply_initial_theme()
            logger.info("Location re-detected: %s (%s, %s)", loc["city_name"], loc["latitude"], loc["longitude"])
        else:
            logger.warning("Failed to auto-detect location")
        if _tray:
            _tray.update_menu()

    elif action == "configure":
        import os
        from theme_switcher.config import _config_path
        os.startfile(_config_path())

    elif action == "exit":
        if _scheduler:
            _scheduler.stop()
        if _tray:
            _tray.stop()
        sys.exit(0)
