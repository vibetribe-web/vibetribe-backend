from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.club_member import ClubMemberRole


class ClubBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=4000)

    @field_validator("name", "description")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        return stripped or None


class ClubCreate(ClubBase):
    pass


class ClubUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    is_active: bool | None = None

    @field_validator("name", "description")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        return stripped or None


class ClubPublicResponse(BaseModel):
    id: int
    name: str
    description: str | None
    event_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClubLeaderResponse(BaseModel):
    user_id: int
    name: str
    email: str
    role: ClubMemberRole
    joined_at: datetime


class ClubMemberResponse(BaseModel):
    user_id: int
    name: str
    email: str
    role: ClubMemberRole
    joined_at: datetime
    added_by: int | None


class ClubAdminResponse(ClubPublicResponse):
    is_active: bool
    created_by: int
    leaders: list[ClubLeaderResponse] = Field(default_factory=list)


class ClubLeaderAssignmentResponse(BaseModel):
    club_id: int
    user_id: int
    role: ClubMemberRole
    message: str


class ClubMemberActionResponse(BaseModel):
    club_id: int
    user_id: int
    role: ClubMemberRole | None = None
    message: str
