from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import AppException
from app.models.event import Event, EventStatus
from app.models.team_message import TeamMessage, TeamMessageType
from app.models.user import User
from app.schemas.team_message import (
    TeamEventShareCreate,
    TeamMessageCreate,
    TeamMessageEventRead,
    TeamMessagePage,
    TeamMessageRead,
    TeamMessageSenderRead,
)
from app.services import team_service


def ensure_team_member(db: Session, team_id: int, user: User) -> None:
    team_service.get_team(db, team_id)
    if not team_service.is_team_member(db, team_id, user.id):
        raise AppException("Only team members can access team conversations", status.HTTP_403_FORBIDDEN)


def list_messages(
    db: Session,
    team_id: int,
    user: User,
    limit: int = 50,
    before_id: int | None = None,
) -> TeamMessagePage:
    ensure_team_member(db, team_id, user)
    query = (
        select(TeamMessage)
        .where(TeamMessage.team_id == team_id)
        .options(
            joinedload(TeamMessage.sender),
            joinedload(TeamMessage.event).joinedload(Event.club),
        )
        .order_by(TeamMessage.id.desc())
        .limit(limit + 1)
    )
    if before_id is not None:
        query = query.where(TeamMessage.id < before_id)

    messages = list(db.scalars(query))
    has_more = len(messages) > limit
    page_messages = messages[:limit]
    page_messages.reverse()
    return TeamMessagePage(
        items=[build_message_response(message) for message in page_messages],
        has_more=has_more,
        next_before_id=page_messages[0].id if has_more and page_messages else None,
    )


def create_text_message(
    db: Session,
    team_id: int,
    payload: TeamMessageCreate,
    user: User,
) -> TeamMessageRead:
    ensure_team_member(db, team_id, user)
    message = TeamMessage(
        team_id=team_id,
        sender_id=user.id,
        message_type=TeamMessageType.text,
        content=payload.content,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return get_message_response(db, message.id)


def share_event(
    db: Session,
    team_id: int,
    payload: TeamEventShareCreate,
    user: User,
) -> TeamMessageRead:
    ensure_team_member(db, team_id, user)
    event = db.get(Event, payload.event_id)
    if event is None:
        raise AppException("Event not found", status.HTTP_404_NOT_FOUND)
    if event.event_status == EventStatus.finished:
        raise AppException("This event has ended", status.HTTP_400_BAD_REQUEST)

    message = TeamMessage(
        team_id=team_id,
        sender_id=user.id,
        message_type=TeamMessageType.event_share,
        content=payload.content,
        shared_event_id=event.id,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return get_message_response(db, message.id)


def get_message_response(db: Session, message_id: int) -> TeamMessageRead:
    message = db.scalar(
        select(TeamMessage)
        .where(TeamMessage.id == message_id)
        .options(
            joinedload(TeamMessage.sender),
            joinedload(TeamMessage.event).joinedload(Event.club),
        )
    )
    if message is None:
        raise AppException("Message not found", status.HTTP_404_NOT_FOUND)
    return build_message_response(message)


def build_message_response(message: TeamMessage) -> TeamMessageRead:
    event = None
    if message.event is not None:
        event = TeamMessageEventRead(
            id=message.event.id,
            title=message.event.title,
            event_type=message.event.event_type,
            mode=message.event.mode,
            start_date=message.event.start_date,
            end_date=message.event.end_date,
            image_url=message.event.image_url,
            venue=message.event.venue,
            description=message.event.description,
            club_id=message.event.club_id,
            club_name=message.event.club.name if message.event.club else "Unknown club",
            event_status=message.event.event_status,
        )

    return TeamMessageRead(
        id=message.id,
        team_id=message.team_id,
        shared_event_id=message.shared_event_id,
        sender=TeamMessageSenderRead.model_validate(message.sender),
        message_type=message.message_type,
        content=message.content,
        event=event,
        created_at=message.created_at,
    )
