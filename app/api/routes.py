from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.api.schemas import Itinerary, PlanCreated, PlanStatus, ReviewRequest, TravelRequest
from app.services.plan_service import PlanConflict, PlanNotFound, PlanService, PlanningFailure


def make_router(service: PlanService) -> APIRouter:
    router = APIRouter()

    @router.post("/plan", response_model=PlanCreated, status_code=202)
    def create_plan(request: TravelRequest, background_tasks: BackgroundTasks):
        plan_id = service.create(request)
        background_tasks.add_task(service.run_initial, plan_id)
        return PlanCreated(plan_id=plan_id, status="researching")

    @router.get("/plan/{plan_id}", response_model=PlanStatus)
    def get_plan(plan_id: str):
        try:
            return service.get(plan_id)
        except PlanNotFound:
            raise HTTPException(status_code=404, detail="Plan not found") from None

    @router.post("/plan/{plan_id}/review", response_model=PlanStatus)
    def review_plan(plan_id: str, decision: ReviewRequest):
        try:
            return service.review(plan_id, decision)
        except PlanNotFound:
            raise HTTPException(status_code=404, detail="Plan not found") from None
        except PlanConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from None
        except PlanningFailure:
            raise HTTPException(status_code=502, detail="Planning failed; inspect plan status and service logs") from None

    @router.get("/plan/{plan_id}/final", response_model=Itinerary)
    def get_final_plan(plan_id: str):
        try:
            return service.final(plan_id)
        except PlanNotFound:
            raise HTTPException(status_code=404, detail="Plan not found") from None
        except PlanConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from None

    return router

