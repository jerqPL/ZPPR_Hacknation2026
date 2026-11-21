from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Zasiłkowy Przewodnik Przyszłego Rodzica (ZPPR) API"
    app_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    data_dir: Path = Path(__file__).resolve().parent.parent / "data"
    admin_api_key: str = "zppr-admin-2026"

    model_config = SettingsConfigDict(env_prefix="ZPPR_")


settings = Settings()
