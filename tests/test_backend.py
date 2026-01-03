"""
Comprehensive tests for SecureDoc Flow Backend.
Run with: python3 -m pytest tests/test_backend.py -v
"""

import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.anonymization import AnonymizationService

client = TestClient(app)


class TestHealthEndpoints:
    """Test health and root endpoints."""
    
    def test_root(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "SecureDoc Flow Privacy Proxy"
        assert data["status"] == "operational"
    
    def test_health(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestAnonymizationService:
    """Test PHI anonymization service."""
    
    def test_date_anonymization(self):
        service = AnonymizationService()
        text = "Patient DOB: 01/15/1980, appointment on 2024-03-20, Folgetermin: 31.12.2025, Bericht: 3. März 2026"
        anonymized, mappings = service.anonymize(text)
        
        assert "01/15/1980" not in anonymized
        assert "2024-03-20" not in anonymized
        assert "31.12.2025" not in anonymized
        assert "3. März 2026" not in anonymized
        assert len([k for k in mappings.keys() if "DATE" in k]) == 4
    
    def test_email_anonymization(self):
        service = AnonymizationService()
        text = "Contact: john.doe@example.com"
        anonymized, mappings = service.anonymize(text)
        
        assert "john.doe@example.com" not in anonymized
        assert len([k for k in mappings.keys() if "EMAIL" in k]) == 1
    
    def test_phone_anonymization(self):
        service = AnonymizationService()
        text = "Phone: (555) 123-4567 or 555-987-6543"
        anonymized, mappings = service.anonymize(text)
        
        assert len([k for k in mappings.keys() if "PHONE" in k]) >= 2
    
    def test_id_anonymization(self):
        service = AnonymizationService()
        text = "MRN: 12345678"
        anonymized, mappings = service.anonymize(text)
        
        assert "MRN: 12345678" not in anonymized
        assert len([k for k in mappings.keys() if "ID" in k]) == 1
    
    def test_name_anonymization(self):
        service = AnonymizationService()
        text = "Dr. Jane Smith"
        anonymized, mappings = service.anonymize(text)
        
        assert "Dr. Jane Smith" not in anonymized
        assert len([k for k in mappings.keys() if "NAME" in k]) == 1
    
    def test_reidentification(self):
        service = AnonymizationService()
        original = "Patient DOB: 01/15/1980"
        anonymized, mappings = service.anonymize(original)
        reidentified = service.reidentify(anonymized, mappings)
        
        assert "01/15/1980" in reidentified

    def test_art9_icd10_anonymization(self):
        service = AnonymizationService()
        text = "Diagnose: E11.9 (Diabetes mellitus Typ 2)"
        anonymized, mappings = service.anonymize(text)

        assert "E11.9" not in anonymized
        assert len([k for k in mappings.keys() if "ART9_HEALTH_ICD10" in k]) == 1

    def test_reidentify_fail_on_missing_placeholders(self, monkeypatch):
        monkeypatch.setenv("REIDENTIFY_FAIL_ON_MISSING_PLACEHOLDERS", "true")
        service = AnonymizationService()
        anonymized, mappings = service.anonymize("Contact: john.doe@example.com")
        # Remove placeholders from the downstream text to simulate LLM modification
        downstream = anonymized.replace(next(iter(mappings.keys())), "")

        with pytest.raises(ValueError):
            service.reidentify(downstream, mappings)
    
    def test_collision_resistance(self):
        service1 = AnonymizationService()
        service2 = AnonymizationService()
        
        text = "test@example.com"
        
        anon1, map1 = service1.anonymize(text)
        anon2, map2 = service2.anonymize(text)
        
        # Different service instances should produce different placeholders
        assert len(map1) > 0 and len(map2) > 0
        assert list(map1.keys())[0] != list(map2.keys())[0]
    
    def test_session_clearing(self):
        service = AnonymizationService()
        service.anonymize("test@example.com")
        
        assert len(service.current_mappings) > 0
        service.clear_session()
        assert len(service.current_mappings) == 0
        assert len(service.used_placeholders) == 0


class TestSecureDocEndpoint:
    """Test /v1/securedoc/generate endpoint."""
    
    def test_valid_request(self):
        response = client.post(
            "/v1/securedoc/generate",
            json={
                "practice_id": "practice_123",
                "task": "summarize",
                "text": "Patient presented with symptoms on 01/15/2024"
            },
            headers={"X-API-Key": "test-api-key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "output_text" in data
        assert data["status"] == "success"
    
    def test_empty_practice_id(self):
        response = client.post(
            "/v1/securedoc/generate",
            json={
                "practice_id": "",
                "task": "summarize",
                "text": "Some text"
            },
            headers={"X-API-Key": "test-api-key"},
        )
        assert response.status_code == 422
    
    def test_text_too_short(self):
        response = client.post(
            "/v1/securedoc/generate",
            json={
                "practice_id": "practice_123",
                "task": "summarize",
                "text": ""
            },
            headers={"X-API-Key": "test-api-key"},
        )
        assert response.status_code == 422
    
    def test_text_with_control_characters(self):
        response = client.post(
            "/v1/securedoc/generate",
            json={
                "practice_id": "practice_123",
                "task": "summarize",
                "text": "Normal text\x00\x01 with control"
            },
            headers={"X-API-Key": "test-api-key"},
        )
        assert response.status_code == 422
    
    def test_text_size_limit(self):
        # Test with text at max size (50000 chars)
        large_text = "a" * 50000
        response = client.post(
            "/v1/securedoc/generate",
            json={
                "practice_id": "practice_123",
                "task": "summarize",
                "text": large_text
            },
            headers={"X-API-Key": "test-api-key"},
        )
        assert response.status_code == 200
        
        # Test with text over max size
        too_large_text = "a" * 50001
        response = client.post(
            "/v1/securedoc/generate",
            json={
                "practice_id": "practice_123",
                "task": "summarize",
                "text": too_large_text
            },
            headers={"X-API-Key": "test-api-key"},
        )
        assert response.status_code == 422

    def test_missing_api_key_unauthorized(self):
        response = client.post(
            "/v1/securedoc/generate",
            json={
                "practice_id": "practice_123",
                "task": "summarize",
                "text": "Some text"
            }
        )
        assert response.status_code == 401


class TestStripeWebhook:
    """Test /v1/billing/stripe/webhook endpoint."""
    
    def test_missing_signature(self):
        response = client.post(
            "/v1/billing/stripe/webhook",
            json={"type": "test", "data": {}}
        )
        assert response.status_code == 400
        assert "Missing Stripe signature" in response.json()["detail"]
    
    def test_with_signature_no_secret(self):
        response = client.post(
            "/v1/billing/stripe/webhook",
            json={"type": "test", "data": {}},
            headers={"Stripe-Signature": "t=123,v1=fake"}
        )
        # Deterministic: secret missing fails closed.
        assert response.status_code == 500

    def test_webhook_success_and_idempotency_mocked(self, monkeypatch):
        import backend.routers.billing as billing_router

        # Configure secret so webhook proceeds to signature verification.
        billing_router.stripe_settings.stripe_webhook_secret = "whsec_test"

        fixed_now = 1_700_000_000
        monkeypatch.setattr(billing_router.time, "time", lambda: fixed_now, raising=True)

        event = {
            "id": "evt_test_1",
            "type": "checkout.session.completed",
            "created": fixed_now,
            "data": {"object": {"id": "cs_test_1"}},
        }

        def _construct_event(payload, sig_header, secret):
            return event

        monkeypatch.setattr(billing_router.stripe.Webhook, "construct_event", _construct_event, raising=True)

        r1 = client.post(
            "/v1/billing/stripe/webhook",
            json={"any": "payload"},
            headers={"Stripe-Signature": "t=123,v1=fake"},
        )
        assert r1.status_code == 200
        assert r1.json()["status"] == "success"

        # Same event id should be treated idempotently.
        r2 = client.post(
            "/v1/billing/stripe/webhook",
            json={"any": "payload"},
            headers={"Stripe-Signature": "t=123,v1=fake"},
        )
        assert r2.status_code == 200
        assert r2.json()["status"] == "success"
        assert "already processed" in r2.json().get("message", "")

    def test_webhook_timestamp_outside_tolerance_mocked(self, monkeypatch):
        import backend.routers.billing as billing_router

        billing_router.stripe_settings.stripe_webhook_secret = "whsec_test"

        now = 1_700_000_000
        old = now - 1_000
        monkeypatch.setattr(billing_router.time, "time", lambda: now, raising=True)

        def _construct_event(payload, sig_header, secret):
            return {"id": "evt_old", "type": "test", "created": old, "data": {"object": {}}}

        monkeypatch.setattr(billing_router.stripe.Webhook, "construct_event", _construct_event, raising=True)

        r = client.post(
            "/v1/billing/stripe/webhook",
            json={"any": "payload"},
            headers={"Stripe-Signature": "t=123,v1=fake"},
        )
        assert r.status_code == 400
        assert "tolerance" in r.json().get("detail", "")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
