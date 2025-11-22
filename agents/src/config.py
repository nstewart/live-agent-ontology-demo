"""Agent configuration."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Agent settings loaded from environment variables."""

    # API
    agent_api_base: str = "http://api:8080"

    # Materialize
    mz_host: str = "mz"
    mz_port: int = 5432
    mz_user: str = "materialize"
    mz_password: str = "materialize"
    mz_database: str = "materialize"

    # OpenSearch
    agent_os_base: str = "http://opensearch:9200"

    # LLM
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    model_name: str = "gpt-4-turbo-preview"

    # Logging
    log_level: str = "INFO"

    @property
    def mz_dsn(self) -> str:
        """Get Materialize connection string."""
        return f"postgresql+asyncpg://{self.mz_user}:{self.mz_password}@{self.mz_host}:{self.mz_port}/{self.mz_database}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
