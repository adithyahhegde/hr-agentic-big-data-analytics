from app.services.agent_orchestration import AgentWorkflowStore, WorkflowStateError


def test_workflow_survives_reopen_and_advances_in_order(tmp_path):
    path = tmp_path / "state.sqlite3"
    store = AgentWorkflowStore(path, max_retries=2)
    created = store.create("d1", "fp1", {"objective": "attrition_classification"})
    workflow_id = created["id"]

    reopened = AgentWorkflowStore(path, max_retries=2)
    assert reopened.recoverable(workflow_id)["step"] == "PLANNING"
    reopened.transition(workflow_id, "EXECUTION")
    reopened.transition(workflow_id, "SYNTHESIS", evidence={"evidence_id": "ev1"})
    completed = reopened.transition(workflow_id, "COMPLETED", result={"recommendations": [{"evidence_ids": ["ev1"]}]})

    assert completed["status"] == "COMPLETED"
    assert completed["step"] == "COMPLETED"
    assert completed["evidence"] == {"evidence_id": "ev1"}


def test_retry_is_bounded_and_preserves_current_step(tmp_path):
    store = AgentWorkflowStore(tmp_path / "state.sqlite3", max_retries=2)
    workflow_id = store.create("d1", "fp1", {})["id"]

    first = store.fail(workflow_id, "RuntimeError")
    second = store.fail(workflow_id, "RuntimeError")
    terminal = store.fail(workflow_id, "RuntimeError")

    assert first["status"] == "RUNNING"
    assert second["status"] == "RUNNING"
    assert second["retry_count"] == 2
    assert second["step"] == "PLANNING"
    assert terminal["status"] == "FAILED"
    assert terminal["step"] == "FAILED"
    assert terminal["retry_count"] == 2
    assert terminal["error_type"] == "RuntimeError"


def test_invalid_transition_and_completed_retry_are_rejected(tmp_path):
    store = AgentWorkflowStore(tmp_path / "state.sqlite3")
    workflow_id = store.create("d1", "fp1", {})["id"]

    try:
        store.transition(workflow_id, "SYNTHESIS")
        raise AssertionError("expected invalid transition")
    except WorkflowStateError:
        pass

    store.transition(workflow_id, "EXECUTION")
    store.transition(workflow_id, "SYNTHESIS")
    store.transition(workflow_id, "COMPLETED")
    try:
        store.fail(workflow_id, "RuntimeError")
        raise AssertionError("expected completed retry rejection")
    except WorkflowStateError:
        pass


def test_run_step_retries_without_exposing_exception_message(tmp_path):
    store = AgentWorkflowStore(tmp_path / "state.sqlite3", max_retries=1)
    workflow_id = store.create("d1", "fp1", {})["id"]

    def fail(_workflow):
        raise RuntimeError("employee salary=999999 /secret/path")

    failed_attempt = store.run_step(workflow_id, fail)
    assert failed_attempt["status"] == "RUNNING"
    assert failed_attempt["retry_count"] == 1
    assert failed_attempt["error_type"] == "RuntimeError"
    assert "salary" not in str(failed_attempt)
    assert "/secret/path" not in str(failed_attempt)


def test_confirmation_gate_survives_restart_and_requires_explicit_approval(tmp_path):
    path = tmp_path / "state.sqlite3"
    store = AgentWorkflowStore(path)
    workflow_id = store.create("d1", "fp1", {})["id"]
    store.transition(workflow_id, "EXECUTION")
    store.transition(workflow_id, "SYNTHESIS")

    waiting = store.request_confirmation(workflow_id, [{"action": "send compensation change", "evidence_ids": ["ev1"]}])
    assert waiting["status"] == "WAITING_CONFIRMATION"
    assert waiting["step"] == "CONFIRMATION"
    assert waiting["confirmation"]["actions"][0]["evidence_ids"] == ["ev1"]

    reopened = AgentWorkflowStore(path)
    assert reopened.recoverable(workflow_id) is None
    still_waiting = reopened.get(workflow_id)
    assert still_waiting["status"] == "WAITING_CONFIRMATION"

    try:
        reopened.transition(workflow_id, "COMPLETED")
        raise AssertionError("expected confirmation gate")
    except WorkflowStateError:
        pass

    denied = reopened.confirm(workflow_id, approved=False)
    assert denied["status"] == "FAILED"
    assert denied["error_type"] == "HumanConfirmationDenied"


def test_confirmation_approval_completes_workflow_and_sanitizes_actions(tmp_path):
    store = AgentWorkflowStore(tmp_path / "state.sqlite3")
    workflow_id = store.create("d1", "fp1", {})["id"]
    store.transition(workflow_id, "EXECUTION")
    store.transition(workflow_id, "SYNTHESIS")

    waiting = store.request_confirmation(workflow_id, [{"action": "A" * 1000, "evidence_ids": [str(i) for i in range(100)]}])
    assert len(waiting["confirmation"]["actions"][0]["action"]) == 500
    assert len(waiting["confirmation"]["actions"][0]["evidence_ids"]) == 20

    completed = store.confirm(workflow_id, approved=True)
    assert completed["status"] == "COMPLETED"
    assert completed["step"] == "COMPLETED"
    assert completed["confirmation"]["approved"] is True
