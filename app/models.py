from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base
from app.enums import BeardCategory, RegistrationStatus, EventStatus, AwardType, PhotoType


class Contestant(Base):
    __tablename__ = "contestants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    nationality = Column(String(80), nullable=False)
    email = Column(String(200), unique=True, index=True)
    phone = Column(String(30))
    bio = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    updated_at = Column(DateTime, default=lambda: datetime.utcnow(), onupdate=lambda: datetime.utcnow())

    photos = relationship("ContestantPhoto", back_populates="contestant", cascade="all, delete-orphan")
    registrations = relationship("Registration", back_populates="contestant", cascade="all, delete-orphan")
    awards = relationship("Award", back_populates="contestant")
    total_points = relationship("ContestantPoints", back_populates="contestant", uselist=False, cascade="all, delete-orphan")


class ContestantPhoto(Base):
    __tablename__ = "contestant_photos"

    id = Column(Integer, primary_key=True, index=True)
    contestant_id = Column(Integer, ForeignKey("contestants.id"), nullable=False)
    photo_type = Column(Enum(PhotoType), nullable=False)
    file_path = Column(String(500), nullable=False)
    uploaded_at = Column(DateTime, default=lambda: datetime.utcnow())

    contestant = relationship("Contestant", back_populates="photos")


class ContestEvent(Base):
    __tablename__ = "contest_events"

    id = Column(Integer, primary_key=True, index=True)
    edition_number = Column(Integer, nullable=False)
    name = Column(String(200), nullable=False)
    host_city = Column(String(100), nullable=False)
    host_country = Column(String(100), nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    event_date = Column(DateTime, nullable=False)
    registration_start = Column(DateTime, nullable=False)
    registration_end = Column(DateTime, nullable=False)
    status = Column(Enum(EventStatus), default=EventStatus.DRAFT)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    registrations = relationship("Registration", back_populates="event")
    scores = relationship("Score", back_populates="event")
    awards = relationship("Award", back_populates="event")


class Registration(Base):
    __tablename__ = "registrations"

    id = Column(Integer, primary_key=True, index=True)
    contestant_id = Column(Integer, ForeignKey("contestants.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("contest_events.id"), nullable=False)
    category = Column(Enum(BeardCategory), nullable=False)
    status = Column(Enum(RegistrationStatus), default=RegistrationStatus.PENDING)
    appearance_order = Column(Integer, nullable=True)
    registered_at = Column(DateTime, default=lambda: datetime.utcnow())
    reviewed_at = Column(DateTime, nullable=True)

    contestant = relationship("Contestant", back_populates="registrations")
    event = relationship("ContestEvent", back_populates="registrations")
    scores = relationship("Score", back_populates="registration", cascade="all, delete-orphan")


class Judge(Base):
    __tablename__ = "judges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    nationality = Column(String(80))
    expertise = Column(String(200))
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    scores = relationship("Score", back_populates="judge")


class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, index=True)
    judge_id = Column(Integer, ForeignKey("judges.id"), nullable=False)
    registration_id = Column(Integer, ForeignKey("registrations.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("contest_events.id"), nullable=False)
    creativity = Column(Float, nullable=False)
    symmetry = Column(Float, nullable=False)
    maintenance = Column(Float, nullable=False)
    stage_presence = Column(Float, nullable=False)
    overall_impression = Column(Float, nullable=False)
    weighted_total = Column(Float, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    judge = relationship("Judge", back_populates="scores")
    registration = relationship("Registration", back_populates="scores")
    event = relationship("ContestEvent", back_populates="scores")


class Award(Base):
    __tablename__ = "awards"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("contest_events.id"), nullable=False)
    contestant_id = Column(Integer, ForeignKey("contestants.id"), nullable=False)
    category = Column(Enum(BeardCategory), nullable=True)
    award_type = Column(Enum(AwardType), nullable=False)
    points = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.utcnow())

    event = relationship("ContestEvent", back_populates="awards")
    contestant = relationship("Contestant", back_populates="awards")


class ContestantPoints(Base):
    __tablename__ = "contestant_points"

    id = Column(Integer, primary_key=True, index=True)
    contestant_id = Column(Integer, ForeignKey("contestants.id"), unique=True, nullable=False)
    total_points = Column(Integer, default=0)
    events_participated = Column(Integer, default=0)
    gold_count = Column(Integer, default=0)
    silver_count = Column(Integer, default=0)
    bronze_count = Column(Integer, default=0)
    updated_at = Column(DateTime, default=lambda: datetime.utcnow(), onupdate=lambda: datetime.utcnow())

    contestant = relationship("Contestant", back_populates="total_points")
