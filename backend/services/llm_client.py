"""
LLM client service with environment-based configuration.
"""
import httpx
import logging
from typing import Dict, Optional
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class LLMSettings(BaseSettings):
    """LLM configuration from environment variables."""
    llm_api_url: str = "https://api.openai.com/v1/chat/completions"
    llm_api_key: str = ""
    llm_model: str = "gpt-4"
    llm_timeout: int = 60
    
    class Config:
        env_file = ".env"


class LLMClient:
    """Client for external LLM API calls."""
    
    def __init__(self):
        """Initialize LLM client with environment configuration."""
        self.settings = LLMSettings()
        self.client = httpx.AsyncClient(timeout=self.settings.llm_timeout)
    
    async def generate(self, prompt: str, task: str) -> str:
        """
        Generate LLM response for anonymized text.
        
        Args:
            prompt: Anonymized text to process
            task: Task description (e.g., "summarize", "extract")
        
        Returns:
            LLM generated response
        """
        if not self.settings.llm_api_key:
            logger.warning("LLM API key not configured, returning mock response")
            # Return mock response with anonymized placeholders preserved
            return f"[Mock LLM Response for task: {task}]\n\nAnalysis of anonymized text:\n{prompt[:200]}...\n\nSummary: The anonymized data shows clinical information with protected PHI."
        
        try:
            # Prepare request based on OpenAI API format
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
            
            logger.info(f"Calling LLM API: {self.settings.llm_api_url}")
            response = await self.client.post(
                self.settings.llm_api_url,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            
            result = response.json()
            generated_text = result["choices"][0]["message"]["content"]
            logger.info("LLM API call successful")
            return generated_text
            
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM API HTTP error: {e.response.status_code}")
            raise Exception(f"LLM API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"LLM API call failed: {str(e)}")
            raise Exception(f"LLM API call failed: {str(e)}")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
