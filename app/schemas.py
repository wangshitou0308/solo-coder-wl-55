from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.enums import BeardCategory, RegistrationStatus, EventStatus, AwardType, PhotoType


class ContestantCreate(BaseModel):
    name: str = Field(..., max_length=100)
    nationality: str = Field(..., max_length=80)
    email: Optional[str] = Field(None, max_length=200)
    phone: Optional[str] = Field(None, max_length=30)
    bio: Optional[str] = None


class ContestantUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    nationality: Optional[str] = Field(None, max_length=80)
    email: Optional[str] = Field(None, max_length=200)
    phone: Optional[str] = Field(None, max_length=30)
    bio: Optional[str] = None


class ContestantPhotoOut(BaseModel):
    id: int
    contestant_id: int
    photo_type: PhotoType
    file_path: str
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class ContestantOut(BaseModel):
    id: int
    name: str
    nationality: str
    email: Optional[str]
    phone: Optional[str]
    bio: Optional[str]
    created_at: datetime
    updated_at: datetime
    photos: List[ContestantPhotoOut] = []

    model_config = {"from_attributes": True}


class ContestantHistoryOut(BaseModel):
    event_id: int
    event_name: str
    edition_number: int
    host_city: str
    event_date: datetime
    category: BeardCategory
    status: RegistrationStatus
    appearance_order: Optional[int]
    final_score: Optional[float]
    award: Optional[str]

    model_config = {"from_attributes": True}


class ContestantPointsOut(BaseModel):
    contestant_id: int
    contestant_name: str
    nationality: str
    total_points: int
    events_participated: int
    gold_count: int
    silver_count: int
    bronze_count: int

    model_config = {"from_attributes": True}


class ContestEventCreate(BaseModel):
    edition_number: int
    name: str = Field(..., max_length=200)
    host_city: str = Field(..., max_length=100)
    host_country: str = Field(..., max_length=100)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    event_date: datetime
    registration_start: datetime
    registration_end: datetime


class ContestEventUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    host_city: Optional[str] = Field(None, max_length=100)
    host_country: Optional[str] = Field(None, max_length=100)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    event_date: Optional[datetime] = None
    registration_start: Optional[datetime] = None
    registration_end: Optional[datetime] = None
    status: Optional[EventStatus] = None


class ContestEventOut(BaseModel):
    id: int
    edition_number: int
    name: str
    host_city: str
    host_country: str
    latitude: Optional[float]
    longitude: Optional[float]
    event_date: datetime
    registration_start: datetime
    registration_end: datetime
    status: EventStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class RegistrationCreate(BaseModel):
    contestant_id: int
    event_id: int
    category: BeardCategory


class RegistrationReview(BaseModel):
    status: RegistrationStatus


class RegistrationOut(BaseModel):
    id: int
    contestant_id: int
    event_id: int
    category: BeardCategory
    status: RegistrationStatus
    appearance_order: Optional[int]
    registered_at: datetime
    reviewed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class RegistrationDetailOut(RegistrationOut):
    contestant_name: Optional[str] = None
    contestant_nationality: Optional[str] = None


class JudgeCreate(BaseModel):
    name: str = Field(..., max_length=100)
    nationality: Optional[str] = Field(None, max_length=80)
    expertise: Optional[str] = Field(None, max_length=200)


class JudgeOut(BaseModel):
    id: int
    name: str
    nationality: Optional[str]
    expertise: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ScoreCreate(BaseModel):
    judge_id: int
    registration_id: int
    event_id: int
    creativity: float = Field(..., ge=0, le=100)
    symmetry: float = Field(..., ge=0, le=100)
    maintenance: float = Field(..., ge=0, le=100)
    stage_presence: float = Field(..., ge=0, le=100)
    overall_impression: float = Field(..., ge=0, le=100)


class ScoreOut(BaseModel):
    id: int
    judge_id: int
    registration_id: int
    event_id: int
    creativity: float
    symmetry: float
    maintenance: float
    stage_presence: float
    overall_impression: float
    weighted_total: float
    created_at: datetime

    model_config = {"from_attributes": True}


class CategoryRankingOut(BaseModel):
    rank: int
    contestant_id: int
    contestant_name: str
    nationality: str
    category: BeardCategory
    final_score: float
    scores_detail: List[dict]


class CategoryRankingsOut(BaseModel):
    event_id: int
    event_name: str
    category: BeardCategory
    rankings: List[CategoryRankingOut]


class AdvancementListOut(BaseModel):
    event_id: int
    event_name: str
    category: BeardCategory
    advancing: List[CategoryRankingOut]
    eliminated: List[CategoryRankingOut]


class AwardCreate(BaseModel):
    event_id: int
    contestant_id: int
    category: Optional[BeardCategory] = None
    award_type: AwardType


class AwardOut(BaseModel):
    id: int
    event_id: int
    contestant_id: int
    category: Optional[BeardCategory]
    award_type: AwardType
    points: int
    created_at: datetime
    contestant_name: Optional[str] = None

    model_config = {"from_attributes": True}


class EventResultsOut(BaseModel):
    event_id: int
    event_name: str
    edition_number: int
    host_city: str
    category_results: dict
    best_newcomer: Optional[AwardOut]
    overall_champion: Optional[AwardOut]


class CountryStatOut(BaseModel):
    country: str
    contestant_count: int


class CategoryChampionOut(BaseModel):
    category: str
    champions: List[dict]


class CityMapOut(BaseModel):
    city: str
    country: str
    latitude: Optional[float]
    longitude: Optional[float]
    edition_number: int
    event_name: str


class MessageOut(BaseModel):
    message: str
