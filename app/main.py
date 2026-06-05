from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1.routes import admin, auth, clubs, events, match, recommendations, requests, teams, users
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestLoggingMiddleware

configure_logging()

app = FastAPI(
    title="VibeTribe API",
    description="Smart collaboration platform for student teams.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://vibetribe.vercel.app",
        "https://vibetribe-two.vercel.app",
        "https://*.vercel.app",
    ],
    allow_origin_regex=r"^https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    same_site="lax",
    https_only=False,
)
app.add_middleware(RequestLoggingMiddleware)
register_exception_handlers(app)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "VibeTribe API running"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(teams.router, prefix="/api/v1/teams", tags=["Teams"])
app.include_router(clubs.router, prefix="/api/v1/clubs", tags=["Clubs"])
app.include_router(events.router, prefix="/api/v1/events", tags=["Events"])
app.include_router(requests.router, prefix="/api/v1/requests", tags=["Requests"])
app.include_router(recommendations.router, prefix="/api/v1/recommendations", tags=["Recommendations"])
app.include_router(recommendations.router, prefix="/recommendations", tags=["Recommendations"])
app.include_router(match.router, prefix="/match", tags=["Matching"])
