from datetime import datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from app.models.event import EventMode, EventStatus, EventType
from app.models.team_message import TeamMessageType


class TeamMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=8000)

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("content is required")
        return stripped


class TeamEventShareCreate(BaseModel):
    event_id: int = Field(validation_alias=AliasChoices("event_id", "shared_event_id"))
    content: str | None = Field(default=None, max_length=8000)

    @field_validator("content")
    @classmethod
    def strip_optional_content(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        return stripped or None


class TeamMessageSenderRead(BaseModel):
    id: int
    name: str
    username: str | None = None
    profile_image_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TeamMessageEventRead(BaseModel):
    id: int
    title: str
    event_type: EventType
    mode: EventMode
    start_date: datetime
    end_date: datetime
    image_url: str | None = None
    venue: str | None = None
    description: str
    club_id: int
    club_name: str
    event_status: EventStatus


class TeamMessageRead(BaseModel):
    id: int
    team_id: int
    shared_event_id: int | None = None
    sender: TeamMessageSenderRead
    message_type: TeamMessageType
    content: str | None
    event: TeamMessageEventRead | None = None
    created_at: datetime


class TeamMessagePage(BaseModel):
    items: list[TeamMessageRead]
    has_more: bool
    next_before_id: int | None = None
