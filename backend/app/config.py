from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    paypal_client_id: str
    paypal_client_secret: str
    paypal_base_url: str = "https://api-m.sandbox.paypal.com"

    mongodb_uri: str = Field(
        validation_alias=AliasChoices("MONGODB_URI", "MONGO_URI")
    )
    mongodb_db: str = "dhanrakshak"

    groq_api_key: str
    groq_model: str = "openai/gpt-oss-120b"

    cors_origins: str = "http://localhost:3000"
    enable_dev_endpoints: bool = False
    auto_score_on_sync: bool = False
    risk_llm_timeout_seconds: float = 20.0
    dispute_submission_mode: Literal["paypal", "prepared"] = "paypal"
    merchant_research_mode: Literal["live", "fixture"] = "live"
    search_provider: Literal["none"] = "none"
    search_api_key: str | None = None
    merchant_cache_hours: int = 24
    merchant_unknown_confidence_floor: float = 0.3

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()