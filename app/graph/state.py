from typing import Any, TypedDict


class TravelState(TypedDict):
    plan_id: str
    travel_request: dict[str, Any]
    research: dict[str, Any] | None
    draft_itinerary: dict[str, Any] | None
    review_status: str | None
    review_feedback: str | None
    modification_request: dict[str, Any] | None
    workflow_stage: str
    final_plan: dict[str, Any] | None
    errors: list[str]
    revision_number: int

