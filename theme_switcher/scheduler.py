"""Polling scheduler for theme transitions with sleep/wake detection."""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(self, on_switch: Callable[[str], None], get_config):
        self._on_switch = on_switch
        self._get_config = get_config
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._last_tick: Optional[datetime] = None
        self._next_transition: Optional[tuple] = None  # (theme, time)
        self._last_applied_theme: Optional[str] = None
        self._poll_interval = 10  # seconds

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._last_tick = datetime.now().astimezone()
        self._recalculate()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="scheduler")
        self._thread.start()
        logger.info("Scheduler started")

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        logger.info("Scheduler stopped")

    def recalculate(self) -> None:
        self._recalculate()

    def _recalculate(self) -> None:
        config = self._get_config()
        from theme_switcher.solar import calculate_next_transition
        self._next_transition = calculate_next_transition(config)
        if self._next_transition:
            theme, when = self._next_transition
            logger.info("Next transition: %s at %s", theme, when.isoformat())
        else:
            logger.info("No next transition (polar edge case)")

    def _loop(self) -> None:
        while self._running:
            try:
                self._tick()
            except Exception:
                logger.exception("Scheduler tick error")
            time.sleep(self._poll_interval)

    def _tick(self) -> None:
        now = datetime.now().astimezone()

        if self._last_tick:
            gap = (now - self._last_tick).total_seconds()
            if gap > self._poll_interval * 5:
                logger.info("Sleep/wake detected (gap=%.0fs), recalculating", gap)
                self._last_tick = now
                self._recalculate()
                self._check_override_expiry(now)
                self._apply_missed_transition(now)
                return

        self._last_tick = now

        if self._check_override_expiry(now):
            return

        config = self._get_config()
        if not config.auto_switch_enabled or config.manual_override:
            return

        if self._next_transition is None:
            if now.minute % 30 == 0 and now.second < self._poll_interval:
                self._recalculate()
            return

        theme, when = self._next_transition

        if now >= when:
            logger.info("Firing scheduled transition to %s", theme)
            self._on_switch(theme)
            self._last_applied_theme = theme
            self._recalculate()
            return

        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if when < midnight and now >= midnight:
            logger.info("Day changed, recalculating")
            self._recalculate()

    def _check_override_expiry(self, now: datetime) -> bool:
        config = self._get_config()
        if not config.manual_override:
            return False

        until = config.manual_override_until_dt
        if until and now >= until:
            logger.info("Manual override expired")
            config.manual_override = False
            config.manual_override_until = None
            config.forced_theme = ""
            from theme_switcher.config import save
            save(config)
            self._recalculate()
            self._apply_missed_transition(now)
            return True

        return False

    def _apply_missed_transition(self, now: datetime) -> None:
        config = self._get_config()
        if not config.auto_switch_enabled:
            return

        from theme_switcher.theme import get_current_theme
        from theme_switcher.solar import calculate_next_transition

        correct = calculate_next_transition(config, now)
        if correct is None:
            return

        target_theme, _ = correct
        current = get_current_theme()

        if current != target_theme:
            logger.info("Missed transition detected, applying %s", target_theme)
            self._on_switch(target_theme)
