from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.exceptions import AppException
from app.models.club import Club
from app.models.event import Event, EventStatus
from app.models.event_interest import EventInterest
from app.models.user import User
from app.models.team_member import TeamMember
from app.schemas.event import EventCreate, EventInterestResponse, EventPublicResponse, EventTeammateRecommendation, EventUpdate
from app.services import club_service


def _url_to_string(value: object) -> str | None:
    return str(value) if value is not None else None


def _validate_event_dates(start_date, end_date) -> None:
    if end_date < start_date:
        raise AppException("end_date must be greater than or equal to start_date", status.HTTP_422_UNPROCESSABLE_ENTITY)


def get_event(db: Session, event_id: int) -> Event:
    event = db.scalar(
        select(Event)
        .options(joinedload(Event.club))
        .where(Event.id == event_id)
    )
    if event is None:
        raise AppException("Event not found", status.HTTP_404_NOT_FOUND)
    return event


def get_public_event(db: Session, event_id: int, user: User) -> EventPublicResponse:
    event = db.scalar(
        select(Event)
        .join(Club)
        .options(joinedload(Event.club))
        .where(Event.id == event_id, Club.is_active.is_(True))
    )
    if event is None:
        raise AppException("Event not found", status.HTTP_404_NOT_FOUND)
    return build_event_response(
        event,
        user,
        get_interest_counts(db, [event.id]),
        get_user_interested_event_ids(db, user.id, [event.id]),
    )


