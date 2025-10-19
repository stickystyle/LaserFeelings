# ABOUTME: Configuration settings for the AI TTRPG Player System using Pydantic Settings.
# ABOUTME: Loads all environment variables and provides type-safe configuration access.

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables"""

    # OpenAI API Configuration
    openai_api_key: str = Field(
        description="OpenAI API key for GPT-4o access"
    )
    openai_model: str = Field(
        default="gpt-4o",
        description="OpenAI model to use for agent intelligence"
    )

    # Neo4j Configuration
    neo4j_uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j connection URI"
    )
    neo4j_user: str = Field(
        default="neo4j",
        description="Neo4j username"
    )
    neo4j_password: str = Field(
        description="Neo4j password"
    )

    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL"
    )

    # RQ Worker Configuration
    rq_worker_timeout: int = Field(
        default=300,
        description="RQ worker timeout in seconds"
    )
    rq_worker_max_jobs: int = Field(
        default=100,
        description="Maximum jobs per worker"
    )

    # LangSmith Tracing (Optional)
    langsmith_api_key: str | None = Field(
        default=None,
        description="LangSmith API key for tracing"
    )
    langsmith_project: str = Field(
        default="ttrpg-ai",
        description="LangSmith project name"
    )
    langchain_tracing_v2: bool = Field(
        default=False,
        description="Enable LangChain tracing v2"
    )
    langchain_endpoint: str = Field(
        default="https://api.smith.langchain.com",
        description="LangChain API endpoint"
    )

    # Application Settings
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    turn_timeout_seconds: int = Field(
        default=60,
        description="Maximum seconds for a single turn phase"
    )
    max_validation_attempts: int = Field(
        default=3,
        description="Maximum validation retries for character actions"
    )
    memory_corruption_enabled: bool = Field(
        default=False,
        description="Enable memory corruption simulation"
    )

    # Performance Settings
    max_context_tokens: int = Field(
        default=5000,
        description="Maximum tokens for LLM context"
    )
    memory_query_timeout: int = Field(
        default=2,
        description="Timeout for memory queries in seconds"
    )
    llm_retry_attempts: int = Field(
        default=5,
        description="Number of retry attempts for LLM API calls"
    )
    llm_retry_backoff_seconds: str = Field(
        default="2,5,10",
        description="Backoff intervals for LLM retries (comma-separated)"
    )

    # Game Session Settings
    max_concurrent_players: int = Field(
        default=4,
        description="Maximum number of concurrent AI players"
    )
    turns_per_session: int = Field(
        default=100,
        description="Maximum turns per session"
    )
    auto_save_interval_turns: int = Field(
        default=10,
        description="Auto-save game state every N turns"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @property
    def llm_retry_backoff_list(self) -> list[int]:
        """Parse comma-separated backoff intervals into list of integers"""
        return [int(x.strip()) for x in self.llm_retry_backoff_seconds.split(",")]


# Singleton settings instance - lazy initialization to allow import without .env
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create the singleton settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
