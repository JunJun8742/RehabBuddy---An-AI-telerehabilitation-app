from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://rehab:rehab@localhost:5432/rehabbuddy"
    test_database_url: str = "postgresql+psycopg://rehab:rehab@localhost:5432/rehabbuddy_test"
    jwt_secret: str = "dev-secret-change-me"
    jwt_expire_minutes: int = 60 * 24
    cors_origins: list[str] = ["http://localhost:5173"]
    anthropic_api_key: str | None = None
    # rehabbuddy/backend/app/core/config.py -> parents[3] is rehabbuddy/
    shared_dir: Path = Path(__file__).resolve().parents[3] / "shared"


settings = Settings()
