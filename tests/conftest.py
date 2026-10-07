from datetime import date, timedelta

import pytest

from app.agents.itinerary_agent import ItineraryAgent
from app.agents.research_agent import ResearchAgent
from app.api.schemas import SearchHit, WeatherInfo
from app.graph.nodes import WorkflowNodes
from app.services.plan_service import PlanService
from app.tools.restaurant_recommender import SearchResultRecommender
from app.tools.travel_time import ApproximateTravelTime


class FakeSearch:
    def search(self, query: str, limit: int = 6):
        return [SearchHit(title="Museum", url="https://example.org/museum", snippet="A central museum")]


class FailingSearch:
    def search(self, query: str, limit: int = 6):
        raise RuntimeError("external search unavailable")


class FakeWeather:
    def forecast(self, destination, start, end):
        return WeatherInfo(status="unavailable", note="Forecast not yet available")


class FakeLLM:
    def generate(self, instructions, input_data):
        if "travel research agent" in instructions:
            return {
                "destination": input_data["destination"],
                "attractions": [{"name": "Museum", "area": "Center", "description": "Art", "source_url": "https://example.org/museum"}],
                "local_tips": ["Use transit"], "safety": [], "seasonal_considerations": [],
                "transportation": ["Metro"], "sources": ["https://example.org/museum"],
            }
        if "revising one itinerary day" in instructions:
            day = input_data["current_day"].copy()
            day["theme"] = "Food tour"
            day["activities"] = [{**day["activities"][0], "name": "Food tour"}]
            return day
        request = input_data["request"]
        start = date.fromisoformat(request["start_date"])
        end = date.fromisoformat(request["end_date"])
        count = (end - start).days + 1
        theme = "Relaxed" if input_data.get("feedback") else "Highlights"
        days = []
        for index in range(count):
            days.append({
                "day": index + 1, "date": str(start + timedelta(days=index)), "theme": theme,
                "activities": [{"start_time": "10:00", "end_time": "12:00", "name": "Museum",
                                "location": "Center", "description": "Art visit", "estimated_cost": 20,
                                "source_url": "https://example.org/museum"}],
                "meals": [{"time": "13:00", "suggestion": "Lunch nearby", "estimated_cost": 15}],
                "transportation": ["Metro"], "estimated_cost": 35, "notes": ["Estimated prices"],
            })
        return {"trip_summary": {"destination": request["destination"]}, "days": days,
                "budget_breakdown": {"estimated_total": 35 * count}, "assumptions": ["Costs are estimates"]}


@pytest.fixture
def request_data():
    start = date.today() + timedelta(days=30)
    return {"destination": "Paris", "start_date": str(start), "end_date": str(start + timedelta(days=1)),
            "budget_min": 100, "budget_max": 500, "interests": ["art", "food"], "travelers": 2}


@pytest.fixture
def service_factory(tmp_path):
    def build(search=None):
        llm = FakeLLM()
        nodes = WorkflowNodes(
            ResearchAgent(search or FakeSearch(), FakeWeather(), llm),
            ItineraryAgent(llm, ApproximateTravelTime(), SearchResultRecommender()),
        )
        return PlanService(tmp_path, nodes)
    return build

