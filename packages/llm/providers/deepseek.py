"""DeepSeek provider (OpenAI-compatible API)."""

from packages.llm.providers.openai_compatible import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        default_model: str = "deepseek-chat",
        timeout: float = 60.0,
    ):
        if not api_key:
            raise ValueError(
                "DeepSeekProvider requires an API key (set AGENTOS_DEEPSEEK_API_KEY)"
            )
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            default_model=default_model,
            timeout=timeout,
        )
