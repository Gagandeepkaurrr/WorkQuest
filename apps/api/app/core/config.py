from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from cryptography.fernet import Fernet
from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[4] / ".env", extra="ignore"
    )
    app_env: Literal["local", "test", "staging", "production"] = "local"
    app_origin: str = "http://localhost:5173"
    backend_hostname: str = Field(
        default="",
        validation_alias=AliasChoices(
            "BACKEND_HOSTNAME", "RENDER_EXTERNAL_HOSTNAME", "backend_hostname"
        ),
    )
    database_url: SecretStr
    redis_url: SecretStr = SecretStr("redis://localhost:56379/0")
    redis_namespace: str = "workquest"
    delivery_payload_encryption_key: SecretStr
    delivery_key_version: str = "1"
    session_secret: SecretStr
    session_max_age_seconds: int = 604800
    public_signup_enabled: bool = True
    email_verification_required: bool = True
    smtp_host: str = "localhost"
    smtp_port: int = 51025
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_from: str = "practice@workquest.local"
    smtp_tls: Literal["none", "starttls", "tls"] = "none"
    ai_provider: Literal["mock", "gemini"] = "mock"
    ai_model: str = "gemini-3.8-flash"
    gemini_api_key: SecretStr = SecretStr("")
    ai_timeout_seconds: int = Field(default=45, ge=5, le=45)
    ai_prompt_version: str = "character-v1"
    ai_user_daily_request_limit: int = 100
    ai_global_daily_request_limit: int = 1000
    ai_global_daily_token_limit: int = 6_800_000
    ai_branch_request_limit: int = 20
    demo_enabled: bool = True
    demo_ttl_seconds: int = 7200
    public_mock_demo: bool = False
    metrics_token: SecretStr = SecretStr("")
    job_lease_seconds: int = Field(default=60, ge=60, le=300)
    job_max_attempts: int = Field(default=3, ge=1, le=3)
    job_max_age_seconds: int = Field(default=600, ge=60, le=600)

    @model_validator(mode="after")
    def validate_environment(self):
        Fernet(self.delivery_payload_encryption_key.get_secret_value().encode())
        if len(self.session_secret.get_secret_value()) < 32:
            raise ValueError("SESSION_SECRET must contain at least 32 characters")
        database = self.database_url.get_secret_value()
        if database.startswith(("postgresql://", "postgres://")):
            self.database_url = SecretStr("postgresql+psycopg://" + database.split("://", 1)[1])
        if self.backend_hostname and (
            "*" in self.backend_hostname
            or "/" in self.backend_hostname
            or ":" in self.backend_hostname
        ):
            raise ValueError("BACKEND_HOSTNAME must be one exact hostname")
        if not self.database_url.get_secret_value().startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must use PostgreSQL with psycopg")
        if not 60 <= self.session_max_age_seconds <= 604800:
            raise ValueError("Session lifetime must be between 60 seconds and seven days")
        origin = urlparse(self.app_origin)
        if origin.path not in ("", "/") or not origin.netloc:
            raise ValueError("APP_ORIGIN must be an origin without a path")
        if self.app_env in ("staging", "production"):
            if origin.scheme != "https" or origin.hostname in ("localhost", "127.0.0.1"):
                raise ValueError("Production requires a public HTTPS origin")
            if self.demo_enabled or not self.email_verification_required:
                raise ValueError("Production must disable guests and require verified email")
            if self.ai_provider == "mock" and not self.public_mock_demo:
                raise ValueError("Public mock mode requires explicit PUBLIC_MOCK_DEMO")
            if self.smtp_tls == "none" or not self.metrics_token.get_secret_value():
                raise ValueError("Production requires SMTP TLS and a metrics token")
        if self.ai_provider == "gemini" and (
            not self.ai_model or not self.gemini_api_key.get_secret_value()
        ):
            raise ValueError("Gemini requires an explicit model and API key")
        return self

    @property
    def secure(self) -> bool:
        return self.app_env in ("staging", "production")

    @property
    def cookie_name(self) -> str:
        return "__Host-wq_session" if self.secure else "wq_local_session"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
