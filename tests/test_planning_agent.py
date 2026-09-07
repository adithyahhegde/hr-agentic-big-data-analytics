from app.config import Settings
from app.services.planning_agent import plan_analyses
from app.services.task_detection import TaskCandidate


def _task(objective, target=None, features=("age", "department")):
    return TaskCandidate(objective, "FEASIBLE", target, features, ("validated capability",))


def _blocked_task(objective, target=None):
    return TaskCandidate(objective, "BLOCKED", target, (), ("blocked",))


def test_planner_selects_only_feasible_objectives_offline():
    result = plan_analyses(
        [_task("attrition_classification", "attrition"), _blocked_task("salary_regression", "salary")],
        Settings(allow_local_llm=False),
    )
    assert result["agent"] == "bounded_analytical_planner_v1"
    assert result["mode"] == "deterministic_fallback"
    assert result["objective"] == "attrition_classification"
    assert [p["objective"] for p in result["plans"]] == ["attrition_classification"]
    assert result["plans"][0]["target_field"] == "attrition"
    assert result["raw_hr_records_accessed"] is False


def test_planner_returns_no_plan_when_all_capabilities_are_blocked():
    result = plan_analyses([], Settings(allow_local_llm=False))
    assert result["objective"] is None
    assert result["plans"] == []
    assert "No feasible analytical objective" in result["reason"]
    assert result["raw_hr_records_accessed"] is False
