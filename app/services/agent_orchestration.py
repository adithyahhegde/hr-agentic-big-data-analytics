"""Durable, bounded state machine for planner-to-synthesis workflows."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from app.services.access_control import current_user

STEPS = ("PLANNING", "EXECUTION", "SYNTHESIS", "CONFIRMATION", "COMPLETED")
TERMINAL = {"COMPLETED", "FAILED"}


class WorkflowStateError(ValueError):
    """Raised when a workflow transition violates the persisted state machine."""


class AgentWorkflowStore:
    """SQLite-backed workflow state with bounded retry, recovery, confirmation, and owner isolation."""

    def __init__(self, path: Path | str = "data/hr_analytics.sqlite3", max_retries: int = 2) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_retries = max(0, min(int(max_retries), 5))
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS agent_workflows (id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL, fingerprint TEXT NOT NULL, status TEXT NOT NULL, step TEXT NOT NULL, retry_count INTEGER NOT NULL DEFAULT 0, plan_json TEXT NOT NULL DEFAULT '{}', evidence_json TEXT NOT NULL DEFAULT '{}', result_json TEXT NOT NULL DEFAULT '{}', error_type TEXT, confirmation_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, updated_at TEXT NOT NULL, owner_id TEXT NOT NULL DEFAULT 'local')")
            columns = {row[1] for row in db.execute("PRAGMA table_info(agent_workflows)")}
            if "confirmation_json" not in columns:
                db.execute("ALTER TABLE agent_workflows ADD COLUMN confirmation_json TEXT NOT NULL DEFAULT '{}'")
            if "owner_id" not in columns:
                db.execute("ALTER TABLE agent_workflows ADD COLUMN owner_id TEXT NOT NULL DEFAULT 'local'")
            db.execute("CREATE INDEX IF NOT EXISTS idx_agent_workflows_owner_updated ON agent_workflows(owner_id, updated_at DESC)")
            db.commit()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _owner() -> str:
        return current_user()

    def create(self, dataset_id: str, fingerprint: str, plan: dict[str, Any]) -> dict[str, Any]:
        workflow_id = str(uuid4())
        now = self._now()
        owner = self._owner()
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO agent_workflows(id,dataset_id,fingerprint,status,step,retry_count,plan_json,evidence_json,result_json,error_type,confirmation_json,created_at,updated_at,owner_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (workflow_id, dataset_id, fingerprint, "RUNNING", "PLANNING", 0, json.dumps(plan), "{}", "{}", None, "{}", now, now, owner))
            db.commit()
        return self.get(workflow_id)  # type: ignore[return-value]

    def get(self, workflow_id: str) -> dict[str, Any] | None:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM agent_workflows WHERE id=? AND owner_id=?", (workflow_id, self._owner())).fetchone()
        if not row:
            return None
        payload = dict(row)
        for key in ("plan_json", "evidence_json", "result_json", "confirmation_json"):
            try:
                payload[key.removesuffix("_json")] = json.loads(payload.pop(key))
            except (TypeError, json.JSONDecodeError):
                payload[key.removesuffix("_json")] = {}
        return payload

    def transition(self, workflow_id: str, next_step: str, *, evidence: dict[str, Any] | None = None, result: dict[str, Any] | None = None) -> dict[str, Any]:
        if next_step not in STEPS:
            raise WorkflowStateError("Unsupported workflow step.")
        current = self.get(workflow_id)
        if current is None:
            raise WorkflowStateError("Workflow not found.")
        allowed = {"PLANNING": {"EXECUTION", "FAILED"}, "EXECUTION": {"SYNTHESIS", "FAILED"}, "SYNTHESIS": {"CONFIRMATION", "COMPLETED", "FAILED"}, "CONFIRMATION": {"FAILED"}, "COMPLETED": set()}
        if next_step not in allowed[current["step"]]:
            raise WorkflowStateError("Invalid workflow transition.")
        status = "COMPLETED" if next_step == "COMPLETED" else ("FAILED" if next_step == "FAILED" else "RUNNING")
        now = self._now()
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE agent_workflows SET status=?,step=?,evidence_json=?,result_json=?,updated_at=? WHERE id=? AND owner_id=?", (status, next_step, json.dumps(evidence or current.get("evidence", {})), json.dumps(result or current.get("result", {})), now, workflow_id, self._owner()))
            db.commit()
        return self.get(workflow_id)  # type: ignore[return-value]

    def request_confirmation(self, workflow_id: str, actions: list[dict[str, Any]]) -> dict[str, Any]:
        """Pause a workflow before consequential actions; no action is executed here."""
        current = self.get(workflow_id)
        if current is None:
            raise WorkflowStateError("Workflow not found.")
        if current["step"] != "SYNTHESIS" or current["status"] != "RUNNING":
            raise WorkflowStateError("Confirmation can only be requested after synthesis.")
        if not actions:
            raise WorkflowStateError("At least one consequential action is required.")
        safe_actions = [{"action": str(item.get("action", ""))[:500], "evidence_ids": list(item.get("evidence_ids", []))[:20]} for item in actions]
        now = self._now()
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE agent_workflows SET status='WAITING_CONFIRMATION',step='CONFIRMATION',confirmation_json=?,updated_at=? WHERE id=? AND owner_id=?", (json.dumps({"actions": safe_actions, "requested_at": now}), now, workflow_id, self._owner()))
            db.commit()
        return self.get(workflow_id)  # type: ignore[return-value]

    def confirm(self, workflow_id: str, *, approved: bool) -> dict[str, Any]:
        """Require an explicit human decision before allowing consequential completion."""
        current = self.get(workflow_id)
        if current is None:
            raise WorkflowStateError("Workflow not found.")
        if current["step"] != "CONFIRMATION" or current["status"] != "WAITING_CONFIRMATION":
            raise WorkflowStateError("Workflow is not awaiting confirmation.")
        now = self._now()
        decision = {**current.get("confirmation", {}), "approved": bool(approved), "decided_at": now}
        if not approved:
            with sqlite3.connect(self.path) as db:
                db.execute("UPDATE agent_workflows SET status='FAILED',step='FAILED',error_type='HumanConfirmationDenied',confirmation_json=?,updated_at=? WHERE id=? AND owner_id=?", (json.dumps(decision), now, workflow_id, self._owner()))
                db.commit()
            return self.get(workflow_id)  # type: ignore[return-value]
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE agent_workflows SET status='COMPLETED',step='COMPLETED',confirmation_json=?,updated_at=? WHERE id=? AND owner_id=?", (json.dumps(decision), now, workflow_id, self._owner()))
            db.commit()
        return self.get(workflow_id)  # type: ignore[return-value]

    def fail(self, workflow_id: str, error_type: str, *, retryable: bool = True) -> dict[str, Any]:
        current = self.get(workflow_id)
        if current is None:
            raise WorkflowStateError("Workflow not found.")
        if current["status"] == "COMPLETED":
            raise WorkflowStateError("Completed workflows cannot be retried.")
        safe_error = str(error_type).split(".")[-1][:100] or "Exception"
        if retryable and current["retry_count"] < self.max_retries:
            now = self._now()
            with sqlite3.connect(self.path) as db:
                db.execute("UPDATE agent_workflows SET retry_count=retry_count+1,error_type=?,status='RUNNING',updated_at=? WHERE id=? AND owner_id=?", (safe_error, now, workflow_id, self._owner()))
                db.commit()
            return self.get(workflow_id)  # type: ignore[return-value]
        now = self._now()
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE agent_workflows SET status='FAILED',step='FAILED',error_type=?,updated_at=? WHERE id=? AND owner_id=?", (safe_error, now, workflow_id, self._owner()))
            db.commit()
        return self.get(workflow_id)  # type: ignore[return-value]

    def recoverable(self, workflow_id: str) -> dict[str, Any] | None:
        workflow = self.get(workflow_id)
        if workflow is None or workflow["status"] != "RUNNING":
            return None
        return workflow

    def run_step(self, workflow_id: str, handler: Callable[[dict[str, Any]], dict[str, Any]]) -> dict[str, Any]:
        """Run the current step once; consequential outputs must explicitly request confirmation."""
        workflow = self.recoverable(workflow_id)
        if workflow is None:
            raise WorkflowStateError("Workflow is not recoverable.")
        try:
            output = handler(workflow)
            if workflow["step"] == "SYNTHESIS" and output.get("consequential_actions"):
                return self.request_confirmation(workflow_id, output["consequential_actions"])
            next_step = {"PLANNING": "EXECUTION", "EXECUTION": "SYNTHESIS", "SYNTHESIS": "COMPLETED"}[workflow["step"]]
            return self.transition(workflow_id, next_step, evidence=output if workflow["step"] == "EXECUTION" else None, result=output if next_step == "COMPLETED" else None)
        except Exception as error:
            return self.fail(workflow_id, type(error).__name__)
