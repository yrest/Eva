"""LLM router for OpenAI-compatible backends."""

import json
from typing import Any, Dict, List, Literal, Optional

import httpx
from anthropic import Anthropic
from openai import AsyncOpenAI

from .config import settings


class LLMRouter:
    """Route LLM requests to appropriate backend (LM Studio, OpenAI, Anthropic)."""

    def __init__(
        self,
        backend: Optional[Literal["lmstudio", "openai", "anthropic"]] = None,
        model: Optional[str] = None,
    ):
        """Initialize LLM router.

        Args:
            backend: LLM backend to use (defaults to config)
            model: Model name/ID (defaults to backend default)
        """
        self.backend = backend or settings.default_llm_backend
        self.model = model or self._get_default_model()

        # Initialize clients
        self._openai_client: Optional[AsyncOpenAI] = None
        self._anthropic_client: Optional[Anthropic] = None

    def _get_default_model(self) -> str:
        """Get default model for current backend."""
        models = {
            "lmstudio": settings.default_lmstudio_model,
            "openai": settings.default_openai_model,
            "anthropic": settings.default_anthropic_model,
        }
        return models[self.backend]

    async def _get_openai_client(self) -> AsyncOpenAI:
        """Get or create OpenAI client (works for OpenAI and LM Studio)."""
        if self._openai_client is None:
            if self.backend == "lmstudio":
                self._openai_client = AsyncOpenAI(
                    base_url=settings.lmstudio_url + "/v1",
                    api_key=settings.lmstudio_api_key,
                    timeout=settings.llm_timeout,
                )
            else:  # openai
                self._openai_client = AsyncOpenAI(
                    api_key=settings.openai_api_key,
                    timeout=settings.llm_timeout,
                )
        return self._openai_client

    def _get_anthropic_client(self) -> Anthropic:
        """Get or create Anthropic client."""
        if self._anthropic_client is None:
            self._anthropic_client = Anthropic(
                api_key=settings.anthropic_api_key,
                timeout=settings.llm_timeout,
            )
        return self._anthropic_client

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> Dict[str, Any]:
        """
        Send chat completion request to LLM.

        Args:
            messages: Conversation messages
            tools: Available tools (OpenAI format)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Response with message and optional tool calls
        """
        if self.backend in ["lmstudio", "openai"]:
            return await self._openai_chat_completion(
                messages, tools, temperature, max_tokens
            )
        elif self.backend == "anthropic":
            return await self._anthropic_chat_completion(
                messages, tools, temperature, max_tokens
            )
        else:
            raise ValueError(f"Unsupported backend: {self.backend}")

    async def _openai_chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]],
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """OpenAI-compatible chat completion (OpenAI, LM Studio)."""
        client = await self._get_openai_client()

        # Build request params
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        # Make request
        response = await client.chat.completions.create(**params)

        # Extract message
        choice = response.choices[0]
        message = choice.message

        # Build response
        result = {
            "role": message.role,
            "content": message.content or "",
            "tool_calls": [],
        }

        # Extract tool calls if present
        if hasattr(message, "tool_calls") and message.tool_calls:
            for tool_call in message.tool_calls:
                result["tool_calls"].append({
                    "id": tool_call.id,
                    "type": tool_call.type,
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                })

        return result

    async def _anthropic_chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]],
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """Anthropic chat completion."""
        client = self._get_anthropic_client()

        # Convert OpenAI format to Anthropic format
        # Extract system message if present
        system_message = None
        anthropic_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })

        # Convert tools to Anthropic format
        anthropic_tools = None
        if tools:
            anthropic_tools = []
            for tool in tools:
                anthropic_tools.append({
                    "name": tool["function"]["name"],
                    "description": tool["function"]["description"],
                    "input_schema": tool["function"]["parameters"],
                })

        # Build request params
        params = {
            "model": self.model,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if system_message:
            params["system"] = system_message

        if anthropic_tools:
            params["tools"] = anthropic_tools

        # Make request
        response = client.messages.create(**params)

        # Build result
        result = {
            "role": "assistant",
            "content": "",
            "tool_calls": [],
        }

        # Extract content and tool calls
        for block in response.content:
            if block.type == "text":
                result["content"] += block.text
            elif block.type == "tool_use":
                result["tool_calls"].append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.input),
                    },
                })

        return result

    async def health_check(self) -> bool:
        """Check if LLM backend is available."""
        try:
            if self.backend == "lmstudio":
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{settings.lmstudio_url}/v1/models",
                        timeout=5.0,
                    )
                    return response.status_code == 200

            elif self.backend == "openai":
                client = await self._get_openai_client()
                models = await client.models.list()
                return len(models.data) > 0

            elif self.backend == "anthropic":
                # Anthropic doesn't have a health endpoint, try a minimal request
                client = self._get_anthropic_client()
                response = client.messages.create(
                    model=self.model,
                    max_tokens=1,
                    messages=[{"role": "user", "content": "test"}],
                )
                return response is not None

        except Exception:
            return False

        return False
