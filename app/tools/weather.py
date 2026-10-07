from datetime import date, timedelta
import logging
from typing import Protocol

import httpx

from app.api.schemas import WeatherDay, WeatherInfo

logger = logging.getLogger(__name__)


class WeatherProvider(Protocol):
    def forecast(self, destination: str, start: date, end: date) -> WeatherInfo: ...


class OpenMeteoWeather:
    """Open-Meteo forecast; far-future dates are marked unavailable."""

    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client(timeout=15)

    def forecast(self, destination: str, start: date, end: date) -> WeatherInfo:
        if start > date.today() + timedelta(days=15) or end < date.today():
            return WeatherInfo(status="unavailable", note="Forecast is unavailable for these travel dates; check closer to departure.")
        logger.info("weather_lookup destination_length=%d", len(destination))
        try:
            place = self.client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": destination, "count": 1, "language": "en", "format": "json"},
            )
            place.raise_for_status()
            matches = place.json().get("results", [])
            if not matches:
                return WeatherInfo(status="unavailable", note="Destination could not be geocoded.")
            forecast = self.client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": matches[0]["latitude"],
                    "longitude": matches[0]["longitude"],
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                    "timezone": "auto",
                    "forecast_days": 16,
                },
            )
            forecast.raise_for_status()
            daily = forecast.json().get("daily", {})
            days = []
            for index, value in enumerate(daily.get("time", [])):
                day = date.fromisoformat(value)
                if start <= day <= end:
                    days.append(WeatherDay(
                        date=day,
                        high_c=daily["temperature_2m_max"][index],
                        low_c=daily["temperature_2m_min"][index],
                        precipitation_probability=daily["precipitation_probability_max"][index],
                    ))
            return WeatherInfo(status="forecast" if days else "unavailable", daily=days,
                               note="Forecast covers only available dates; remaining dates need a later check." if len(days) < (end-start).days + 1 else "")
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            logger.warning("weather_lookup_failed error_type=%s", type(exc).__name__)
            return WeatherInfo(status="unavailable", note="Weather service is temporarily unavailable.")

