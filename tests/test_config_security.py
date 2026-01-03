"""Tests for configuration-driven security behavior and internal helper functions.

Goal:
- Cover critical branches (fail-closed misconfig, rate limiting, auth toggles)
- Also cover key internal helper functions directly

Note:
- Some modules initialize objects at import time.
- SecureDoc auth/rate-limit helpers read env at call-time, so monkeypatch works.
"""

import os
import time

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

import backend.main as backend_main
import backend.routers.securedoc as securedoc_router


@pytest.fixture(autouse=True)
def _reset_global_states():
    # Ensure rate limit state doesn't leak across tests.
    securedoc_router._rate_state.clear()
    yield
    securedoc_router._rate_state.clear()


@pytest.fixture()
def client():
    return TestClient(backend_main.app)


def _make_request(client_host: str = "127.0.0.1") -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/v1/securedoc/generate",
        "raw_path": b"/v1/securedoc/generate",
        "query_string": b"",
        "headers": [],
        "client": (client_host, 12345),
        "server": ("testserver", 80),
    }

    async def _receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, _receive)


class TestBackendMainHelpers:
    def test_parse_csv_env_empty(self, monkeypatch):
        monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
        assert backend_main._parse_csv_env("CORS_ALLOW_ORIGINS") == []

    def test_parse_csv_env_csv(self, monkeypatch):
        monkeypatch.setenv("CORS_ALLOW_ORIGINS", " https://a.example ,https://b.example,  ,")
        assert backend_main._parse_csv_env("CORS_ALLOW_ORIGINS") == [
            "https://a.example",
            "https://b.example",
        ]

    def test_env_bool_defaults_and_values(self, monkeypatch):
        monkeypatch.delenv("CORS_ALLOW_CREDENTIALS", raising=False)
        assert backend_main._env_bool("CORS_ALLOW_CREDENTIALS", default=False) is False
        assert backend_main._env_bool("CORS_ALLOW_CREDENTIALS", default=True) is True

        monkeypatch.setenv("CORS_ALLOW_CREDENTIALS", "true")
        assert backend_main._env_bool("CORS_ALLOW_CREDENTIALS", default=False) is True

        monkeypatch.setenv("CORS_ALLOW_CREDENTIALS", "0")
        assert backend_main._env_bool("CORS_ALLOW_CREDENTIALS", default=True) is False


