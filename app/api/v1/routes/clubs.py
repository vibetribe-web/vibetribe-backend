from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, get_optional_current_user
from app.db.database import get_db
from app.models.event import Event
from app.models.user import User
from app.schemas.club import ClubMemberActionResponse, ClubMemberResponse, ClubPublicResponse
from app.schemas.event import EventCreate, EventPosterUploadResponse, EventPublicResponse, EventUpdate
from app.services import club_service, event_service, storage_service

router = APIRouter()


@router.get("/", response_model=list[ClubPublicResponse])
def list_clubs(db: Session = Depends(get_db)) -> list[ClubPublicResponse]:
    return club_service.list_active_clubs(db)


@router.get("/{club_id}", response_model=ClubPublicResponse)
def get_club(club_id: int, db: Session = Depends(get_db)) -> ClubPublicResponse:
    return club_service.get_public_club(db, club_id)


@router.post("/{club_id}/members/{user_id}", response_model=ClubMemberActionResponse)
def add_member(
    club_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClubMemberActionResponse:
    return club_service.add_member(db, club_id, user_id, current_user)


@router.delete("/{club_id}/members/{user_id}", response_model=ClubMemberActionResponse)
def remove_member(
    club_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClubMemberActionResponse:
    return club_service.remove_member(db, club_id, user_id, current_user)


@router.post("/{club_id}/members/{user_id}/promote", response_model=ClubMemberActionResponse)
def promote_member(
    club_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClubMemberActionResponse:
    return club_service.promote_member(db, club_id, user_id, current_user)


@router.post("/{club_id}/members/{user_id}/demote", response_model=ClubMemberActionResponse)
def demote_leader(
    club_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClubMemberActionResponse:
    return club_service.demote_leader(db, club_id, user_id, current_user)


@router.get("/{club_id}/members", response_model=list[ClubMemberResponse])
def list_members(
    club_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ClubMemberResponse]:
    return club_service.list_club_members(db, club_id, current_user)


@router.get("/{club_id}/events", response_model=list[EventPublicResponse])
def list_club_events(
    club_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> list[EventPublicResponse]:
    return event_service.list_club_events(db, club_id, current_user)


@router.post("/{club_id}/event-poster-upload", response_model=EventPosterUploadResponse)
async def upload_event_poster(
    club_id: int,
    poster: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EventPosterUploadResponse:
    club = club_service.get_active_club(db, club_id)
    club_service.ensure_club_member(db, club.id, current_user)
    return await storage_service.upload_event_poster(club.id, poster)


@router.post(
    "/{club_id}/events",
    response_model=EventPublicResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_event(
    club_id: int,
    payload: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Event:
    return event_service.create_event(db, club_id, payload, current_user)


@router.put("/{club_id}/events/{event_id}", response_model=EventPublicResponse)
def update_event(
    club_id: int,
    event_id: int,
    payload: EventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Event:
    return event_service.update_event(db, club_id, event_id, payload, current_user)


@router.delete("/{club_id}/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    club_id: int,
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    event_service.delete_event(db, club_id, event_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
