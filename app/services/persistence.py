from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3

from app.api.schemas import TravelRequest


@dataclass(frozen=True)
class StoredPlan:
    plan_id: str
    request: dict
    status: str
    research: dict | None
    draft: dict | None
    final: dict | None
    error: str | None
    pending_review: dict | None
    review_revision: int | None


class PlanRepository:
    """Plan index. LangGraph stores the authoritative execution checkpoint separately."""

    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "plans.sqlite"
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS plans (
                    plan_id TEXT PRIMARY KEY,
                    request_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    research_json TEXT,
                    draft_json TEXT,
                    final_json TEXT,
                    error TEXT,
                    pending_review_json TEXT,
                    review_revision INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def create(self, plan_id: str, request: TravelRequest) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO plans (plan_id, request_json, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (plan_id, request.model_dump_json(), "RESEARCHING", now, now),
            )

    def get(self, plan_id: str) -> StoredPlan | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM plans WHERE plan_id = ?", (plan_id,)).fetchone()
        if row is None:
            return None
        return StoredPlan(
            plan_id=row["plan_id"], request=json.loads(row["request_json"]), status=row["status"],
            research=json.loads(row["research_json"]) if row["research_json"] else None,
            draft=json.loads(row["draft_json"]) if row["draft_json"] else None,
            final=json.loads(row["final_json"]) if row["final_json"] else None,
            error=row["error"],
            pending_review=json.loads(row["pending_review_json"]) if row["pending_review_json"] else None,
            review_revision=row["review_revision"],
        )

    def pending_ids(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute("""SELECT plan_id FROM plans
                WHERE status IN ('RESEARCHING', 'PLANNING')
                   OR (status = 'REVISING' AND pending_review_json IS NOT NULL)""").fetchall()
        return [row["plan_id"] for row in rows]

    def set_stage(self, plan_id: str, stage: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE plans SET status = ?, updated_at = ? WHERE plan_id = ?",
                (stage, datetime.now(timezone.utc).isoformat(), plan_id),
            )

    def claim_review(self, plan_id: str, decision: dict, revision_number: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                """UPDATE plans SET status = 'REVISING', pending_review_json = ?, review_revision = ?,
                   updated_at = ? WHERE plan_id = ? AND status = 'AWAITING_REVIEW'""",
                (json.dumps(decision), revision_number, datetime.now(timezone.utc).isoformat(), plan_id),
            )
            return cursor.rowcount == 1

    def save_state(self, plan_id: str, state: dict, status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """UPDATE plans SET status = ?, research_json = ?, draft_json = ?, final_json = ?,
                   error = NULL, pending_review_json = NULL, review_revision = NULL,
                   updated_at = ? WHERE plan_id = ?""",
                (status, json.dumps(state.get("research")), json.dumps(state.get("draft_itinerary")),
                 json.dumps(state.get("final_plan")), datetime.now(timezone.utc).isoformat(), plan_id),
            )

    def fail(self, plan_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE plans SET status = 'FAILED', error = ?, updated_at = ? WHERE plan_id = ?",
                ("Planning could not be completed. Check service logs.", datetime.now(timezone.utc).isoformat(), plan_id),
            )
