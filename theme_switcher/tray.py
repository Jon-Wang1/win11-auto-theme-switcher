"""System tray icon and context menu via pystray."""

import logging
import threading
from typing import Callable, Optional

from PIL import Image

from theme_switcher import icons
from theme_switcher.theme import THEME_DARK, THEME_LIGHT

logger = logging.getLogger(__name__)

ActionCallback = Callable[[str], None]


class TrayManager:
    def __init__(
        self,
        on_action: ActionCallback,
        get_config,
        get_status_text: Callable[[], str],
    ):
        self._on_action = on_action
        self._get_config = get_config
        self._get_status_text = get_status_text
        self._icon: Optional["pystray.Icon"] = None

    def start(self) -> None:
        import pystray

        config = self._get_config()
        theme = "light"
        auto = config.auto_switch_enabled

        icon_image = icons.get_icon_for_state(auto, theme)

        self._icon = pystray.Icon(
            "ThemeSwitcher",
            icon_image,
            "Theme Switcher",
            menu=self._build_menu(),
        )
        self._icon.title = self._get_status_text()

        self._icon.run()

    def stop(self) -> None:
        if self._icon:
            self._icon.stop()

    def update_icon(self) -> None:
        if not self._icon:
            return
        config = self._get_config()
        from theme_switcher.theme import get_current_theme
        theme = get_current_theme()
        auto = config.auto_switch_enabled and not config.manual_override
        self._icon.icon = icons.get_icon_for_state(auto, theme)

    def update_menu(self) -> None:
        if self._icon:
            self._icon.menu = self._build_menu()

    def _build_menu(self):
        import pystray

        config = self._get_config()
        from theme_switcher.theme import get_current_theme

        current = get_current_theme()
        auto = config.auto_switch_enabled
        override = config.manual_override

        menu_items = []

        menu_items.append(
            pystray.MenuItem(
                f"Currently: {'Light' if current == THEME_LIGHT else 'Dark'} Theme",
                None,
                enabled=False,
            )
        )
        menu_items.append(pystray.Menu.SEPARATOR)

        if current == THEME_LIGHT:
            menu_items.append(
                pystray.MenuItem(
                    "Switch to Dark Theme",
                    lambda: self._on_action("switch_dark"),
                )
            )
        else:
            menu_items.append(
                pystray.MenuItem(
                    "Switch to Light Theme",
                    lambda: self._on_action("switch_light"),
                )
            )

        menu_items.append(pystray.Menu.SEPARATOR)

        menu_items.append(
            pystray.MenuItem(
                f"Auto-Switch: {'ON' if auto else 'OFF'}",
                lambda: self._on_action("toggle_auto"),
                checked=lambda item: self._get_config().auto_switch_enabled,
            )
        )

        menu_items.append(pystray.Menu.SEPARATOR)

        if auto and override:
            menu_items.append(
                pystray.MenuItem(
                    "Cancel Override",
                    lambda: self._on_action("cancel_override"),
                )
            )
        elif auto:
            menu_items.append(
                pystray.MenuItem(
                    "Override until next switch",
                    lambda: self._on_action("override_until_next"),
                )
            )

        menu_items.append(pystray.Menu.SEPARATOR)

        status = self._get_status_text()
        menu_items.append(
            pystray.MenuItem(f"Status: {status}", None, enabled=False)
        )

        menu_items.append(pystray.Menu.SEPARATOR)

        menu_items.append(
            pystray.MenuItem(
                "Re-detect Location",
                lambda: self._on_action("redetect_location"),
            )
        )
        menu_items.append(
            pystray.MenuItem(
                "Edit Config File...",
                lambda: self._on_action("configure"),
            )
        )
        menu_items.append(pystray.MenuItem("Exit", lambda: self._on_action("exit")))

        return pystray.Menu(*menu_items)
