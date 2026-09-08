from types import SimpleNamespace

import pytest

from app.config import _parse_api_keys
from app.services.access_control import authenticate_api_key, current_user, reset_current_user, set_current_user
from app.services.dataset_registry import DatasetAccessError, DatasetRegistry


def test_parse_per_user_credentials():
    assert _parse_api_keys("alice=secret-a; bob=secret-b") == (("alice", "secret-a"), ("bob", "secret-b"))
    assert _parse_api_keys("bad-entry;;alice=secret-a") == (("alice", "secret-a"),)


def test_per_user_authentication_resolves_identity_and_rejects_unknown_key():
    credentials = (("alice", "secret-a"), ("bob", "secret-b"))
    assert authenticate_api_key("secret-a", "", credentials) == "alice"
    assert authenticate_api_key("secret-b", "", credentials) == "bob"
    assert authenticate_api_key("secret-x", "", credentials) is None


def test_legacy_shared_key_maps_to_local_identity():
    assert authenticate_api_key("secret", "secret") == "local"
    assert authenticate_api_key("secret", "other") is None


def test_request_identity_is_reset_after_request_scope():
    before = current_user()
    token = set_current_user("alice")
    try:
        assert current_user() == "alice"
    finally:
        reset_current_user(token)
    assert current_user() == before


def test_dataset_registry_isolates_owners(tmp_path):
    registry = DatasetRegistry(tmp_path / "registry.sqlite3")
    alice_token = set_current_user("alice")
    try:
        dataset = SimpleNamespace(
            dataset_id="dataset-1", sha256="fingerprint", filename="hr.csv", path=tmp_path / "dataset-1.csv",
            size_bytes=10, row_count=1, column_count=1,
        )
        registry.register(dataset)
        assert registry.get("dataset-1")["owner_id"] == "alice"
    finally:
        reset_current_user(alice_token)

    bob_token = set_current_user("bob")
    try:
        assert registry.get("dataset-1") is None
        with pytest.raises(DatasetAccessError):
            registry.register(dataset)
    finally:
        reset_current_user(bob_token)
