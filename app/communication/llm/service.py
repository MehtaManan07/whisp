import json
import logging
import asyncio
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from dataclasses import dataclass
import httpx

from app.infra.config import config

logger = logging.getLogger(__name__)


@dataclass
class LLMMessage:
    """Represents a message in the conversation."""
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMRequest:
    """Represents a request to the LLM service."""
    messages: List[LLMMessage]
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None


@dataclass
class LLMResponse:
    """Represents a response from the LLM service."""
    content: str
    usage: Optional[Dict[str, int]] = None
    model: Optional[str] = None
    finish_reason: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None


class LLMServiceError(Exception):
    """Base exception for LLM service errors."""
    pass


class LLMTimeoutError(LLMServiceError):
    """Raised when LLM request times out."""
    pass


class LLMAPIError(LLMServiceError):
    """Raised when LLM API returns an error."""
    pass


class LLMService:
    """
    Service class for making LLM calls via OpenRouter API.
    Provides a centralized interface for all agents to interact with language models.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        base_url: str = "https://openrouter.ai/api/v1"
    ):
        """
        Initialize the LLM service.
        
        Args:
            api_key: OpenRouter API key (defaults to config value)
            model_name: Default model to use (defaults to config value)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            base_url: Base URL for OpenRouter API
        """
        self.api_key = api_key or config.open_router_api_key
        self.default_model = model_name or config.open_router_model_name
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_url = base_url.rstrip("/")
        
        if not self.api_key:
            logger.warning("OpenRouter API key not configured")

    async def complete(
        self, 
        prompt: str, 
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """
        Simple completion interface for single prompt requests.
        
        Args:
            prompt: The prompt to send to the LLM
            model: Model to use (defaults to configured model)
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            **kwargs: Additional parameters for the API
            
        Returns:
            LLMResponse object with the completion
        """
        messages = [LLMMessage(role="user", content=prompt)]
        request = LLMRequest(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )
        response = await self.chat(request)
        return response

    async def chat(self, request: LLMRequest) -> LLMResponse:
        """
        Main chat interface supporting conversation history.
        
        Args:
            request: LLMRequest object with messages and parameters
            
        Returns:
            LLMResponse object with the response
            
        Raises:
            LLMServiceError: For various API and service errors
        """
        if not self.api_key:
            raise LLMServiceError("OpenRouter API key not configured")

        model = request.model or self.default_model
        
        # Build the API payload
        payload = {
            "model": model,
            "messages": [
                {"role": msg.role, "content": msg.content} 
                for msg in request.messages
            ]
        }
        
        # Add optional parameters
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.frequency_penalty is not None:
            payload["frequency_penalty"] = request.frequency_penalty
        if request.presence_penalty is not None:
            payload["presence_penalty"] = request.presence_penalty

        return await self._make_request_with_retry(payload)

    async def _make_request_with_retry(self, payload: Dict[str, Any]) -> LLMResponse:
        """
        Make API request with retry logic and error handling.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://whisp.finance",  # Optional: for OpenRouter analytics
            "X-Title": "Whisp Finance Assistant"  # Optional: for OpenRouter analytics
        }

        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    

                    # Handle HTTP errors
                    if response.status_code != 200:
                        error_msg = f"HTTP {response.status_code}: {response.text}"
                        logger.error(f"OpenRouter API error: {error_msg}")
                        
                        # Don't retry on client errors (4xx)
                        if 400 <= response.status_code < 500:
                            raise LLMAPIError(f"Client error: {error_msg}")
                        
                        # Retry on server errors (5xx)
                        if attempt < self.max_retries:
                            await self._wait_before_retry(attempt)
                            continue
                        else:
                            raise LLMAPIError(f"Server error after {self.max_retries} retries: {error_msg}")

                    # Parse response
                    data = response.json()
                    return self._parse_response(data)

            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning(f"LLM request timeout (attempt {attempt + 1}/{self.max_retries + 1})")
                if attempt < self.max_retries:
                    await self._wait_before_retry(attempt)
                    continue

            except httpx.RequestError as e:
                last_exception = e
                logger.error(f"Network error during LLM request: {str(e)}")
                if attempt < self.max_retries:
                    await self._wait_before_retry(attempt)
                    continue

            except json.JSONDecodeError as e:
                last_exception = e
                logger.error(f"Invalid JSON response from OpenRouter: {str(e)}")
                raise LLMAPIError(f"Invalid response format: {str(e)}")

            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error during LLM request: {str(e)}")
                if attempt < self.max_retries:
                    await self._wait_before_retry(attempt)
                    continue

        # If we get here, all retries failed
        if isinstance(last_exception, httpx.TimeoutException):
            raise LLMTimeoutError(f"Request timed out after {self.max_retries} retries")
        else:
            raise LLMServiceError(f"Request failed after {self.max_retries} retries: {str(last_exception)}")

    def _parse_response(self, data: Dict[str, Any]) -> LLMResponse:
        """
        Parse the API response into an LLMResponse object.
        """
        try:
            print(f"Data: {json.dumps(data, indent=2)}")
            if "choices" not in data or not data["choices"]:
                raise LLMAPIError("No choices in API response")

            choice = data["choices"][0]
            message = choice.get("message", {})
            content = message.get("content", "").strip()
            
            if not content:
                logger.warning("Empty content in LLM response")
                content = "I apologize, but I couldn't generate a proper response. Please try again."

            # Extract JSON from markdown code blocks if present
            processed_content = self._extract_json_from_markdown(content)

            return LLMResponse(
                content=processed_content,
                usage=data.get("usage"),
                model=data.get("model"),
                finish_reason=choice.get("finish_reason"),
                raw_response=data
            )

        except (KeyError, IndexError) as e:
            logger.error(f"Unexpected response format from OpenRouter: {data}")
            raise LLMAPIError(f"Unexpected response format: {str(e)}")

    def _extract_json_from_markdown(self, content: str) -> str:
        """
        Extract JSON content from markdown code blocks.
        
        Args:
            content: Raw content that may contain markdown-wrapped JSON
            
        Returns:
            Extracted JSON string or original content if no markdown blocks found
        """
        # Check if content contains markdown code blocks
        if "```json" in content and "```" in content:
            # Find the start and end of the JSON block
            start_marker = "```json"
            end_marker = "```"
            
            start_idx = content.find(start_marker)
            if start_idx != -1:
                # Move past the start marker and any newline
                json_start = start_idx + len(start_marker)
                if json_start < len(content) and content[json_start] == '\n':
                    json_start += 1
                
                # Find the end marker after the start
                end_idx = content.find(end_marker, json_start)
                if end_idx != -1:
                    # Extract the JSON content
                    json_content = content[json_start:end_idx].strip()
                    logger.debug(f"Extracted JSON from markdown: {json_content}")
                    return json_content
        
        # Check for generic code blocks without language specification
        elif "```" in content:
            lines = content.split('\n')
            in_code_block = False
            json_lines = []
            
            for line in lines:
                if line.strip() == "```":
                    if not in_code_block:
                        in_code_block = True
                        continue
                    else:
                        # End of code block
                        break
                elif in_code_block:
                    json_lines.append(line)
            
            if json_lines:
                json_content = '\n'.join(json_lines).strip()
                # Validate that it looks like JSON
                if json_content.startswith('{') and json_content.endswith('}'):
                    logger.debug(f"Extracted JSON from generic code block: {json_content}")
                    return json_content
        
        # Return original content if no extraction needed
        return content

    async def _wait_before_retry(self, attempt: int) -> None:
        """
        Wait before retrying with exponential backoff.
        """
        delay = min(2 ** attempt, 10)  # Cap at 10 seconds
        logger.info(f"Waiting {delay} seconds before retry...")
        await asyncio.sleep(delay)

    def create_system_message(self, content: str) -> LLMMessage:
        """Helper to create a system message."""
        return LLMMessage(role="system", content=content)

    def create_user_message(self, content: str) -> LLMMessage:
        """Helper to create a user message."""
        return LLMMessage(role="user", content=content)

    def create_assistant_message(self, content: str) -> LLMMessage:
        """Helper to create an assistant message."""
        return LLMMessage(role="assistant", content=content)

    def build_conversation(
        self, 
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        user_message: Optional[str] = None
    ) -> List[LLMMessage]:
        """
        Helper to build a conversation with system prompt and message history.
        
        Args:
            system_prompt: Optional system prompt
            messages: Optional list of {"role": str, "content": str} messages
            user_message: Optional final user message to add
            
        Returns:
            List of LLMMessage objects
        """
        conversation = []
        
        if system_prompt:
            conversation.append(self.create_system_message(system_prompt))
        
        if messages:
            for msg in messages:
                conversation.append(LLMMessage(
                    role=msg["role"], 
                    content=msg["content"]
                ))
        
        if user_message:
            conversation.append(self.create_user_message(user_message))
        
        return conversation

    async def generate_with_system_prompt(
        self,
        system_prompt: str,
        user_message: str,
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """
        Convenience method for generating with a system prompt and user message.
        
        Args:
            system_prompt: System prompt to set context
            user_message: User message to respond to
            model: Model to use
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            **kwargs: Additional parameters
            
        Returns:
            LLMResponse object
        """
        messages = [
            self.create_system_message(system_prompt),
            self.create_user_message(user_message)
        ]
        
        request = LLMRequest(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )
        
        return await self.chat(request)

    def get_model_info(self) -> Dict[str, Union[str, bool]]:
        """Get information about the current model configuration."""
        return {
            "default_model": self.default_model,
            "base_url": self.base_url,
            "timeout": str(self.timeout),
            "max_retries": str(self.max_retries),
            "api_key_configured": bool(self.api_key)
        }


# Global instance for easy access
llm_service = LLMService()