def create_event(db: Session, club_id: int, payload: EventCreate, user: User) -> Event:
    club = club_service.get_active_club(db, club_id)
    club_service.ensure_club_member(db, club.id, user)
    event = Event(
        club_id=club.id,
        created_by=user.id,
        title=payload.title,
        description=payload.description,
        event_type=payload.event_type,
        mode=payload.mode,
        venue=payload.venue,
        start_date=payload.start_date,
        end_date=payload.end_date,
        registration_link=_url_to_string(payload.registration_link),
        image_url=_url_to_string(payload.image_url),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def _ensure_event_edit_permission(db: Session, event: Event, club_id: int, user: User) -> None:
    if event.club_id != club_id:
        raise AppException("Event not found for this club", status.HTTP_404_NOT_FOUND)
    if user.is_admin:
        return
    if club_service.is_club_member(db, club_id, user.id):
        return
    raise AppException("Only club members can edit this event", status.HTTP_403_FORBIDDEN)


def _ensure_event_delete_permission(db: Session, event: Event, club_id: int, user: User) -> None:
    if event.club_id != club_id:
        raise AppException("Event not found for this club", status.HTTP_404_NOT_FOUND)
    if user.is_admin:
        return
    if club_service.is_club_leader(db, club_id, user.id):
        return
    if event.created_by == user.id and club_service.is_club_member(db, club_id, user.id):
        return
    raise AppException("Only club leaders, event owners, or admins can delete this event", status.HTTP_403_FORBIDDEN)


def update_event(
    db: Session,
    club_id: int,
    event_id: int,
    payload: EventUpdate,
    user: User,
) -> Event:
    club_service.get_active_club(db, club_id)
    event = get_event(db, event_id)
    _ensure_event_edit_permission(db, event, club_id, user)

    values = payload.model_dump(exclude_unset=True)
    start_date = values.get("start_date", event.start_date)
    end_date = values.get("end_date", event.end_date)
    _validate_event_dates(start_date, end_date)

    for field, value in values.items():
        if field in {"registration_link", "image_url"}:
            setattr(event, field, _url_to_string(value))
        else:
            setattr(event, field, value)

    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def delete_event(db: Session, club_id: int, event_id: int, user: User) -> None:
    event = get_event(db, event_id)
    _ensure_event_delete_permission(db, event, club_id, user)
    db.delete(event)
    db.commit()


def list_public_events(db: Session, user: User) -> list[EventPublicResponse]:
    events = list(
        db.scalars(
            select(Event)
            .join(Club)
            .options(selectinload(Event.club))
            .where(Club.is_active.is_(True))
            .order_by(Event.start_date, Event.id)
        )
    )
    event_ids = [event.id for event in events]
    counts = get_interest_counts(db, event_ids)
    interested_ids = get_user_interested_event_ids(db, user.id, event_ids)
    return [build_event_response(event, user, counts, interested_ids) for event in events]


def list_interested_events(db: Session, user: User) -> list[EventPublicResponse]:
    events = list(
        db.scalars(
            select(Event)
            .join(EventInterest, EventInterest.event_id == Event.id)
            .join(Club)
            .options(selectinload(Event.club))
            .where(
                EventInterest.user_id == user.id,
                Club.is_active.is_(True),
            )
            .order_by(Event.start_date, Event.id)
        )
    )
    event_ids = [event.id for event in events]
    counts = get_interest_counts(db, event_ids)
    return [build_event_response(event, user, counts, set(event_ids)) for event in events]


def list_club_events(db: Session, club_id: int, user: User | None = None) -> list[EventPublicResponse]:
    club = club_service.get_active_club(db, club_id)
    events = list(
        db.scalars(
            select(Event)
            .options(selectinload(Event.club))
            .where(Event.club_id == club.id)
            .order_by(Event.start_date, Event.id)
        )
    )
    event_ids = [event.id for event in events]
    counts = get_interest_counts(db, event_ids)
    interested_ids = get_user_interested_event_ids(db, user.id, event_ids) if user else set()
    return [build_event_response(event, user, counts, interested_ids) for event in events]


def mark_interested(db: Session, event_id: int, user: User) -> EventInterestResponse:
    event = get_public_event_model(db, event_id)
    if event.event_status == EventStatus.finished:
        raise AppException("This event has ended", status.HTTP_400_BAD_REQUEST)
    existing = db.scalar(
        select(EventInterest).where(
            EventInterest.event_id == event.id,
            EventInterest.user_id == user.id,
        )
    )
    if existing is None:
        db.add(EventInterest(event_id=event.id, user_id=user.id))
        db.commit()
    return build_interest_response(db, event.id, True)


def remove_interest(db: Session, event_id: int, user: User) -> EventInterestResponse:
    event = get_public_event_model(db, event_id)
    existing = db.scalar(
        select(EventInterest).where(
            EventInterest.event_id == event.id,
            EventInterest.user_id == user.id,
        )
    )
    if existing is not None:
        db.delete(existing)
        db.commit()
    return build_interest_response(db, event.id, False)


def list_event_teammates(db: Session, event_id: int, user: User) -> list[EventTeammateRecommendation]:
    get_public_event_model(db, event_id)
    interested_users = list(
        db.scalars(
            select(User)
            .join(EventInterest, EventInterest.user_id == User.id)
            .options(
                selectinload(User.skill_entities),
                selectinload(User.college_ref),
                selectinload(User.branch_ref),
            )
            .where(EventInterest.event_id == event_id, User.id != user.id)
        )
    )
    current_skills = {skill.lower() for skill in user.skills}
    busy_user_ids = set(
        db.scalars(
            select(TeamMember.user_id)
            .join(TeamMember.team)
            .where(TeamMember.user_id.in_([candidate.id for candidate in interested_users]))
        )
    )
    recommendations = [
        build_teammate_recommendation(candidate, user, current_skills, candidate.id not in busy_user_ids)
        for candidate in interested_users
    ]
    return sorted(recommendations, key=lambda item: (-item.match_score, item.name.lower()))


def get_public_event_model(db: Session, event_id: int) -> Event:
    event = db.scalar(
        select(Event)
        .join(Club)
        .where(Event.id == event_id, Club.is_active.is_(True))
    )
    if event is None:
        raise AppException("Event not found", status.HTTP_404_NOT_FOUND)
    return event


def get_interest_counts(db: Session, event_ids: list[int]) -> dict[int, int]:
    if not event_ids:
        return {}
    rows = db.execute(
        select(EventInterest.event_id, func.count(EventInterest.id))
        .where(EventInterest.event_id.in_(event_ids))
        .group_by(EventInterest.event_id)
    ).all()
    return {event_id: count for event_id, count in rows}


def get_user_interested_event_ids(db: Session, user_id: int, event_ids: list[int]) -> set[int]:
    if not event_ids:
        return set()
    return set(
        db.scalars(
            select(EventInterest.event_id).where(
                EventInterest.user_id == user_id,
                EventInterest.event_id.in_(event_ids),
            )
        )
    )


def build_event_response(
    event: Event,
    user: User | None,
    counts: dict[int, int],
    interested_ids: set[int],
) -> EventPublicResponse:
    return EventPublicResponse(
        id=event.id,
        club_id=event.club_id,
        title=event.title,
        description=event.description,
        event_type=event.event_type,
        mode=event.mode,
        venue=event.venue,
        start_date=event.start_date,
        end_date=event.end_date,
        registration_link=event.registration_link,
        image_url=event.image_url,
        interested_count=counts.get(event.id, 0),
        is_interested=event.id in interested_ids,
        event_status=event.event_status,
        club=event.club,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


def build_interest_response(db: Session, event_id: int, is_interested: bool) -> EventInterestResponse:
    count = (
        db.scalar(
            select(func.count(EventInterest.id)).where(EventInterest.event_id == event_id)
        )
        or 0
    )
    return EventInterestResponse(
        event_id=event_id,
        is_interested=is_interested,
        interested_count=count,
    )


def build_teammate_recommendation(
    candidate: User,
    user: User,
    current_skills: set[str],
    available: bool,
) -> EventTeammateRecommendation:
    score = 40
    tags = ["Same event"]
    candidate_skills = candidate.skills
    complementary = [skill for skill in candidate_skills if skill.lower() not in current_skills]
    if complementary:
        score += min(25, len(complementary) * 8)
        tags.append("Complementary skills")
    if candidate.college and candidate.college == user.college:
        score += 12
        tags.append("Same college")
    if candidate.branch and candidate.branch == user.branch:
        score += 10
        tags.append("Same branch")
    if candidate.year and candidate.year == user.year:
        score += 8
        tags.append("Same year")
    if available:
        score += 10
        tags.append("Likely available")
    return EventTeammateRecommendation(
        id=candidate.id,
        name=candidate.name,
        username=candidate.username,
        college=candidate.college,
        branch=candidate.branch,
        year=candidate.year,
        skills=candidate_skills,
        profile_image_url=candidate.profile_image_url,
        match_score=min(score, 100),
        reason_tags=tags,
    )
