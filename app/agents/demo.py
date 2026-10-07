"""Clearly labeled, deterministic sample data for trying the review workflow offline."""

from datetime import timedelta
import re

from app.api.schemas import (
    Activity, Attraction, Itinerary, ItineraryDay, Meal, Modification, Research,
    TravelRequest, WeatherInfo,
)


class DemoResearchAgent:
    def run(self, request: TravelRequest) -> Research:
        return Research(
            destination=request.destination,
            attractions=[
                Attraction(name="Local highlights", area="City center", description="Sample sightseeing category"),
                Attraction(name="Neighborhood walk", area="City center", description="Sample walking activity"),
                Attraction(name="Local food experience", area="City center", description="Sample dining category"),
            ],
            local_tips=["Sample content only. Confirm local transport, opening hours, and reservations before travel."],
            safety=["Demo mode does not provide live safety information."],
            seasonal_considerations=["Check the weather forecast closer to departure."],
            transportation=["Allow time between stops; route estimates are approximate."],
            weather=WeatherInfo(status="unavailable", note="Demo mode has no live weather data."),
            sources=[],
        )


class DemoItineraryAgent:
    def plan(self, request: TravelRequest, research: Research, previous: Itinerary | None = None,
             feedback: str | None = None) -> Itinerary:
        if previous is not None:
            revised = previous.model_copy(deep=True)
            match = re.search(r"\bday\s*(\d+)\b", feedback or "", re.IGNORECASE)
            targets = [int(match.group(1))] if match and int(match.group(1)) <= len(revised.days) else range(1, len(revised.days) + 1)
            for number in targets:
                day = revised.days[number - 1]
                day.theme = "Relaxed " + day.theme
                day.activities = day.activities[:1]
                day.notes.append("Reviewer feedback: " + (feedback or "Revise this day"))
                day.estimated_cost = round(sum(a.estimated_cost for a in day.activities) + sum(m.estimated_cost for m in day.meals), 2)
            revised.budget_breakdown["estimated_total"] = round(sum(day.estimated_cost for day in revised.days), 2)
            return revised

        count = (request.end_date - request.start_date).days + 1
        daily_cost = round(request.budget_max * 0.6 / count, 2)
        days = []
        for offset in range(count):
            day_number = offset + 1
            interest = request.interests[offset % len(request.interests)]
            activities = [
                Activity(start_time="09:30", end_time="11:30", name="Explore local highlights",
                         location="City center", description=f"Sample {interest} activity; choose a real venue in live mode.",
                         estimated_cost=round(daily_cost * 0.35, 2)),
                Activity(start_time="14:00", end_time="16:00", name="Neighborhood walk",
                         location="City center", description="Sample afternoon activity with a rest break.",
                         estimated_cost=round(daily_cost * 0.15, 2)),
            ]
            meals = [
                Meal(time="12:30", suggestion="Lunch near the morning activity", estimated_cost=round(daily_cost * 0.25, 2)),
                Meal(time="18:30", suggestion="Dinner in the city center", estimated_cost=round(daily_cost * 0.25, 2)),
            ]
            days.append(ItineraryDay(
                day=day_number, date=request.start_date + timedelta(days=offset), theme=f"{interest.title()} and local discovery",
                activities=activities, meals=meals, transportation=["Allow around 15–40 minutes between stops"],
                estimated_cost=round(sum(a.estimated_cost for a in activities) + sum(m.estimated_cost for m in meals), 2),
                notes=["Demo itinerary only: venues, prices, and times are examples."],
            ))
        total = round(sum(day.estimated_cost for day in days), 2)
        return Itinerary(
            trip_summary={"destination": request.destination, "travelers": request.travelers,
                          "start_date": str(request.start_date), "end_date": str(request.end_date), "currency": request.currency,
                          "mode": "demo"},
            days=days,
            budget_breakdown={"estimated_total": total, "currency": request.currency, "group_budget_max": request.budget_max},
            assumptions=["This is sample data for trying the workflow. Add API keys for live research and AI planning."],
        )

    def modify_day(self, request: TravelRequest, research: Research, previous: Itinerary,
                   modification: Modification) -> Itinerary:
        if modification.day > len(previous.days):
            raise ValueError("modification day is outside the itinerary")
        updated = previous.model_copy(deep=True)
        day = updated.days[modification.day - 1]
        day.theme = "Requested change"
        day.activities[0].name = "Reviewer requested activity"
        day.activities[0].description = modification.request
        day.notes.append("Demo change applied. Live mode researches specific venues.")
        return updated

