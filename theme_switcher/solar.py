"""Sunrise/sunset calculation using astral."""

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from astral import LocationInfo
from astral.sun import sun
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger(__name__)


def calculate_sun_times(
    latitude: float,
    longitude: float,
    timezone: str,
    target_date: Optional[date] = None,
) -> dict:
    if target_date is None:
        target_date = date.today()

    try:
        tz = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, KeyError):
        logger.warning("Unknown timezone '%s', falling back to UTC", timezone)
        tz = ZoneInfo("UTC")

    location = LocationInfo(
        name="user_location",
        region="",
        timezone=timezone,
        latitude=latitude,
        longitude=longitude,
    )

    try:
        s = sun(location.observer, date=target_date, tzinfo=timezone)
        return {
            "sunrise": s["sunrise"],
            "sunset": s["sunset"],
            "dawn": s.get("dawn"),
            "dusk": s.get("dusk"),
        }
    except ValueError as e:
        logger.warning("Sun calculation failed for %s: %s", target_date, e)
        raise


def calculate_next_transition(config, now: Optional[datetime] = None) -> Optional[tuple]:
    if now is None:
        now = datetime.now().astimezone()

    today = now.date()

    try:
        times = calculate_sun_times(
            config.latitude,
            config.longitude,
            config.timezone,
            today,
        )
    except ValueError:
        try:
            times = calculate_sun_times(
                config.latitude,
                config.longitude,
                config.timezone,
                today + timedelta(days=1),
            )
        except ValueError:
            return None

    sunrise = times["sunrise"] + timedelta(minutes=config.sunrise_offset_minutes)
    sunset = times["sunset"] + timedelta(minutes=config.sunset_offset_minutes)

    current_theme = _get_effective_theme(config)

    if current_theme == "dark":
        if now < sunrise:
            return ("light", sunrise)
        elif now < sunset:
            return ("dark", sunset)
        else:
            tomorrow_times = _get_tomorrow_times(config, now)
            if tomorrow_times:
                return ("light", tomorrow_times["sunrise"])
            return None
    else:
        if now < sunrise:
            return ("light", sunrise)
        elif now < sunset:
            return ("dark", sunset)
        else:
            tomorrow_times = _get_tomorrow_times(config, now)
            if tomorrow_times:
                return ("light", tomorrow_times["sunrise"])
            return None


def get_theme_for_now(config, now=None) -> Optional[str]:
    """Return the theme that should be active right now based on sun position."""
    from datetime import datetime as dt

    if now is None:
        now = dt.now().astimezone()

    today = now.date()

    try:
        times = calculate_sun_times(
            config.latitude, config.longitude, config.timezone, today
        )
    except ValueError:
        return None

    sunrise = times["sunrise"] + timedelta(minutes=config.sunrise_offset_minutes)
    sunset = times["sunset"] + timedelta(minutes=config.sunset_offset_minutes)

    if sunrise <= now < sunset:
        return "light"
    return "dark"


def _get_effective_theme(config) -> str:
    from theme_switcher.theme import get_current_theme
    if config.manual_override and config.forced_theme:
        return config.forced_theme
    return get_current_theme()


def _get_tomorrow_times(config, now: datetime) -> Optional[dict]:
    tomorrow = (now + timedelta(days=1)).date()
    try:
        times = calculate_sun_times(
            config.latitude,
            config.longitude,
            config.timezone,
            tomorrow,
        )
        return {
            "sunrise": times["sunrise"] + timedelta(minutes=config.sunrise_offset_minutes),
            "sunset": times["sunset"] + timedelta(minutes=config.sunset_offset_minutes),
        }
    except ValueError:
        return None
