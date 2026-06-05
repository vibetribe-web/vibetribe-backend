import logging
from urllib.parse import urlencode

from authlib.integrations.base_client.errors import MismatchingStateError
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppException
from app.db.database import get_db
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserLogin, UserRead
from app.services import auth_service, google_auth_service

router = APIRouter()
oauth = OAuth()
logger = logging.getLogger(__name__)

if settings.google_client_id and settings.google_client_secret:
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


def _ensure_google_oauth_configured() -> None:
    if not settings.google_client_id or not settings.google_client_secret:
        raise AppException("Google OAuth is not configured", status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    return auth_service.register_user(db, payload)


@router.post("/login", response_model=Token)
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    user = auth_service.authenticate_user(db, form_data.username, form_data.password)
    return auth_service.create_login_token(user)


@router.post("/login/json", response_model=Token)
def login_user_json(payload: UserLogin, db: Session = Depends(get_db)) -> Token:
    return auth_service.login_user(db, payload)


@router.get("/google/login")
async def google_login(request: Request):
    _ensure_google_oauth_configured()
    logger.info("Google OAuth login route reached redirect_uri=%s", settings.google_redirect_uri)
    return await oauth.google.authorize_redirect(
        request,
        redirect_uri=settings.google_redirect_uri,
    )


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    _ensure_google_oauth_configured()
    logger.info("Google OAuth callback reached")

    try:
        token = await oauth.google.authorize_access_token(request)
    except MismatchingStateError:
        logger.warning("Google OAuth state mismatch")
        if settings.frontend_auth_success_url:
            auth_url = settings.frontend_auth_success_url.rsplit("/", 1)[0]
            return RedirectResponse(f"{auth_url}?oauth_error=state")
        raise AppException("Google sign-in expired. Please try again.", status.HTTP_400_BAD_REQUEST)

    user_info = token.get("userinfo")
    if user_info is None:
        user_info = await oauth.google.userinfo(token=token)

    user_email = user_info.get("email")
    if user_email:
        logger.info("Google OAuth user email received email=%s", user_email)
    auth_response = google_auth_service.login_or_create_google_user(db, dict(user_info))
    if settings.frontend_auth_success_url:
        query = urlencode(
            {
                "access_token": auth_response.access_token,
                "token_type": auth_response.token_type,
            }
        )
        return RedirectResponse(f"{settings.frontend_auth_success_url}?{query}")
    return auth_response
