import json
import logging
import re
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
import httpx

from app.core.config import config
from app.core.exceptions import LLMServiceError
from .key_manager import APIKeyManager

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
    call_stack: Optional[str] = None


@dataclass
class LLMResponse:
    """Represents a response from the LLM service."""

    content: str
    usage: Optional[Dict[str, int]] = None
    model: Optional[str] = None
    finish_reason: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None


class LLMService:
    """
    Service class for making LLM calls via OpenRouter and Groq APIs.
    Provides a centralized interface for all agents to interact with language models.
    """

    def __init__(
        self,
        api_key_manager: APIKeyManager,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: float = 30.0,
        base_url: str = "https://openrouter.ai/api/v1",
        use_key_rotation: bool = True,
    ):
        """
        Initialize the LLM service.

        Args:
            api_key_manager: APIKeyManager instance for key rotation
            api_key: OpenRouter API key (if provided, disables key rotation)
            model_name: Default model to use (defaults to config value)
            timeout: Request timeout in seconds
            base_url: Base URL for OpenRouter API
            use_key_rotation: Whether to use automatic key rotation (default: True)
        """
        self.api_key_manager = api_key_manager
        self.use_key_rotation = (
            use_key_rotation and api_key is None and api_key_manager is not None
        )
        self.api_key = api_key
        self.default_model = model_name or config.open_router_model_name
        self.timeout = timeout
        self.base_url = base_url.rstrip("/")

        if not self.use_key_rotation and not self.api_key:
            self.api_key = config.open_router_api_key
            if not self.api_key:
                logger.warning("OpenRouter API key not configured and key rotation disabled")
        elif self.use_key_rotation:
            logger.info("LLM service initialized with automatic key rotation")

    async def complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs,
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
        print(f"\033[94mLLMService.complete called\033[0m", kwargs)

        messages = [LLMMessage(role="user", content=prompt)]
        request = LLMRequest(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )
        return await self.chat(request)

    async def chat(self, request: LLMRequest) -> LLMResponse:
        """
        Main chat interface supporting conversation history using OpenRouter.

        Args:
            request: LLMRequest object with messages and parameters

        Returns:
            LLMResponse object with the response

        Raises:
            LLMServiceError: For various API and service errors
        """
        # Get API key (either from rotation or fixed key)
        if self.use_key_rotation:
            key_result = self.api_key_manager.get_available_key()
            if key_result is None:
                raise LLMServiceError("All API keys have reached their daily limit")
            current_api_key, key_index = key_result
        else:
            if not self.api_key:
                raise LLMServiceError("OpenRouter API key not configured")
            current_api_key = self.api_key
            key_index = None

        # Build payload
        payload = self._build_payload(request)

        # Make the request
        try:
            response = await self._make_openrouter_request(payload, current_api_key)

            # Record usage for key rotation
            if self.use_key_rotation and key_index is not None:
                self.api_key_manager.record_usage(key_index)

            return response
        except Exception:
            raise

    async def complete_with_groq(
        self,
        prompt: str,
        model: str = "llama-3.3-70b-versatile",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        """
        Use Groq API for fast inference with Llama models.
        
        Groq provides extremely fast inference speeds (up to 750 tokens/sec).
        
        Args:
            prompt: The prompt to send to the LLM
            model: Groq model to use (default: llama-3.3-70b-versatile)
                   Other options: llama-3.1-8b-instant, mixtral-8x7b-32768, etc.
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            **kwargs: Additional parameters for the API
            
        Returns:
            LLMResponse object with the completion
            
        Raises:
            LLMServiceError: If Groq API key not configured or request fails
        """
        print(f"\033[95mLLMService.complete_with_groq called\033[0m", kwargs)
        
        messages = [LLMMessage(role="user", content=prompt)]
        request = LLMRequest(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )
        
        return await self.chat_with_groq(request)

    async def chat_with_groq(self, request: LLMRequest) -> LLMResponse:
        """
        Chat interface using Groq API.
        
        Args:
            request: LLMRequest object with messages and parameters
            
        Returns:
            LLMResponse object with the response
            
        Raises:
            LLMServiceError: If Groq API key not configured or request fails
        """
        groq_api_key = config.groq_api_key
        if not groq_api_key:
            raise LLMServiceError("Groq API key not configured. Set GROQ_API_KEY in .env")
        
        # Build payload
        payload = self._build_payload(request, default_model="llama-3.3-70b-versatile")
        
        # Make the request
        return await self._make_groq_request(payload, groq_api_key)

    def _build_payload(
        self, request: LLMRequest, default_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Build API payload from request."""
        model = request.model or default_model or self.default_model
        
        payload = {
            "model": model,
            "messages": [
                {"role": msg.role, "content": msg.content} for msg in request.messages
            ],
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
        
        return payload

    async def _make_openrouter_request(
        self, payload: Dict[str, Any], api_key: str
    ) -> LLMResponse:
        """Make API request to OpenRouter."""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://whisp.finance",
            "X-Title": "Whisp Finance Assistant",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )

                if response.status_code != 200:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    logger.error(f"OpenRouter API error: {error_msg}")
                    raise LLMServiceError(f"OpenRouter API error: {error_msg}")

                data = response.json()
                return self._parse_response(data)

        except httpx.TimeoutException as e:
            logger.error(f"OpenRouter request timeout: {str(e)}")
            raise LLMServiceError(f"Request timed out: {str(e)}")

        except httpx.RequestError as e:
            logger.error(f"Network error during OpenRouter request: {str(e)}")
            raise LLMServiceError(f"Network error: {str(e)}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from OpenRouter: {str(e)}")
            raise LLMServiceError(f"Invalid response format: {str(e)}")

    async def _make_groq_request(
        self, payload: Dict[str, Any], api_key: str
    ) -> LLMResponse:
        """Make API request to Groq."""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        groq_url = "https://api.groq.com/openai/v1/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    groq_url,
                    headers=headers,
                    json=payload,
                )
                
                if response.status_code != 200:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    logger.error(f"Groq API error: {error_msg}")
                    raise LLMServiceError(f"Groq API error: {error_msg}")
                
                data = response.json()
                return self._parse_response(data)

        except httpx.TimeoutException as e:
            logger.error(f"Groq request timeout: {str(e)}")
            raise LLMServiceError(f"Groq request timed out: {str(e)}")

        except httpx.RequestError as e:
            logger.error(f"Network error during Groq request: {str(e)}")
            raise LLMServiceError(f"Groq network error: {str(e)}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from Groq: {str(e)}")
            raise LLMServiceError(f"Invalid Groq response format: {str(e)}")

    def _parse_response(self, data: Dict[str, Any]) -> LLMResponse:
        """Parse the API response into an LLMResponse object."""
        try:
            if "choices" not in data or not data["choices"]:
                raise LLMServiceError("No choices in API response")

            choice = data["choices"][0]
            message = choice.get("message", {})
            content = message.get("content", "").strip()

            # Remove special tokens that some models emit
            content = self._clean_special_tokens(content)

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
                raw_response=data,
            )

        except (KeyError, IndexError) as e:
            logger.error(f"Unexpected response format: {data}")
            raise LLMServiceError(f"Unexpected response format: {str(e)}")

    def _clean_special_tokens(self, content: str) -> str:
        """Remove special control tokens that some models emit."""
        special_tokens = [
            r'<｜begin▁of▁sentence｜>',
            r'<\|begin_of_sentence\|>',
            r'<｜end▁of▁sentence｜>',
            r'<\|end_of_sentence\|>',
            r'<｜begin▁of▁text｜>',
            r'<\|begin_of_text\|>',
            r'<｜end▁of▁text｜>',
            r'<\|end_of_text\|>',
            r'<s>',
            r'</s>',
            r'<\|im_start\|>',
            r'<\|im_end\|>',
        ]
        
        for token in special_tokens:
            content = re.sub(token, '', content)
        
        return content.strip()

    def _extract_json_from_markdown(self, content: str) -> str:
        """Extract JSON content from markdown code blocks."""
        # Check for ```json blocks
        if "```json" in content and "```" in content:
            start_marker = "```json"
            end_marker = "```"

            start_idx = content.find(start_marker)
            if start_idx != -1:
                json_start = start_idx + len(start_marker)
                if json_start < len(content) and content[json_start] == "\n":
                    json_start += 1

                end_idx = content.find(end_marker, json_start)
                if end_idx != -1:
                    json_content = content[json_start:end_idx].strip()
                    return json_content

        # Check for generic ``` blocks
        elif "```" in content:
            lines = content.split("\n")
            in_code_block = False
            json_lines = []

            for line in lines:
                if line.strip() == "```":
                    if not in_code_block:
                        in_code_block = True
                        continue
                    else:
                        break
                elif in_code_block:
                    json_lines.append(line)

            if json_lines:
                json_content = "\n".join(json_lines).strip()
                if json_content.startswith("{") and json_content.endswith("}"):
                    return json_content

        return content

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
        user_message: Optional[str] = None,
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
                conversation.append(
                    LLMMessage(role=msg["role"], content=msg["content"])
                )

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
        **kwargs,
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
            self.create_user_message(user_message),
        ]

        request = LLMRequest(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )

        return await self.chat(request)

    def get_model_info(self) -> Dict[str, Union[str, bool, int]]:
        """Get information about the current model configuration."""
        info = {
            "default_model": self.default_model,
            "base_url": self.base_url,
            "timeout": str(self.timeout),
            "use_key_rotation": self.use_key_rotation,
        }

        if self.use_key_rotation:
            info.update(
                {
                    "total_available_requests": (
                        self.api_key_manager.get_total_available_requests()
                        if self.api_key_manager
                        else 0
                    ),
                    "number_of_keys": (
                        len(self.api_key_manager._api_keys)
                        if self.api_key_manager
                        else 0
                    ),
                    "daily_limit_per_key": (
                        self.api_key_manager.daily_limit if self.api_key_manager else 0
                    ),
                }
            )
        else:
            info["api_key_configured"] = bool(self.api_key)

        return info

    def get_key_usage_info(self) -> List[Dict[str, Union[str, int, bool]]]:
        """
        Get detailed usage information for all API keys.
        Only works when key rotation is enabled.

        Returns:
            List of dictionaries with key usage information
        """
        if not self.use_key_rotation:
            return [{"error": "Key rotation is disabled"}]

        key_info = (
            self.api_key_manager.get_all_key_info() if self.api_key_manager else []
        )
        return [
            {
                "key_index": info.key_index,
                "masked_key": info.key,
                "usage_today": info.usage_today,
                "daily_limit": info.daily_limit,
                "remaining_requests": info.remaining_requests,
                "is_available": info.is_available,
            }
            for info in key_info
        ]
