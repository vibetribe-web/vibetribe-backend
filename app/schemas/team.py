from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.event import EventStatus
from app.models.request import RequestStatus
from app.models.team_member import TeamMemberRole
from app.schemas.user import UserRead


class TeamBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    required_skills: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    preferred_roles: list[str] = Field(default_factory=list)
    hackathon_category: str | None = Field(default=None, max_length=120)
    event_id: int | None = Field(default=None, gt=0)
    max_members: int = Field(default=5, ge=2, le=50)

    @field_validator("name", "description", "hackathon_category")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        return stripped or None

    @field_validator("required_skills")
    @classmethod
    def normalize_required_skills(cls, value: list[str]) -> list[str]:
        return normalize_text_list(value)

    @field_validator("interests", "preferred_roles")
    @classmethod
    def normalize_optional_lists(cls, value: list[str]) -> list[str]:
        return normalize_text_list(value)


def normalize_text_list(value: list[str]) -> list[str]:
        skills = []
        seen = set()
        for skill in value:
            normalized = skill.strip()
            key = normalized.lower()
            if normalized and key not in seen:
                skills.append(normalized)
                seen.add(key)
        return skills


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    required_skills: list[str] | None = None
    interests: list[str] | None = None
    preferred_roles: list[str] | None = None
    hackathon_category: str | None = Field(default=None, max_length=120)
    event_id: int | None = Field(default=None, gt=0)
    max_members: int | None = Field(default=None, ge=2, le=50)

    @field_validator("name", "description", "hackathon_category")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        return stripped or None

    @field_validator("required_skills")
    @classmethod
    def normalize_required_skills(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        return normalize_text_list(value)

    @field_validator("interests", "preferred_roles")
    @classmethod
    def normalize_optional_lists(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        return normalize_text_list(value)


class TeamMemberRead(BaseModel):
    user_id: int
    name: str
    email: str
    username: str | None = None
    profile_image_url: str | None = None
    role: TeamMemberRole
    joined_at: datetime


class TeamMemberRoleUpdate(BaseModel):
    role: TeamMemberRole


class TeamEventSummary(BaseModel):
    id: int
    title: str
    event_type: str
    start_date: datetime
    event_status: EventStatus

    model_config = ConfigDict(from_attributes=True)


class TeamResponse(TeamBase):
    id: int
    leader_id: int
    leader: UserRead | None = None
    event: TeamEventSummary | None = None
    current_members_count: int = 0
    available_slots: int = 0
    members: list[TeamMemberRead] = Field(default_factory=list)
    is_current_user_member: bool = False
    is_current_user_leader: bool = False
    has_pending_request: bool = False

    model_config = ConfigDict(from_attributes=True)


TeamRead = TeamResponse


class TeamDetail(TeamRead):
    pass


class TeamWorkflowResponse(BaseModel):
    team_id: int
    team_name: str
    member_count: int
    max_members: int
    request_status: RequestStatus | None = None
    message: str
