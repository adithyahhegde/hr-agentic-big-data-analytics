from app.services.access_control import reset_current_user, set_current_user
from app.services.run_history import RunHistory


def test_run_history_and_explanations_are_owner_scoped(tmp_path):
    history = RunHistory(tmp_path / "history.sqlite3")
    alice = set_current_user("alice")
    try:
        run_id = history.record(
            "dataset-1",
            "fp-1",
            "attrition_classification",
            "SUCCEEDED",
            {"schema_version": "v1", "explainability": {"method": "permutation", "top_features": [{"feature": "tenure", "importance": 0.4}]}},
        )
        assert run_id > 0
        assert history.latest_matching("dataset-1", "attrition_classification", "fp-1", "v1") is not None
        assert history.latest_explanation("dataset-1", "attrition_classification", "fp-1", "v1")["run_id"] == run_id
    finally:
        reset_current_user(alice)

    bob = set_current_user("bob")
    try:
        assert history.latest_matching("dataset-1", "attrition_classification", "fp-1", "v1") is None
        assert history.list("dataset-1") == []
        assert history.latest_explanation("dataset-1", "attrition_classification", "fp-1", "v1") is None
    finally:
        reset_current_user(bob)
