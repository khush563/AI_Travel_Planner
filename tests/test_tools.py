from datetime import date, timedelta

import httpx

from app.api.schemas import SearchHit
from app.tools.restaurant_recommender import SearchResultRecommender
from app.tools.travel_time import ApproximateTravelTime
from app.tools.weather import OpenMeteoWeather
from app.tools.web_search import SerperSearch


def test_local_planning_tools():
    tool = ApproximateTravelTime()
    assert tool.estimate("Museum", "Cafe", "Center", "Center").minutes == 15
    assert tool.estimate("Museum", "Beach", "Center", "Coast").minutes == 40
    candidates = [SearchHit(title="Food market", url="https://example.org/market"),
                  SearchHit(title="Art museum", url="https://example.org/art")]
    recommended = SearchResultRecommender().recommend(candidates, ["food"], 50)
    assert recommended[0].title == "Food market"


def test_far_future_weather_is_not_presented_as_forecast():
    start = date.today() + timedelta(days=60)
    weather = OpenMeteoWeather().forecast("Paris", start, start + timedelta(days=2))
    assert weather.status == "unavailable"
    assert weather.daily == []


def test_serper_maps_live_result_shape_and_sends_key():
    def handle(request):
        assert request.headers["X-API-KEY"] == "test-key"
        assert request.url.path == "/search"
        return httpx.Response(200, json={"organic": [{"title": "Museum", "link": "https://example.org/museum", "snippet": "Art"}]})

    client = httpx.Client(transport=httpx.MockTransport(handle))
    results = SerperSearch("test-key", client).search("Paris museum")
    assert results[0].url == "https://example.org/museum"


def test_open_meteo_maps_daily_forecast():
    travel_date = date.today() + timedelta(days=2)

    def handle(request):
        if "geocoding" in request.url.host:
            return httpx.Response(200, json={"results": [{"latitude": 48.86, "longitude": 2.35}]})
        return httpx.Response(200, json={"daily": {
            "time": [str(travel_date)], "temperature_2m_max": [22.0],
            "temperature_2m_min": [12.0], "precipitation_probability_max": [30],
        }})

    client = httpx.Client(transport=httpx.MockTransport(handle))
    result = OpenMeteoWeather(client).forecast("Paris", travel_date, travel_date)
    assert result.status == "forecast"
    assert result.daily[0].high_c == 22.0
