from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import AppException
from app.models.club import Club
from app.models.club_member import ClubMember, ClubMemberRole
from app.models.user import User
from app.schemas.club import (
    ClubAdminResponse,
    ClubCreate,
    ClubLeaderAssignmentResponse,
    ClubLeaderResponse,
    ClubMemberActionResponse,
    ClubMemberResponse,
    ClubPublicResponse,
    ClubUpdate,
)


def _normalize_name(name: str) -> str:
    return name.strip()


def _get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise AppException("User not found", status.HTTP_404_NOT_FOUND)
    return user


def get_club(db: Session, club_id: int) -> Club:
    club = db.get(Club, club_id)
    if club is None:
        raise AppException("Club not found", status.HTTP_404_NOT_FOUND)
    return club


def get_active_club(db: Session, club_id: int) -> Club:
    club = get_club(db, club_id)
    if not club.is_active:
        raise AppException("Club not found", status.HTTP_404_NOT_FOUND)
    return club


def _ensure_unique_name(db: Session, name: str, club_id: int | None = None) -> None:
    query = select(Club).where(func.lower(Club.name) == name.lower())
    if club_id is not None:
        query = query.where(Club.id != club_id)
    if db.scalar(query) is not None:
        raise AppException("Club name already exists", status.HTTP_409_CONFLICT)


def _leader_response(membership: ClubMember) -> ClubLeaderResponse:
    return ClubLeaderResponse(
        user_id=membership.user_id,
        name=membership.user.name,
        email=membership.user.email,
        role=membership.role,
        joined_at=membership.joined_at,
    )


def _member_response(membership: ClubMember) -> ClubMemberResponse:
    return ClubMemberResponse(
        user_id=membership.user_id,
        name=membership.user.name,
        email=membership.user.email,
        role=membership.role,
        joined_at=membership.joined_at,
        added_by=membership.added_by,
    )


def _public_response(club: Club) -> ClubPublicResponse:
    return ClubPublicResponse(
        id=club.id,
        name=club.name,
        description=club.description,
        event_count=len(club.events),
        created_at=club.created_at,
        updated_at=club.updated_at,
    )


def _admin_response(club: Club) -> ClubAdminResponse:
    leaders = [
        _leader_response(membership)
        for membership in club.members
        if membership.role == ClubMemberRole.leader
    ]
    return ClubAdminResponse(
        id=club.id,
        name=club.name,
        description=club.description,
        event_count=len(club.events),
        is_active=club.is_active,
        created_by=club.created_by,
        created_at=club.created_at,
        updated_at=club.updated_at,
        leaders=leaders,
    )


def create_club(db: Session, payload: ClubCreate, admin: User) -> ClubAdminResponse:
    name = _normalize_name(payload.name)
    _ensure_unique_name(db, name)
    club = Club(
        name=name,
        description=payload.description,
        created_by=admin.id,
    )
    db.add(club)
    db.commit()
    db.refresh(club)
    return _admin_response(club)


def update_club(db: Session, club_id: int, payload: ClubUpdate) -> ClubAdminResponse:
    club = get_club(db, club_id)
    values = payload.model_dump(exclude_unset=True)
    if "name" in values and values["name"] is not None:
        name = _normalize_name(values["name"])
        _ensure_unique_name(db, name, club_id=club.id)
        club.name = name
    if "description" in values:
        club.description = values["description"]
    if "is_active" in values and values["is_active"] is not None:
        club.is_active = values["is_active"]

    db.add(club)
    db.commit()
    db.refresh(club)
    return _admin_response(club)


def deactivate_club(db: Session, club_id: int) -> ClubAdminResponse:
    club = get_club(db, club_id)
    club.is_active = False
    db.add(club)
    db.commit()
    db.refresh(club)
    return _admin_response(club)


