"""Credential isolation through Hermes' real secret scope implementation."""

from __future__ import annotations

import json

import pytest
from agent import secret_scope

from hermes_fal_video import tools


@pytest.fixture
def secret_context(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setenv("FAL_KEY", "other-profile-key")
    previous = secret_scope.is_multiplex_active()
    token = secret_scope.set_secret_scope(None)
    try:
        yield
    finally:
        secret_scope.reset_secret_scope(token)
        secret_scope.set_multiplex_active(previous)


@pytest.mark.parametrize(
    ("multiplex", "scope", "expected"),
    [
        (True, None, ""),
        (True, {}, ""),
        (True, {"FAL_KEY": " profile-key "}, "profile-key"),
        (False, None, "other-profile-key"),
        (False, {}, "other-profile-key"),
    ],
)
def test_key_resolution_respects_profile_scope(secret_context, multiplex, scope, expected):
    secret_scope.set_multiplex_active(multiplex)
    token = secret_scope.set_secret_scope(scope)
    try:
        assert tools.get_fal_key() == expected
        assert tools.is_available() is bool(expected)
    finally:
        secret_scope.reset_secret_scope(token)


@pytest.mark.parametrize("operation", tools.OPERATIONS)
def test_unscoped_multiplex_refuses_client_creation(secret_context, operation):
    secret_scope.set_multiplex_active(True)

    def refuse_client(key):
        pytest.fail("An unscoped request must not create a FAL client")

    handler = tools.make_handler(operation, lambda key, default=None: default,
                                 make_client=refuse_client)
    result = json.loads(handler({"prompt": "continue the scene"}))
    assert result["success"] is False
    assert result["error_type"] == "auth_required"
