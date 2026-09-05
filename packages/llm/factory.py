"""LLM provider factory."""

from typing import Any

from packages.llm.base import LLMProvider
from packages.llm.providers.deepseek import DeepSeekProvider
from packages.llm.providers.mock import MockLLMProvider
from packages.llm.providers.openai_compatible import OpenAICompatibleProvider

DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"


class LLMFactory:
    @staticmethod
    def create(settings: Any) -> LLMProvider:
        provider = (getattr(settings, "llm_provider", "mock") or "mock").lower()
        model = getattr(settings, "llm_model", "") or ""

        if provider == "mock":
            return MockLLMProvider(model=model or "mock-model")
        if provider == "deepseek":
            return DeepSeekProvider(
                api_key=settings.deepseek_api_key,
                default_model=model or "deepseek-chat",
            )
        if provider == "openai":
            return OpenAICompatibleProvider(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url or DEFAULT_OPENAI_BASE_URL,
                default_model=model or "gpt-4o-mini",
            )
        if provider == "openai_compatible":
            return OpenAICompatibleProvider(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                default_model=model or "default-model",
            )
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider!r}")
