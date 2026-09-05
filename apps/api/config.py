"""Application settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="AGENTOS_")

    app_name: str = "AgentOS Studio"
    database_url: str = "sqlite+aiosqlite:///./data/agentos.db"
    log_level: str = "INFO"
    llm_provider: str = "mock"  # mock | deepseek | openai | openai_compatible
    llm_model: str = "mock-model"
    deepseek_api_key: str = ""
    openai_api_key: str = ""
    openai_base_url: str = ""


settings = Settings()
