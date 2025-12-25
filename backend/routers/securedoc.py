"""
SecureDoc router for PHI-protected document generation.
"""
from fastapi import APIRouter, HTTPException
import logging

from backend.models.schemas import SecureDocRequest, SecureDocResponse
from backend.services.anonymization import AnonymizationService
from backend.services.llm_client import LLMClient

logger = logging.getLogger(__name__)
router = APIRouter()

# LLM client can be shared (stateless)
llm_client = LLMClient()


@router.post("/securedoc/generate", response_model=SecureDocResponse)
async def generate_securedoc(request: SecureDocRequest):
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
        logger.info(f"Processing request for practice_id: {request.practice_id}, task: {request.task}")
        
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
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing request: {type(e).__name__}")
        # Clear session on error too
        anonymization_service.clear_session()
        raise HTTPException(status_code=500, detail="Error processing request")