def assign_leader(
    db: Session,
    club_id: int,
    user_id: int,
    added_by: User | None = None,
) -> ClubLeaderAssignmentResponse:
    club = get_club(db, club_id)
    _get_user(db, user_id)
    membership = db.get(ClubMember, {"club_id": club.id, "user_id": user_id})
    if membership is not None and membership.role == ClubMemberRole.leader:
        raise AppException("User is already a club leader", status.HTTP_409_CONFLICT)
    if membership is None:
        membership = ClubMember(
            club_id=club.id,
            user_id=user_id,
            role=ClubMemberRole.leader,
            added_by=added_by.id if added_by else None,
        )
    else:
        membership.role = ClubMemberRole.leader

    db.add(membership)
    db.commit()
    return ClubLeaderAssignmentResponse(
        club_id=club.id,
        user_id=user_id,
        role=ClubMemberRole.leader,
        message="Club leader assigned successfully",
    )


def remove_leader(
    db: Session,
    club_id: int,
    user_id: int,
) -> ClubLeaderAssignmentResponse:
    club = get_club(db, club_id)
    membership = db.get(ClubMember, {"club_id": club.id, "user_id": user_id})
    if membership is None or membership.role != ClubMemberRole.leader:
        raise AppException("Club leader assignment not found", status.HTTP_404_NOT_FOUND)
    _ensure_not_last_leader(db, club.id, user_id)

    db.delete(membership)
    db.commit()
    return ClubLeaderAssignmentResponse(
        club_id=club.id,
        user_id=user_id,
        role=ClubMemberRole.leader,
        message="Club leader removed successfully",
    )


def list_admin_clubs(db: Session) -> list[ClubAdminResponse]:
    clubs = list(
        db.scalars(
            select(Club)
            .options(selectinload(Club.members).selectinload(ClubMember.user))
            .order_by(Club.id)
        )
    )
    return [_admin_response(club) for club in clubs]


def _get_membership(db: Session, club_id: int, user_id: int) -> ClubMember | None:
    return db.get(ClubMember, {"club_id": club_id, "user_id": user_id})


def _leader_count(db: Session, club_id: int) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(ClubMember)
            .where(
                ClubMember.club_id == club_id,
                ClubMember.role == ClubMemberRole.leader,
            )
        )
        or 0
    )


def _ensure_not_last_leader(db: Session, club_id: int, user_id: int) -> None:
    membership = _get_membership(db, club_id, user_id)
    if membership is None or membership.role != ClubMemberRole.leader:
        return
    if _leader_count(db, club_id) <= 1:
        raise AppException("Cannot remove or demote the last club leader", status.HTTP_400_BAD_REQUEST)


def get_public_club(db: Session, club_id: int) -> ClubPublicResponse:
    club = db.scalar(
        select(Club)
        .where(Club.id == club_id, Club.is_active.is_(True))
        .options(
            selectinload(Club.members).selectinload(ClubMember.user),
            selectinload(Club.events),
        )
    )
    if club is None:
        raise AppException("Club not found", status.HTTP_404_NOT_FOUND)
    return _public_response(club)


def list_active_clubs(db: Session) -> list[ClubPublicResponse]:
    return list(
        _public_response(club)
        for club in db.scalars(
            select(Club)
            .where(Club.is_active.is_(True))
            .options(
                selectinload(Club.members).selectinload(ClubMember.user),
                selectinload(Club.events),
            )
            .order_by(Club.name)
        )
    )


def is_club_leader(db: Session, club_id: int, user_id: int) -> bool:
    membership = _get_membership(db, club_id, user_id)
    return membership is not None and membership.role == ClubMemberRole.leader


def is_club_member(db: Session, club_id: int, user_id: int) -> bool:
    return _get_membership(db, club_id, user_id) is not None


def ensure_club_leader(db: Session, club_id: int, user: User) -> None:
    if user.is_admin:
        return
    if not is_club_leader(db, club_id, user.id):
        raise AppException("Only this club's leader can perform this action", status.HTTP_403_FORBIDDEN)


