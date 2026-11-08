"""Application settings, read from environment variables only (no secrets in source)."""
import logging
import os
import secrets
from dataclasses import dataclass, field

log = logging.getLogger("app.config")


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    env: str = "development"
    database_url: str = "sqlite:///./app.db"
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 480
    cors_origins: list[str] = field(default_factory=list)
    seed_demo_data: bool = True
    # LLM: provider is "none" | "openai" | "anthropic"
    llm_provider: str = "none"
    llm_api_key: str | None = None
    llm_model: str = ""
    llm_base_url: str | None = None
    llm_timeout_seconds: float = 12.0
    login_max_failures: int = 5
    login_lockout_seconds: int = 60


def load_settings() -> Settings:
    secret = os.getenv("JWT_SECRET", "").strip()
    if not secret:
        # Development convenience only: a random per-process secret (sessions reset on restart).
        secret = secrets.token_urlsafe(48)
        log.warning("JWT_SECRET is not set; using a random per-process secret. Set it for any shared deployment.")
    origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
    return Settings(
        env=os.getenv("APP_ENV", "development"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./app.db"),
        jwt_secret=secret,
        access_token_minutes=int(os.getenv("ACCESS_TOKEN_MINUTES", "480")),
        cors_origins=origins,
        seed_demo_data=_bool("SEED_DEMO_DATA", True),
        llm_provider=os.getenv("LLM_PROVIDER", "none").strip().lower(),
        llm_api_key=os.getenv("LLM_API_KEY") or None,
        llm_model=os.getenv("LLM_MODEL", "").strip(),
        llm_base_url=os.getenv("LLM_BASE_URL") or None,
        llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "12")),
        login_max_failures=int(os.getenv("LOGIN_MAX_FAILURES", "5")),
        login_lockout_seconds=int(os.getenv("LOGIN_LOCKOUT_SECONDS", "60")),
    )


settings = load_settings()
