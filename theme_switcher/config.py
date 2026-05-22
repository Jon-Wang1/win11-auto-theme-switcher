"""Configuration management with YAML storage and first-run wizard."""

import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml


def _config_dir() -> Path:
    return Path(os.environ["APPDATA"]) / "ThemeSwitcher"


def _config_path() -> Path:
    return _config_dir() / "config.yaml"


def _backup_path() -> Path:
    return _config_dir() / "config.yaml.bak"


@dataclass
class Config:
    latitude: float = 0.0
    longitude: float = 0.0
    timezone: str = "Asia/Shanghai"
    city_name: str = ""

    auto_switch_enabled: bool = True
    manual_override: bool = False
    manual_override_until: Optional[str] = None
    forced_theme: str = "dark"

    sunrise_offset_minutes: int = 0
    sunset_offset_minutes: int = 0

    enable_wallpaper_switch: bool = False
    light_wallpaper_dir: str = ""
    dark_wallpaper_dir: str = ""

    config_version: int = 2

    @property
    def manual_override_until_dt(self) -> Optional[datetime]:
        if self.manual_override_until:
            return datetime.fromisoformat(self.manual_override_until)
        return None


def load() -> Optional[Config]:
    path = _config_path()
    if not path.exists():
        return None

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data is None:
            return None

        loc = data.get("location", {})
        theme = data.get("theme", {})
        sched = data.get("schedule", {})
        wp = data.get("wallpaper", {})

        return Config(
            latitude=float(loc.get("latitude", 0)),
            longitude=float(loc.get("longitude", 0)),
            timezone=str(loc.get("timezone", "Asia/Shanghai")),
            city_name=str(loc.get("city_name", "")),
            auto_switch_enabled=bool(theme.get("auto_switch_enabled", True)),
            manual_override=bool(theme.get("manual_override", False)),
            manual_override_until=theme.get("manual_override_until"),
            forced_theme=str(theme.get("forced_theme", "dark")),
            sunrise_offset_minutes=int(sched.get("sunrise_offset_minutes", 0)),
            sunset_offset_minutes=int(sched.get("sunset_offset_minutes", 0)),
            enable_wallpaper_switch=bool(wp.get("enabled", False)),
            light_wallpaper_dir=str(wp.get("light_dir", "")),
            dark_wallpaper_dir=str(wp.get("dark_dir", "")),
            config_version=int(data.get("config_version", 1)),
        )
    except (yaml.YAMLError, KeyError, ValueError):
        bak = _backup_path()
        if bak.exists():
            try:
                data = yaml.safe_load(bak.read_text(encoding="utf-8"))
                if data:
                    return load()
            except Exception:
                pass
        return None


def save(config: Config) -> None:
    data = {
        "config_version": config.config_version,
        "location": {
            "latitude": config.latitude,
            "longitude": config.longitude,
            "timezone": config.timezone,
            "city_name": config.city_name,
        },
        "theme": {
            "auto_switch_enabled": config.auto_switch_enabled,
            "manual_override": config.manual_override,
            "manual_override_until": config.manual_override_until,
            "forced_theme": config.forced_theme,
        },
        "schedule": {
            "sunrise_offset_minutes": config.sunrise_offset_minutes,
            "sunset_offset_minutes": config.sunset_offset_minutes,
        },
        "wallpaper": {
            "enabled": config.enable_wallpaper_switch,
            "light_dir": config.light_wallpaper_dir,
            "dark_dir": config.dark_wallpaper_dir,
        },
    }

    config_dir = _config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)

    path = _config_path()
    tmp = path.with_suffix(".tmp")

    tmp.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding="utf-8")

    if path.exists():
        bak = _backup_path()
        path.replace(bak)

    tmp.replace(path)


