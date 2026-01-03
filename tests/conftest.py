import pytest


@pytest.fixture(autouse=True)
def _reset_global_states(monkeypatch):
    """Make tests deterministic by resetting global in-memory state and mocking externals.

    - Clears SecureDoc rate-limit bucket state between tests
    - Clears Stripe webhook idempotency cache between tests
    - Mocks LLM calls so tests never depend on network or API keys
    """
    # Import inside fixture to avoid import-order surprises.
    import backend.routers.securedoc as securedoc_router
    import backend.routers.billing as billing_router

    # --- SecureDoc defaults (safe + stable for tests) ---
    # Use os.environ directly here (instead of monkeypatch.setenv) to avoid
    # edge cases with TestClient thread/context seeing an empty value.
    import os
    prev = {
        "SECUREDOC_REQUIRE_API_KEY": os.environ.get("SECUREDOC_REQUIRE_API_KEY"),
        "SECUREDOC_API_KEY": os.environ.get("SECUREDOC_API_KEY"),
        "SECUREDOC_RATE_LIMIT_ENABLED": os.environ.get("SECUREDOC_RATE_LIMIT_ENABLED"),
    }
    os.environ["SECUREDOC_REQUIRE_API_KEY"] = "true"
    os.environ["SECUREDOC_API_KEY"] = "test-api-key"
    os.environ["SECUREDOC_RATE_LIMIT_ENABLED"] = "false"

    # --- Reset global in-memory states ---
    securedoc_router._rate_state.clear()
    billing_router.processed_events.clear()

    # --- Mock LLM to avoid any external dependency ---
    async def _mock_generate(prompt: str, task: str) -> str:
        # Return exactly the anonymized prompt so placeholder integrity is guaranteed.
        return prompt

    monkeypatch.setattr(securedoc_router.llm_client, "generate", _mock_generate, raising=True)

    yield

    # Best-effort cleanup again.
    securedoc_router._rate_state.clear()
    billing_router.processed_events.clear()

    # Restore env
    for key, value in prev.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
