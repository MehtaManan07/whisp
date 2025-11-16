import json
import logging
import re
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass

from app.core.config import config
from app.core.exceptions import LLMServiceError
from app.core.fetcher import fetch

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
    """Service for making LLM calls via Gemini and Groq APIs."""

    def __init__(
        self,
        api_key_manager: Optional[Any] = None,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """Initialize the LLM service."""
        self.api_key = api_key or config.gemini_key
        self.default_model = model_name or config.gemini_model_name
        self.timeout = timeout

        if not self.api_key:
            logger.warning("Gemini API key not configured")

    async def complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        """Simple completion interface for single prompt requests."""
        print(prompt)
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
        """Main chat interface supporting conversation history using Gemini."""
        if not self.api_key:
            raise LLMServiceError("Gemini API key not configured")

        # Build payload
        payload, model = self._build_gemini_payload(request)

        # Make the request
        return await self._make_gemini_request(payload, model)

    async def complete_with_groq(
        self,
        prompt: str,
        model: str = "llama-3.3-70b-versatile",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        """Use Groq API for fast inference with Llama models."""
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
        """Chat interface using Groq API."""
        groq_api_key = config.groq_api_key
        if not groq_api_key:
            raise LLMServiceError(
                "Groq API key not configured. Set GROQ_API_KEY in .env"
            )

        # Build payload
        payload = self._build_payload(request, default_model="llama-3.3-70b-versatile")

        # Make the request
        return await self._make_groq_request(payload, groq_api_key)

    def _build_payload(
        self, request: LLMRequest, default_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Build API payload from request (for Groq)."""
        model = request.model or default_model or "llama-3.3-70b-versatile"

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

    def _build_gemini_payload(
        self, request: LLMRequest, default_model: Optional[str] = None
    ) -> tuple[Dict[str, Any], str]:
        """Build Gemini API payload from request."""
        model = request.model or default_model or self.default_model

        # Convert messages to Gemini format
        contents = []
        system_instruction = None
        
        for msg in request.messages:
            if msg.role == "system":
                system_instruction = msg.content
            else:
                # Gemini uses "user" and "model" roles (not "assistant")
                role = "user" if msg.role == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg.content}]
                })

        payload: Dict[str, Any] = {
            "contents": contents
        }

        # Add system instruction if present
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        # Add generation config
        generation_config: Dict[str, Any] = {}
        if request.max_tokens is not None:
            generation_config["maxOutputTokens"] = request.max_tokens
        if request.temperature is not None:
            generation_config["temperature"] = request.temperature
        if request.top_p is not None:
            generation_config["topP"] = request.top_p
        
        if generation_config:
            payload["generationConfig"] = generation_config

        return payload, model

    async def _make_gemini_request(
        self, payload: Dict[str, Any], model: str
    ) -> LLMResponse:
        """Make API request to Gemini."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
        
        headers = {
            "Content-Type": "application/json",
        }

        try:
            data = await fetch(
                url,
                model=None,
                method="POST",
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            
            if data is None:
                raise LLMServiceError("Gemini API returned no response")
            
            return self._parse_gemini_response(data)

        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            raise LLMServiceError(f"Gemini API error: {str(e)}")

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
            data = await fetch(
                groq_url,
                model=None,
                method="POST",
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            
            if data is None:
                raise LLMServiceError("Groq API returned no response")
            
            return self._parse_response(data)

        except Exception as e:
            logger.error(f"Groq API error: {str(e)}")
            raise LLMServiceError(f"Groq API error: {str(e)}")

    def _parse_gemini_response(self, data: Dict[str, Any]) -> LLMResponse:
        """Parse the Gemini API response into an LLMResponse object."""
        try:
            if "candidates" not in data or not data["candidates"]:
                raise LLMServiceError("No candidates in Gemini API response")

            candidate = data["candidates"][0]
            content_parts = candidate.get("content", {}).get("parts", [])
            
            if not content_parts:
                raise LLMServiceError("No content parts in Gemini response")

            content = content_parts[0].get("text", "").strip()

            # Remove special tokens that some models emit
            content = self._clean_special_tokens(content)

            if not content:
                logger.warning("Empty content in LLM response")
                content = "I apologize, but I couldn't generate a proper response. Please try again."

            # Extract JSON from markdown code blocks if present
            processed_content = self._extract_json_from_markdown(content)

            # Extract usage info if available
            usage = None
            if "usageMetadata" in data:
                usage_meta = data["usageMetadata"]
                usage = {
                    "prompt_tokens": usage_meta.get("promptTokenCount", 0),
                    "completion_tokens": usage_meta.get("candidatesTokenCount", 0),
                    "total_tokens": usage_meta.get("totalTokenCount", 0),
                }

            finish_reason = candidate.get("finishReason", "STOP")
            # Map Gemini finish reasons to standard ones
            if finish_reason == "STOP":
                finish_reason = "stop"
            elif finish_reason == "MAX_TOKENS":
                finish_reason = "length"

            return LLMResponse(
                content=processed_content,
                usage=usage,
                model=data.get("model", self.default_model),
                finish_reason=finish_reason,
                raw_response=data,
            )

        except (KeyError, IndexError) as e:
            logger.error(f"Unexpected Gemini response format: {data}")
            raise LLMServiceError(f"Unexpected Gemini response format: {str(e)}")

    def _parse_response(self, data: Dict[str, Any]) -> LLMResponse:
        """Parse the API response into an LLMResponse object (for Groq)."""
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
            r"<｜begin▁of▁sentence｜>",
            r"<\|begin_of_sentence\|>",
            r"<｜end▁of▁sentence｜>",
            r"<\|end_of_sentence\|>",
            r"<｜begin▁of▁text｜>",
            r"<\|begin_of_text\|>",
            r"<｜end▁of▁text｜>",
            r"<\|end_of_text\|>",
            r"<s>",
            r"</s>",
            r"<\|im_start\|>",
            r"<\|im_end\|>",
        ]

        for token in special_tokens:
            content = re.sub(token, "", content)

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
        """Build a conversation with system prompt and message history."""
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
        """Generate response with system prompt and user message."""
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
            "timeout": str(self.timeout),
            "api_key_configured": bool(self.api_key),
        }
        return info