def auto_detect_location() -> Optional[dict]:
    """Detect location via IP geolocation using ip-api.com (free, no API key).
    Bypasses system proxy to get the real external IP, not the proxy exit node."""
    import json
    import urllib.request

    try:
        url = "http://ip-api.com/json/?fields=status,lat,lon,timezone,city,country"
        req = urllib.request.Request(url, headers={"User-Agent": "theme-switcher-win11/1.0"})
        # Bypass proxy to get real IP location
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)
        with opener.open(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("status") != "success":
            return None
        return {
            "latitude": round(data["lat"], 4),
            "longitude": round(data["lon"], 4),
            "timezone": data.get("timezone", ""),
            "city_name": f"{data.get('city', '')}, {data.get('country', '')}",
        }
    except Exception:
        return None


def first_run_wizard() -> Optional[Config]:
    print("\n" + "=" * 50)
    print("  Windows 11 Auto Theme Switcher - First Setup")
    print("=" * 50 + "\n")

    config = Config()

    print("Detecting your location...")
    loc = auto_detect_location()

    if loc:
        config.latitude = loc["latitude"]
        config.longitude = loc["longitude"]
        config.timezone = loc["timezone"]
        config.city_name = loc["city_name"]
        print(f"  Location: {loc['city_name']}")
        print(f"  Coordinates: {loc['latitude']}, {loc['longitude']}")
        print(f"  Timezone: {loc['timezone']}")
        confirm = input("\nIs this correct? (Y/n): ").strip().lower()
        if confirm == "n":
            loc = None

    if not loc:
        while True:
            city = input("Enter your city name (e.g. 'Beijing, China'): ").strip()
            if not city:
                print("City name cannot be empty.\n")
                continue

            print(f"\nLooking up coordinates for '{city}'...")
            try:
                from geopy.geocoders import Nominatim
                geolocator = Nominatim(user_agent="theme-switcher-win11")
                location = geolocator.geocode(city)
                if location is None:
                    print(f"Could not find '{city}'. Try a more specific name.\n")
                    continue

                config.latitude = round(location.latitude, 4)
                config.longitude = round(location.longitude, 4)
                config.city_name = city

                from timezonefinder import TimezoneFinder
                tf = TimezoneFinder()
                tz = tf.timezone_at(lng=config.longitude, lat=config.latitude)
                config.timezone = tz if tz else _detect_windows_timezone()

                print(f"  Lat: {config.latitude}, Lon: {config.longitude}")
                print(f"  Timezone: {config.timezone}")
                break

            except ImportError:
                print("Geocoding requires 'geopy' and 'timezonefinder' libraries.")
                print("Falling back to manual coordinate entry.\n")
                return _manual_coordinate_entry(config)
            except Exception as e:
                print(f"Geocoding failed: {e}")
                print("Falling back to manual coordinate entry.\n")
                return _manual_coordinate_entry(config)

    offset_str = input("\nSunrise offset in minutes (default 0, negative = earlier): ").strip()
    if offset_str:
        try:
            config.sunrise_offset_minutes = int(offset_str)
        except ValueError:
            pass

    offset_str = input("Sunset offset in minutes (default 0, negative = earlier): ").strip()
    if offset_str:
        try:
            config.sunset_offset_minutes = int(offset_str)
        except ValueError:
            pass

    print("\n--- Wallpaper Settings (optional) ---")
    enable_wp = input("Enable automatic wallpaper switching? (y/n, default n): ").strip().lower()
    if enable_wp == "y":
        config.enable_wallpaper_switch = True
        light_dir = input("  Light wallpaper directory (e.g. D:\\wallpaper\\light): ").strip()
        dark_dir = input("  Dark wallpaper directory (e.g. D:\\wallpaper\\dark): ").strip()
        if light_dir and Path(light_dir).is_dir():
            config.light_wallpaper_dir = light_dir
        if dark_dir and Path(dark_dir).is_dir():
            config.dark_wallpaper_dir = dark_dir
        if not config.light_wallpaper_dir or not config.dark_wallpaper_dir:
            print("  One or both directories not found. Wallpaper switching disabled.")
            config.enable_wallpaper_switch = False

    save(config)
    print(f"\nConfiguration saved to {_config_path()}")
    print("You can edit this file directly to change settings.\n")
    return config


def _manual_coordinate_entry(config: Config) -> Optional[Config]:
    print("\n--- Manual Coordinate Entry ---")
    try:
        config.latitude = float(input("Latitude (e.g. 40.7128): ").strip())
        config.longitude = float(input("Longitude (e.g. -74.006): ").strip())
    except ValueError:
        print("Invalid coordinates. Aborting setup.")
        return None

    tz = input("Timezone (e.g. Asia/Shanghai, press Enter to auto-detect): ").strip()
    if tz:
        config.timezone = tz
    else:
        config.timezone = _detect_windows_timezone()

    config.city_name = f"{config.latitude}, {config.longitude}"
    save(config)
    print(f"\nConfiguration saved to {_config_path()}")
    return config


def _detect_windows_timezone() -> str:
    try:
        import ctypes
        from ctypes import wintypes

        TIME_ZONE_ID_INVALID = 0xFFFFFFFF
        TIME_ZONE_ID_STANDARD = 1
        TIME_ZONE_ID_DAYLIGHT = 2

        class DYNAMIC_TIME_ZONE_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("Bias", wintypes.LONG),
                ("StandardName", wintypes.WCHAR * 32),
                ("StandardDate", wintypes.LONG * 8),
                ("StandardBias", wintypes.LONG),
                ("DaylightName", wintypes.WCHAR * 32),
                ("DaylightDate", wintypes.LONG * 8),
                ("DaylightBias", wintypes.LONG),
                ("TimeZoneKeyName", wintypes.WCHAR * 128),
                ("DynamicDaylightTimeDisabled", wintypes.BOOLEAN),
            ]

        tz_info = DYNAMIC_TIME_ZONE_INFORMATION()
        result = ctypes.windll.kernel32.GetDynamicTimeZoneInformation(ctypes.byref(tz_info))

        if result != TIME_ZONE_ID_INVALID:
            return tz_info.TimeZoneKeyName

    except Exception:
        pass

    return "Asia/Shanghai"
