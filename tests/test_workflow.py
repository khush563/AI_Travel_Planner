import pytest

from app.api.schemas import ReviewRequest, TravelRequest
from app.services.plan_service import PlanConflict


def start_plan(service, request_data):
    plan_id = service.create(TravelRequest.model_validate(request_data))
    service.run_initial(plan_id)
    assert service.get(plan_id).status == "awaiting_review"
    return plan_id


def test_approval_survives_new_service_instance(service_factory, request_data):
    plan_id = start_plan(service_factory(), request_data)
    restarted = service_factory()
    assert restarted.get(plan_id).requires_review
    with pytest.raises(PlanConflict):
        restarted.final(plan_id)
    response = restarted.review(plan_id, ReviewRequest(action="approve"))
    assert response.status == "finalized"
    assert len(restarted.final(plan_id)["days"]) == 2
    assert service_factory().final(plan_id)["days"][0]["theme"] == "Highlights"


def test_reject_revises_and_interrupts_again(service_factory, request_data):
    service = service_factory()
    plan_id = start_plan(service, request_data)
    response = service.review(plan_id, ReviewRequest(action="reject", feedback="Make this relaxed"))
    assert response.status == "awaiting_review"
    assert response.draft_itinerary.days[0].theme == "Relaxed"
    with pytest.raises(PlanConflict):
        service.final(plan_id)
    assert service.review(plan_id, ReviewRequest(action="approve")).status == "finalized"


def test_modify_changes_only_requested_day(service_factory, request_data):
    service = service_factory()
    plan_id = start_plan(service, request_data)
    before = service.get(plan_id).draft_itinerary
    response = service.review(plan_id, ReviewRequest(
        action="modify", modifications={"day": 2, "request": "Replace the museum with a food tour"}))
    assert response.status == "awaiting_review"
    assert response.draft_itinerary.days[0] == before.days[0]
    assert response.draft_itinerary.days[1].theme == "Food tour"


def test_submitted_review_recovers_after_restart(service_factory, request_data):
    service = service_factory()
    plan_id = start_plan(service, request_data)
    assert service.repository.claim_review(plan_id, {"action": "approve"}, 0)
    restarted = service_factory()
    assert plan_id in restarted.repository.pending_ids()
    restarted.run_initial(plan_id)
    assert restarted.get(plan_id).status == "finalized"
