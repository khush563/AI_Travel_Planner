import logging
from pathlib import Path
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from app.agents.itinerary_agent import ItineraryAgent
from app.agents.demo import DemoItineraryAgent, DemoResearchAgent
from app.agents.llm import OpenAIJsonLLM
from app.agents.research_agent import ResearchAgent
from app.api.schemas import PlanStatus, ReviewRequest, TravelRequest
from app.config import Settings
from app.graph.nodes import WorkflowNodes
from app.graph.workflow import build_workflow
from app.services.persistence import PlanRepository
from app.tools.restaurant_recommender import SearchResultRecommender
from app.tools.travel_time import ApproximateTravelTime
from app.tools.weather import OpenMeteoWeather
from app.tools.web_search import SerperSearch

logger = logging.getLogger(__name__)


class PlanNotFound(Exception):
    pass


class PlanConflict(Exception):
    pass


class PlanningFailure(Exception):
    pass


class PlanService:
    def __init__(self, directory: Path, nodes: WorkflowNodes):
        self.repository = PlanRepository(directory)
        self.checkpoint_path = directory / "checkpoints.sqlite"
        self.nodes = nodes
        self.nodes.on_stage = self.repository.set_stage

    @classmethod
    def from_settings(cls, settings: Settings) -> "PlanService":
        if settings.mode == "demo":
            return cls(settings.database_dir, WorkflowNodes(DemoResearchAgent(), DemoItineraryAgent()))
        llm = OpenAIJsonLLM(settings)
        research = ResearchAgent(SerperSearch(settings.serper_api_key), OpenMeteoWeather(), llm)
        planner = ItineraryAgent(llm, ApproximateTravelTime(), SearchResultRecommender())
        return cls(settings.database_dir, WorkflowNodes(research, planner))

    @staticmethod
    def _config(plan_id: str) -> dict:
        return {"configurable": {"thread_id": plan_id}}

    def create(self, request: TravelRequest) -> str:
        plan_id = str(uuid4())
        self.repository.create(plan_id, request)
        logger.info("plan_created plan_id=%s", plan_id)
        return plan_id

    def _sync(self, graph, plan_id: str) -> str:
        snapshot = graph.get_state(self._config(plan_id))
        state = snapshot.values
        if state.get("final_plan"):
            status = "FINALIZED"
        elif "review" in snapshot.next:
            status = "AWAITING_REVIEW"
        else:
            raise RuntimeError("Graph ended without a final plan or review interrupt")
        self.repository.save_state(plan_id, state, status)
        logger.info("stage_transition plan_id=%s stage=%s", plan_id, status)
        return status

    def run_initial(self, plan_id: str) -> None:
        plan = self.repository.get(plan_id)
        if plan is None or plan.status not in {"RESEARCHING", "PLANNING", "REVISING"}:
            return
        try:
            with SqliteSaver.from_conn_string(str(self.checkpoint_path)) as saver:
                graph = build_workflow(self.nodes, saver)
                config = self._config(plan_id)
                snapshot = graph.get_state(config)
                if plan.status == "REVISING" and plan.pending_review:
                    if snapshot.values.get("final_plan"):
                        pass
                    elif "review" in snapshot.next and snapshot.values.get("revision_number", 0) > (plan.review_revision or 0):
                        # A revision already reached the next review interrupt.
                        pass
                    elif "review" in snapshot.next:
                        graph.invoke(Command(resume=plan.pending_review), config)
                    else:
                        graph.invoke(None, config)
                elif not snapshot.values:
                    initial = {
                        "plan_id": plan_id, "travel_request": plan.request, "research": None,
                        "draft_itinerary": None, "review_status": None, "review_feedback": None,
                        "modification_request": None, "workflow_stage": "VALIDATING",
                        "final_plan": None, "errors": [], "revision_number": 0,
                    }
                    graph.invoke(initial, config)
                elif "review" not in snapshot.next and not snapshot.values.get("final_plan"):
                    graph.invoke(None, config)
                self._sync(graph, plan_id)
        except Exception:
            logger.exception("initial_planning_failed plan_id=%s", plan_id)
            self.repository.fail(plan_id)

    def review(self, plan_id: str, decision: ReviewRequest) -> PlanStatus:
        plan = self.repository.get(plan_id)
        if plan is None:
            raise PlanNotFound
        if plan.status != "AWAITING_REVIEW":
            raise PlanConflict("Plan is not awaiting review")
        if decision.modifications and plan.draft and decision.modifications.day > len(plan.draft["days"]):
            raise PlanConflict("Modification day is outside the itinerary")
        try:
            with SqliteSaver.from_conn_string(str(self.checkpoint_path)) as saver:
                graph = build_workflow(self.nodes, saver)
                snapshot = graph.get_state(self._config(plan_id))
                if "review" not in snapshot.next:
                    raise PlanConflict("Review checkpoint is unavailable")
                decision_data = decision.model_dump(mode="json", exclude_none=True)
                if not self.repository.claim_review(plan_id, decision_data, snapshot.values.get("revision_number", 0)):
                    raise PlanConflict("Plan review is already in progress")
                graph.invoke(Command(resume=decision_data), self._config(plan_id))
                self._sync(graph, plan_id)
        except PlanConflict:
            raise
        except Exception as exc:
            logger.exception("review_processing_failed plan_id=%s", plan_id)
            self.repository.fail(plan_id)
            raise PlanningFailure from exc
        return self.get(plan_id)

    def get(self, plan_id: str) -> PlanStatus:
        plan = self.repository.get(plan_id)
        if plan is None:
            raise PlanNotFound
        return PlanStatus(
            plan_id=plan.plan_id, status=plan.status.lower(),
            requires_review=plan.status == "AWAITING_REVIEW",
            research=plan.research, draft_itinerary=plan.draft, error=plan.error,
        )

    def final(self, plan_id: str) -> dict:
        plan = self.repository.get(plan_id)
        if plan is None:
            raise PlanNotFound
        if plan.status != "FINALIZED" or plan.final is None:
            raise PlanConflict("Plan has not been approved")
        return plan.final
