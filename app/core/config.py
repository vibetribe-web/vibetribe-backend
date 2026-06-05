import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://vibetribe-frontend-cyan.vercel.app",
]


@dataclass(frozen=True)
class Settings:
    database_url: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    cors_origins: list[str]
    admin_setup_key: str | None
    google_client_id: str | None
    google_client_secret: str | None
    google_redirect_uri: str
    frontend_auth_success_url: str | None
    supabase_url: str | None
    supabase_service_role_key: str | None


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _parse_origins(value: str | None) -> list[str]:
    if not value:
        return DEFAULT_CORS_ORIGINS

    origins = [
        origin.strip().rstrip("/")
        for origin in value.split(",")
        if origin.strip() and origin.strip() != "*"
    ]
    for origin in DEFAULT_CORS_ORIGINS:
        if origin not in origins:
            origins.append(origin)
    return origins


@lru_cache
def get_settings() -> Settings:
    return Settings(
        database_url=_required_env("DATABASE_URL"),
        secret_key=_required_env("SECRET_KEY"),
        algorithm=os.getenv("ALGORITHM", "HS256"),
        access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
        cors_origins=_parse_origins(os.getenv("CORS_ORIGINS")),
        admin_setup_key=os.getenv("ADMIN_SETUP_KEY"),
        google_client_id=os.getenv("GOOGLE_CLIENT_ID"),
        google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        google_redirect_uri=os.getenv(
            "GOOGLE_REDIRECT_URI",
            "http://127.0.0.1:8000/api/v1/auth/google/callback",
        ),
        frontend_auth_success_url=os.getenv("FRONTEND_AUTH_SUCCESS_URL"),
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    )


settings = get_settings()
