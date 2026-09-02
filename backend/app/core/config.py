from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# backend/app/core/config.py
# parents[2] resolves to the backend directory.
BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    # Existing application settings
    openai_api_key: str
    database_url: str = "postgresql://username:password@localhost:5432/repopilot"
    environment: str = "development"

    # AWS / Cognito authentication
    aws_region: str = "us-east-2"
    cognito_user_pool_id: str
    cognito_app_client_id: str

    # DynamoDB repository ownership metadata
    repository_table_name: str = "RepoPilotRepositories"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings():
    return Settings()