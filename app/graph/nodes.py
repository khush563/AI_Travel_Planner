import logging
from typing import Callable

from langgraph.types import interrupt

from app.agents.itinerary_agent import ItineraryAgent
from app.agents.research_agent import ResearchAgent
from app.api.schemas import Itinerary, Modification, Research, TravelRequest
from app.graph.state import TravelState

logger = logging.getLogger(__name__)


class WorkflowNodes:
    def __init__(self, research_agent: ResearchAgent, itinerary_agent: ItineraryAgent):
        self.research_agent = research_agent
        self.itinerary_agent = itinerary_agent
        self.on_stage: Callable[[str, str], None] | None = None

    def _transition(self, plan_id: str, stage: str) -> None:
        logger.info("stage_transition plan_id=%s stage=%s", plan_id, stage)
        if self.on_stage:
            self.on_stage(plan_id, stage)

    def research(self, state: TravelState) -> dict:
        self._transition(state["plan_id"], "RESEARCHING")
        request = TravelRequest.model_validate(state["travel_request"])
        research = self.research_agent.run(request)
        return {"research": research.model_dump(mode="json"), "workflow_stage": "PLANNING"}

    def plan(self, state: TravelState) -> dict:
        self._transition(state["plan_id"], "PLANNING")
        request = TravelRequest.model_validate(state["travel_request"])
        research = Research.model_validate(state["research"])
        draft = self.itinerary_agent.plan(request, research)
        return {"draft_itinerary": draft.model_dump(mode="json"), "workflow_stage": "AWAITING_REVIEW"}

    def review(self, state: TravelState) -> dict:
        # Keep interrupt first: LangGraph re-executes this node on resume.
        decision = interrupt({
            "plan_id": state["plan_id"],
            "draft_itinerary": state["draft_itinerary"],
            "allowed_actions": ["approve", "reject", "modify"],
        })
        logger.info("review_decision plan_id=%s action=%s", state["plan_id"], decision["action"])
        return {
            "review_status": decision["action"],
            "review_feedback": decision.get("feedback"),
            "modification_request": decision.get("modifications"),
            "workflow_stage": "REVISING" if decision["action"] != "approve" else "FINALIZED",
        }

    def revise(self, state: TravelState) -> dict:
        self._transition(state["plan_id"], "REVISING")
        request = TravelRequest.model_validate(state["travel_request"])
        research = Research.model_validate(state["research"])
        previous = Itinerary.model_validate(state["draft_itinerary"])
        if state["review_status"] == "modify":
            modification = Modification.model_validate(state["modification_request"])
            draft = self.itinerary_agent.modify_day(request, research, previous, modification)
        else:
            draft = self.itinerary_agent.plan(request, research, previous, state["review_feedback"])
        return {
            "draft_itinerary": draft.model_dump(mode="json"),
            "workflow_stage": "AWAITING_REVIEW",
            "revision_number": state["revision_number"] + 1,
            "review_status": None,
            "review_feedback": None,
            "modification_request": None,
        }

    def finalize(self, state: TravelState) -> dict:
        logger.info("finalizing plan_id=%s", state["plan_id"])
        return {"final_plan": state["draft_itinerary"], "workflow_stage": "FINALIZED"}