class TestSecureDocHelpers:
    def test_securedoc_env_bool(self, monkeypatch):
        monkeypatch.delenv("SECUREDOC_REQUIRE_API_KEY", raising=False)
        assert securedoc_router._env_bool("SECUREDOC_REQUIRE_API_KEY", default=True) is True
        assert securedoc_router._env_bool("SECUREDOC_REQUIRE_API_KEY", default=False) is False

        monkeypatch.setenv("SECUREDOC_REQUIRE_API_KEY", "yes")
        assert securedoc_router._env_bool("SECUREDOC_REQUIRE_API_KEY", default=False) is True

        monkeypatch.setenv("SECUREDOC_REQUIRE_API_KEY", "off")
        assert securedoc_router._env_bool("SECUREDOC_REQUIRE_API_KEY", default=True) is False

    def test_require_api_key_disabled_returns_empty(self, monkeypatch):
        monkeypatch.setenv("SECUREDOC_REQUIRE_API_KEY", "false")
        monkeypatch.delenv("SECUREDOC_API_KEY", raising=False)
        assert securedoc_router._require_api_key(x_api_key=None) == ""

    def test_require_api_key_misconfigured_503(self, monkeypatch):
        monkeypatch.setenv("SECUREDOC_REQUIRE_API_KEY", "true")
        monkeypatch.setenv("SECUREDOC_API_KEY", "")
        with pytest.raises(Exception) as exc:
            securedoc_router._require_api_key(x_api_key="anything")
        # fastapi.HTTPException string repr isn't stable; assert status_code.
        assert getattr(exc.value, "status_code", None) == 503

    def test_require_api_key_invalid_401(self, monkeypatch):
        monkeypatch.setenv("SECUREDOC_REQUIRE_API_KEY", "true")
        monkeypatch.setenv("SECUREDOC_API_KEY", "expected")
        with pytest.raises(Exception) as exc:
            securedoc_router._require_api_key(x_api_key="wrong")
        assert getattr(exc.value, "status_code", None) == 401

    def test_enforce_rate_limit_429_and_retry_after(self, monkeypatch):
        monkeypatch.setenv("SECUREDOC_RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("SECUREDOC_RATE_LIMIT_RPS", "100")
        monkeypatch.setenv("SECUREDOC_RATE_LIMIT_BURST", "1")

        req = _make_request()
        # First call consumes the burst token.
        securedoc_router._enforce_rate_limit(req, api_key="")

        # Second immediate call should be rate limited.
        with pytest.raises(Exception) as exc:
            securedoc_router._enforce_rate_limit(req, api_key="")
        assert getattr(exc.value, "status_code", None) == 429
        headers = getattr(exc.value, "headers", {}) or {}
        assert "Retry-After" in headers

    def test_enforce_rate_limit_misconfigured_503(self, monkeypatch):
        monkeypatch.setenv("SECUREDOC_RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("SECUREDOC_RATE_LIMIT_RPS", "not-a-number")
        monkeypatch.setenv("SECUREDOC_RATE_LIMIT_BURST", "5")

        req = _make_request()
        with pytest.raises(Exception) as exc:
            securedoc_router._enforce_rate_limit(req, api_key="")
        assert getattr(exc.value, "status_code", None) == 503


class TestSecureDocEndpointBranches:
    def test_auth_misconfigured_returns_503(self, client, monkeypatch):
        monkeypatch.setenv("SECUREDOC_REQUIRE_API_KEY", "true")
        monkeypatch.setenv("SECUREDOC_API_KEY", "")
        monkeypatch.setenv("SECUREDOC_RATE_LIMIT_ENABLED", "false")

        resp = client.post(
            "/v1/securedoc/generate",
            json={"practice_id": "p1", "task": "t", "text": "Some text"},
            headers={"X-API-Key": "whatever"},
        )
        assert resp.status_code == 503

    def test_auth_disabled_allows_missing_key(self, client, monkeypatch):
        monkeypatch.setenv("SECUREDOC_REQUIRE_API_KEY", "false")
        monkeypatch.delenv("SECUREDOC_API_KEY", raising=False)
        monkeypatch.setenv("SECUREDOC_RATE_LIMIT_ENABLED", "false")

        resp = client.post(
            "/v1/securedoc/generate",
            json={"practice_id": "p1", "task": "t", "text": "Some text"},
        )
        assert resp.status_code == 200

    def test_rate_limit_422_wins_over_429(self, client, monkeypatch):
        # Ensure rate limit is active and extremely strict...
        monkeypatch.setenv("SECUREDOC_RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("SECUREDOC_RATE_LIMIT_RPS", "0.0001")
        monkeypatch.setenv("SECUREDOC_RATE_LIMIT_BURST", "1")

        # ...but auth must pass (otherwise 401/503 would win).
        monkeypatch.setenv("SECUREDOC_REQUIRE_API_KEY", "true")
        monkeypatch.setenv("SECUREDOC_API_KEY", "expected")

        # Invalid request body should return 422 BEFORE rate limiting.
        resp = client.post(
            "/v1/securedoc/generate",
            json={"practice_id": "", "task": "t", "text": ""},
            headers={"X-API-Key": "expected"},
        )
        assert resp.status_code == 422

    def test_rate_limit_429_on_second_call(self, client, monkeypatch):
        monkeypatch.setenv("SECUREDOC_RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("SECUREDOC_RATE_LIMIT_RPS", "100")
        monkeypatch.setenv("SECUREDOC_RATE_LIMIT_BURST", "1")

        monkeypatch.setenv("SECUREDOC_REQUIRE_API_KEY", "true")
        monkeypatch.setenv("SECUREDOC_API_KEY", "expected")

        payload = {"practice_id": "p1", "task": "t", "text": "Some text"}

        r1 = client.post("/v1/securedoc/generate", json=payload, headers={"X-API-Key": "expected"})
        assert r1.status_code == 200

        r2 = client.post("/v1/securedoc/generate", json=payload, headers={"X-API-Key": "expected"})
        assert r2.status_code == 429
        assert "Retry-After" in r2.headers
