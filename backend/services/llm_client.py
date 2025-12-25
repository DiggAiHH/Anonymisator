"""
LLM client service with environment-based configuration.

Improvements:
- Retry logic with exponential backoff for transient failures
- Enhanced error handling with specific HTTP status codes
- Configurable timeout and retry parameters
- Better logging for observability
"""
import httpx
import logging
import asyncio
from typing import Dict, Optional
from pydantic_settings import BaseSettings
from enum import Enum

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    # Future: Add more providers as needed


class LLMSettings(BaseSettings):
    """LLM configuration from environment variables."""
    llm_api_url: str = "https://api.openai.com/v1/chat/completions"
    llm_api_key: str = ""
    llm_model: str = "gpt-4"
    llm_timeout: int = 60
    llm_max_retries: int = 3
    llm_retry_delay: float = 1.0  # Initial delay in seconds
    llm_provider: LLMProvider = LLMProvider.OPENAI
    
    class Config:
        env_file = ".env"


class LLMClient:
    """
    Client for external LLM API calls with retry logic and enhanced error handling.
    
    Implements exponential backoff for transient failures and proper error categorization.
    """
    
    # HTTP status codes that should trigger a retry
    RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
    
    def __init__(self):
        """Initialize LLM client with environment configuration."""
        self.settings = LLMSettings()
        self.client = httpx.AsyncClient(timeout=self.settings.llm_timeout)
        self._circuit_breaker_failures = 0
        self._circuit_breaker_threshold = 5
    
    async def generate(self, prompt: str, task: str) -> str:
        """
        Generate LLM response for anonymized text with retry logic.
        
        Implements exponential backoff for transient failures.
        
        Args:
            prompt: Anonymized text to process
            task: Task description (e.g., "summarize", "extract")
        
        Returns:
            LLM generated response
            
        Raises:
            Exception: If all retries are exhausted or non-retryable error occurs
        """
        if not self.settings.llm_api_key:
            logger.warning("LLM API key not configured, returning mock response")
            return self._generate_mock_response(prompt, task)
        
        # Check circuit breaker
        if self._circuit_breaker_failures >= self._circuit_breaker_threshold:
            logger.error(
                f"Circuit breaker open: {self._circuit_breaker_failures} consecutive failures. "
                "Returning mock response."
            )
            return self._generate_mock_response(prompt, task)
        
        last_exception = None
        
        for attempt in range(self.settings.llm_max_retries):
            try:
                response = await self._make_request(prompt, task)
                
                # Reset circuit breaker on success
                self._circuit_breaker_failures = 0
                return response
                
            except httpx.HTTPStatusError as e:
                last_exception = e
                status_code = e.response.status_code
                
                # Non-retryable errors
                if status_code not in self.RETRYABLE_STATUS_CODES:
                    logger.error(
                        f"Non-retryable LLM API error: {status_code}. "
                        f"Response: {e.response.text[:200]}"
                    )
                    self._circuit_breaker_failures += 1
                    raise Exception(f"LLM API error: {status_code}")
                
                # Retryable error - calculate backoff
                if attempt < self.settings.llm_max_retries - 1:
                    delay = self.settings.llm_retry_delay * (2 ** attempt)
                    logger.warning(
                        f"LLM API error {status_code} (attempt {attempt + 1}/"
                        f"{self.settings.llm_max_retries}). Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"LLM API error {status_code}. All {self.settings.llm_max_retries} "
                        "retries exhausted."
                    )
                    self._circuit_breaker_failures += 1
                    
            except httpx.TimeoutException as e:
                last_exception = e
                if attempt < self.settings.llm_max_retries - 1:
                    delay = self.settings.llm_retry_delay * (2 ** attempt)
                    logger.warning(
                        f"LLM API timeout (attempt {attempt + 1}/"
                        f"{self.settings.llm_max_retries}). Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("LLM API timeout. All retries exhausted.")
                    self._circuit_breaker_failures += 1
                    
            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected LLM API error: {type(e).__name__}: {str(e)}")
                self._circuit_breaker_failures += 1
                break  # Don't retry unexpected errors
        
        # All retries exhausted
        raise Exception(f"LLM API call failed after {self.settings.llm_max_retries} attempts: {str(last_exception)}")
    
    async def _make_request(self, prompt: str, task: str) -> str:
        """
        Make the actual HTTP request to the LLM API.
        
        Separated for cleaner retry logic.
        """
        # Prepare request based on provider
        if self.settings.llm_provider == LLMProvider.OPENAI:
            payload = {
                "model": self.settings.llm_model,
                "messages": [
                    {
                        "role": "system",
                        "content": f"You are a medical assistant. Task: {task}"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            headers = {
                "Authorization": f"Bearer {self.settings.llm_api_key}",
                "Content-Type": "application/json"
            }
        else:
            raise ValueError(f"Unsupported LLM provider: {self.settings.llm_provider}")
        
        logger.info(
            f"Calling LLM API: {self.settings.llm_api_url} "
            f"(model: {self.settings.llm_model}, prompt_length: {len(prompt)})"
        )
        
        response = await self.client.post(
            self.settings.llm_api_url,
            json=payload,
            headers=headers
        )
        response.raise_for_status()
        
        result = response.json()
        generated_text = result["choices"][0]["message"]["content"]
        
        logger.info(
            f"LLM API call successful (response_length: {len(generated_text)})"
        )
        return generated_text
    
    def _generate_mock_response(self, prompt: str, task: str) -> str:
        """Generate a mock response for testing/fallback."""
        return (
            f"[Mock LLM Response for task: {task}]\n\n"
            f"Analysis of anonymized text:\n{prompt[:200]}...\n\n"
            f"Summary: The anonymized data shows clinical information with protected PHI."
        )
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