def ensure_club_member(db: Session, club_id: int, user: User) -> None:
    if user.is_admin:
        return
    if not is_club_member(db, club_id, user.id):
        raise AppException("Only this club's members can perform this action", status.HTTP_403_FORBIDDEN)


def add_member(
    db: Session,
    club_id: int,
    user_id: int,
    actor: User,
) -> ClubMemberActionResponse:
    club = get_active_club(db, club_id)
    ensure_club_member(db, club.id, actor)
    _get_user(db, user_id)
    if _get_membership(db, club.id, user_id) is not None:
        raise AppException("User is already a club member", status.HTTP_409_CONFLICT)

    membership = ClubMember(
        club_id=club.id,
        user_id=user_id,
        role=ClubMemberRole.member,
        added_by=actor.id,
    )
    db.add(membership)
    db.commit()
    return ClubMemberActionResponse(
        club_id=club.id,
        user_id=user_id,
        role=ClubMemberRole.member,
        message="Club member added successfully",
    )


def remove_member(
    db: Session,
    club_id: int,
    user_id: int,
    actor: User,
) -> ClubMemberActionResponse:
    club = get_active_club(db, club_id)
    ensure_club_leader(db, club.id, actor)
    membership = _get_membership(db, club.id, user_id)
    if membership is None:
        raise AppException("Club membership not found", status.HTTP_404_NOT_FOUND)
    _ensure_not_last_leader(db, club.id, user_id)

    db.delete(membership)
    db.commit()
    return ClubMemberActionResponse(
        club_id=club.id,
        user_id=user_id,
        message="Club member removed successfully",
    )


def promote_member(
    db: Session,
    club_id: int,
    user_id: int,
    actor: User,
) -> ClubMemberActionResponse:
    club = get_active_club(db, club_id)
    ensure_club_leader(db, club.id, actor)
    if actor.id == user_id:
        raise AppException("Club leaders cannot promote themselves", status.HTTP_400_BAD_REQUEST)
    membership = _get_membership(db, club.id, user_id)
    if membership is None:
        raise AppException("Club membership not found", status.HTTP_404_NOT_FOUND)
    if membership.role == ClubMemberRole.leader:
        raise AppException("User is already a club leader", status.HTTP_409_CONFLICT)

    membership.role = ClubMemberRole.leader
    db.add(membership)
    db.commit()
    return ClubMemberActionResponse(
        club_id=club.id,
        user_id=user_id,
        role=ClubMemberRole.leader,
        message="Club member promoted to leader",
    )


def demote_leader(
    db: Session,
    club_id: int,
    user_id: int,
    actor: User,
) -> ClubMemberActionResponse:
    club = get_active_club(db, club_id)
    ensure_club_leader(db, club.id, actor)
    if actor.id == user_id:
        raise AppException("Club leaders cannot demote themselves", status.HTTP_400_BAD_REQUEST)
    membership = _get_membership(db, club.id, user_id)
    if membership is None:
        raise AppException("Club membership not found", status.HTTP_404_NOT_FOUND)
    if membership.role != ClubMemberRole.leader:
        raise AppException("User is not a club leader", status.HTTP_400_BAD_REQUEST)
    _ensure_not_last_leader(db, club.id, user_id)

    membership.role = ClubMemberRole.member
    db.add(membership)
    db.commit()
    return ClubMemberActionResponse(
        club_id=club.id,
        user_id=user_id,
        role=ClubMemberRole.member,
        message="Club leader demoted to member",
    )


def list_club_members(db: Session, club_id: int, actor: User) -> list[ClubMemberResponse]:
    club = get_active_club(db, club_id)
    ensure_club_member(db, club.id, actor)
    memberships = list(
        db.scalars(
            select(ClubMember)
            .where(ClubMember.club_id == club.id)
            .join(ClubMember.user)
            .order_by(ClubMember.role, User.name)
        )
    )
    return [_member_response(membership) for membership in memberships]
