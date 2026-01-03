"""
SecureDoc router for PHI-protected document generation.
"""
import hashlib
import os
import secrets
import time
from fastapi import APIRouter, HTTPException, Depends, Header, Request, Security
import logging
from fastapi.security import APIKeyHeader

from backend.models.schemas import SecureDocRequest, SecureDocResponse
from backend.services.anonymization import AnonymizationService
from backend.services.llm_client import LLMClient

logger = logging.getLogger(__name__)
router = APIRouter()

# LLM client can be shared (stateless)
llm_client = LLMClient()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


_RATE_SALT = secrets.token_hex(16)
_rate_state: dict[str, tuple[float, float]] = {}


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _require_api_key(
    x_api_key: str | None = Security(api_key_header),
) -> str:
    """API-Key Auth for securedoc.

    Secure-by-default:
    - If SECUREDOC_REQUIRE_API_KEY=true and SECUREDOC_API_KEY is missing -> 503.
    - If key required and missing/invalid -> 401.
    """
    require = _env_bool("SECUREDOC_REQUIRE_API_KEY", default=True)
    expected = os.getenv("SECUREDOC_API_KEY", "").strip()

    if not require:
        return ""

    if not expected:
        raise HTTPException(status_code=503, detail="Auth misconfigured")

    if not x_api_key or x_api_key.strip() != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return x_api_key.strip()


def _enforce_rate_limit(request: Request, api_key: str) -> None:
    """In-memory token bucket rate limit.

    Best practice notes:
    - In production, use a shared store (Redis) to enforce limits across replicas.
    - We avoid storing raw IPs by hashing with a per-process salt.
    """
    enabled = _env_bool("SECUREDOC_RATE_LIMIT_ENABLED", default=True)
    if not enabled:
        return

    try:
        rate_per_sec = float(os.getenv("SECUREDOC_RATE_LIMIT_RPS", "2"))
        burst = float(os.getenv("SECUREDOC_RATE_LIMIT_BURST", "5"))
    except ValueError:
        raise HTTPException(status_code=503, detail="Rate limit misconfigured")

    if rate_per_sec <= 0 or burst <= 0:
        return

    # Keyed by API key when present; otherwise by hashed client address.
    if api_key:
        identity = f"key:{api_key}"
    else:
        client_host = getattr(getattr(request, "client", None), "host", "") or "unknown"
        digest = hashlib.sha256(f"{_RATE_SALT}:{client_host}".encode("utf-8")).hexdigest()[:16]
        identity = f"ip:{digest}"

    now = time.monotonic()
    tokens, last = _rate_state.get(identity, (burst, now))
    # Refill
    elapsed = max(0.0, now - last)
    tokens = min(burst, tokens + elapsed * rate_per_sec)

    if tokens < 1.0:
        retry_after = max(1, int((1.0 - tokens) / rate_per_sec) if rate_per_sec > 0 else 1)
        raise HTTPException(
            status_code=429,
            detail="Too Many Requests",
            headers={"Retry-After": str(retry_after)},
        )

    tokens -= 1.0
    _rate_state[identity] = (tokens, now)


@router.post(
    "/securedoc/generate",
    response_model=SecureDocResponse,
    responses={
        401: {"description": "Unauthorized (missing/invalid X-API-Key)"},
        429: {"description": "Too Many Requests (rate limit exceeded)", "headers": {"Retry-After": {"schema": {"type": "string"}}}},
        503: {"description": "Misconfiguration (missing required env vars)"},
    },
)
async def generate_securedoc(
    request: SecureDocRequest,
    http_request: Request,
    _auth: str = Security(_require_api_key),
):
    """
    Generate LLM-enhanced document with PHI protection.
    
    Process:
    1. Anonymize PHI in input text
    2. Send only anonymized text to LLM
    3. Re-identify LLM response
    4. Clear in-memory mappings
    
    Args:
        request: SecureDocRequest with practice_id, task, and text
    
    Returns:
        SecureDocResponse with output_text and status
    """
    # Create a new anonymization service instance for each request (thread-safe)
    anonymization_service = AnonymizationService()
    
    try:
        # Rate-limit only after the request body is validated (422 must win over 429)
        _enforce_rate_limit(http_request, _auth)
        # Avoid logging request fields (may contain sensitive/personal data)
        logger.info("Processing securedoc request")
        
        # Step 1: Anonymize input text
        anonymized_text, mappings = anonymization_service.anonymize(request.text)
        logger.info("Text anonymized successfully")
        
        # Step 2: Call LLM with ONLY anonymized text
        llm_response = await llm_client.generate(anonymized_text, request.task)
        logger.info("LLM response received")
        
        # Step 3: Re-identify the LLM response
        reidentified_response = anonymization_service.reidentify(llm_response, mappings)
        logger.info("Response re-identified successfully")
        
        # Step 4: Clear session data (critical for privacy)
        anonymization_service.clear_session()
        
        return SecureDocResponse(
            output_text=reidentified_response,
            status="success"
        )
        
    except HTTPException:
        # Preserve explicit HTTP errors (e.g., 429 rate limit, 503 misconfig)
        anonymization_service.clear_session()
        raise
    except ValueError:
        logger.error("Validation error")
        raise HTTPException(status_code=400, detail="Invalid request")
    except Exception as e:
        logger.error(f"Error processing request: {type(e).__name__}")
        # Clear session on error too
        anonymization_service.clear_session()
        raise HTTPException(status_code=500, detail="Error processing request")
