from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Taste Travel API", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    debug: bool = Field(default=True, alias="APP_DEBUG")
    database_url: str = Field(
        default="sqlite:///./test.db",
        alias="DATABASE_URL",
    )
    default_user_email: str = Field(
        default="demo@tastetravel.app",
        alias="DEFAULT_USER_EMAIL",
    )
    default_user_name: str = Field(
        default="Demo Traveler",
        alias="DEFAULT_USER_NAME",
    )
    google_places_api_key: str | None = Field(default=None, alias="GOOGLE_PLACES_API_KEY")
    google_places_base_url: str = Field(
        default="https://maps.googleapis.com/maps/api/place/nearbysearch/json",
        alias="GOOGLE_PLACES_BASE_URL",
    )
    google_places_text_search_base_url: str = Field(
        default="https://maps.googleapis.com/maps/api/place/textsearch/json",
        alias="GOOGLE_PLACES_TEXT_SEARCH_BASE_URL",
    )
    google_geocoding_base_url: str = Field(
        default="https://maps.googleapis.com/maps/api/geocode/json",
        alias="GOOGLE_GEOCODING_BASE_URL",
    )
    google_places_timeout_seconds: float = Field(default=8.0, alias="GOOGLE_PLACES_TIMEOUT_SECONDS")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-5-mini", alias="OPENAI_MODEL")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    openai_timeout_seconds: float = Field(default=15.0, alias="OPENAI_TIMEOUT_SECONDS")
    backend_cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        alias="BACKEND_CORS_ORIGINS",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url.startswith("postgres://"):
            return self.database_url.replace("postgres://", "postgresql+psycopg://", 1)
        if self.database_url.startswith("postgresql://") and "+psycopg" not in self.database_url:
            return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return self.database_url

    @property
    def is_sqlite(self) -> bool:
        return self.sqlalchemy_database_url.startswith("sqlite")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"prod", "production"}

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
