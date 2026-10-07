from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class TravelRequest(BaseModel):
    destination: str = Field(min_length=2, max_length=120)
    start_date: date
    end_date: date
    budget_min: float = Field(ge=0)
    budget_max: float = Field(gt=0)
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    interests: list[str] = Field(min_length=1, max_length=20)
    travelers: int = Field(ge=1, le=30)

    @model_validator(mode="after")
    def validate_trip(self) -> "TravelRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        if self.budget_max < self.budget_min:
            raise ValueError("budget_max must be at least budget_min")
        self.destination = self.destination.strip()
        self.interests = [item.strip() for item in self.interests if item.strip()]
        if not self.interests:
            raise ValueError("at least one nonempty interest is required")
        return self


class ReviewAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"


class Modification(BaseModel):
    day: int = Field(ge=1)
    request: str = Field(min_length=3, max_length=2000)


class ReviewRequest(BaseModel):
    action: ReviewAction
    feedback: str | None = Field(default=None, max_length=2000)
    modifications: Modification | None = None

    @model_validator(mode="after")
    def validate_review(self) -> "ReviewRequest":
        if self.action == ReviewAction.REJECT and not (self.feedback or "").strip():
            raise ValueError("feedback is required for rejection")
        if self.action == ReviewAction.MODIFY and self.modifications is None:
            raise ValueError("modifications are required for modification")
        return self


class SearchHit(BaseModel):
    title: str
    url: str
    snippet: str = ""


class Attraction(BaseModel):
    name: str
    area: str = ""
    description: str = ""
    source_url: str = ""
    estimated_cost_per_person: float | None = Field(default=None, ge=0)


class WeatherDay(BaseModel):
    date: date
    high_c: float | None = None
    low_c: float | None = None
    precipitation_probability: int | None = None


class WeatherInfo(BaseModel):
    status: Literal["forecast", "unavailable"]
    note: str = ""
    daily: list[WeatherDay] = Field(default_factory=list)


class Research(BaseModel):
    destination: str
    attractions: list[Attraction] = Field(default_factory=list)
    local_tips: list[str] = Field(default_factory=list)
    safety: list[str] = Field(default_factory=list)
    seasonal_considerations: list[str] = Field(default_factory=list)
    transportation: list[str] = Field(default_factory=list)
    restaurants: list[SearchHit] = Field(default_factory=list)
    weather: WeatherInfo
    sources: list[str] = Field(default_factory=list)


class Activity(BaseModel):
    start_time: str
    end_time: str
    name: str
    location: str
    description: str = ""
    estimated_cost: float = Field(ge=0)
    source_url: str = ""


class Meal(BaseModel):
    time: str
    suggestion: str
    estimated_cost: float = Field(ge=0)
    source_url: str = ""


class ItineraryDay(BaseModel):
    day: int = Field(ge=1)
    date: date
    theme: str
    activities: list[Activity]
    meals: list[Meal]
    transportation: list[str] = Field(default_factory=list)
    estimated_cost: float = Field(ge=0)
    notes: list[str] = Field(default_factory=list)


class Itinerary(BaseModel):
    trip_summary: dict
    days: list[ItineraryDay]
    budget_breakdown: dict
    assumptions: list[str] = Field(default_factory=list)


class PlanStatus(BaseModel):
    plan_id: str
    status: str
    requires_review: bool
    research: Research | None = None
    draft_itinerary: Itinerary | None = None
    error: str | None = None


class PlanCreated(BaseModel):
    plan_id: str
    status: str
