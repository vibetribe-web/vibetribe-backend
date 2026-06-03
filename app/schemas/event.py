from datetime import datetime

from pydantic import AnyUrl, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.event import EventMode, EventStatus, EventType
from app.schemas.club import ClubPublicResponse


class EventBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    description: str = Field(..., min_length=1, max_length=8000)
    event_type: EventType
    mode: EventMode
    venue: str | None = Field(default=None, max_length=255)
    start_date: datetime
    end_date: datetime
    registration_link: AnyUrl | None = None
    image_url: AnyUrl | None = None

    @field_validator("title", "description", "venue")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def validate_dates(self) -> "EventBase":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        return self


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=8000)
    event_type: EventType | None = None
    mode: EventMode | None = None
    venue: str | None = Field(default=None, max_length=255)
    start_date: datetime | None = None
    end_date: datetime | None = None
    registration_link: AnyUrl | None = None
    image_url: AnyUrl | None = None

    @field_validator("title", "description", "venue")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        return stripped or None


class EventPosterUploadResponse(BaseModel):
    path: str
    public_url: str


class EventPublicResponse(BaseModel):
    id: int
    club_id: int
    title: str
    description: str
    event_type: EventType
    mode: EventMode
    venue: str | None
    start_date: datetime
    end_date: datetime
    registration_link: str | None
    image_url: str | None
    interested_count: int = 0
    is_interested: bool = False
    event_status: EventStatus
    club: ClubPublicResponse | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventDetailResponse(EventPublicResponse):
    club: ClubPublicResponse


class EventAdminResponse(EventPublicResponse):
    created_by: int


class EventInterestResponse(BaseModel):
    event_id: int
    is_interested: bool
    interested_count: int


class EventTeammateRecommendation(BaseModel):
    id: int
    name: str
    username: str | None = None
    college: str | None = None
    branch: str | None = None
    year: int | None = None
    skills: list[str] = Field(default_factory=list)
    profile_image_url: str | None = None
    match_score: int
    reason_tags: list[str] = Field(default_factory=list)
