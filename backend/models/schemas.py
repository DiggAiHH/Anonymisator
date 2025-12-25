"""
Pydantic models for request/response schemas.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional


class SecureDocRequest(BaseModel):
    """Request model for /v1/securedoc/generate endpoint."""
    practice_id: str = Field(..., min_length=1, max_length=100)
    task: str = Field(..., min_length=1, max_length=100)
    text: str = Field(..., min_length=1, max_length=50000)

    @field_validator('text')
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validate text doesn't contain control characters."""
        # Allow newlines, tabs, but not other control characters
        for char in v:
            if ord(char) < 32 and char not in ['\n', '\t', '\r']:
                raise ValueError('Text contains invalid control characters')
        return v


class SecureDocResponse(BaseModel):
    """Response model for /v1/securedoc/generate endpoint."""
    output_text: str
    status: str = "success"


class StripeWebhookEvent(BaseModel):
    """Stripe webhook event model."""
    type: str
    data: dict
