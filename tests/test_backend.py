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
        text = "Patient DOB: 01/15/1980, appointment on 2024-03-20"
        anonymized, mappings = service.anonymize(text)
        
        assert "01/15/1980" not in anonymized
        assert "2024-03-20" not in anonymized
        assert len([k for k in mappings.keys() if "DATE" in k]) == 2
    
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
            }
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
            }
        )
        assert response.status_code == 422
    
    def test_text_too_short(self):
        response = client.post(
            "/v1/securedoc/generate",
            json={
                "practice_id": "practice_123",
                "task": "summarize",
                "text": ""
            }
        )
        assert response.status_code == 422
    
    def test_text_with_control_characters(self):
        response = client.post(
            "/v1/securedoc/generate",
            json={
                "practice_id": "practice_123",
                "task": "summarize",
                "text": "Normal text\x00\x01 with control"
            }
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
            }
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
            }
        )
        assert response.status_code == 422


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
        assert response.status_code in [400, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
