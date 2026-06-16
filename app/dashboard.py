from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from collections import defaultdict

from app.database import get_db
from app.models import (
    Contestant, ContestEvent, Registration, Score,
    Award, ContestantPoints, Judge,
)
from app.schemas import (
    CountryStatOut, CategoryChampionOut, ContestantPointsOut, CityMapOut,
)
from app.enums import AwardType, RegistrationStatus, BeardCategory

router = APIRouter(prefix="/dashboard", tags=["数据看板"])


@router.get("/country-stats", response_model=List[CountryStatOut], summary="各国参赛人数统计")
def country_statistics(db: Session = Depends(get_db)):
    contestants = db.query(Contestant).all()
    country_counts = defaultdict(int)
    for c in contestants:
        country_counts[c.nationality] += 1

    results = [
        CountryStatOut(country=country, contestant_count=count)
        for country, count in sorted(country_counts.items(), key=lambda x: x[1], reverse=True)
    ]
    return results


@router.get("/country-event-stats/{event_id}", response_model=List[CountryStatOut], summary="某届赛事各国参赛人数统计")
def country_event_statistics(event_id: int, db: Session = Depends(get_db)):
    event = db.query(ContestEvent).filter(ContestEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="赛事不存在")

    registrations = (
        db.query(Registration)
        .filter(Registration.event_id == event_id, Registration.status == RegistrationStatus.APPROVED)
        .all()
    )

    country_counts = defaultdict(int)
    for reg in registrations:
        contestant = db.query(Contestant).filter(Contestant.id == reg.contestant_id).first()
        if contestant:
            country_counts[contestant.nationality] += 1

    results = [
        CountryStatOut(country=country, contestant_count=count)
        for country, count in sorted(country_counts.items(), key=lambda x: x[1], reverse=True)
    ]
    return results


@router.get("/category-champions", summary="各组别历年冠军分布")
def category_champions_history(db: Session = Depends(get_db)):
    gold_awards = db.query(Award).filter(Award.award_type == AwardType.GOLD).all()

    champions_by_category = defaultdict(list)
    for award in gold_awards:
        event = db.query(ContestEvent).filter(ContestEvent.id == award.event_id).first()
        contestant = db.query(Contestant).filter(Contestant.id == award.contestant_id).first()

        champions_by_category[award.category.value if award.category else "unknown"].append({
            "event_id": award.event_id,
            "event_name": event.name if event else "Unknown",
            "edition_number": event.edition_number if event else 0,
            "year": event.event_date.year if event else 0,
            "champion_id": award.contestant_id,
            "champion_name": contestant.name if contestant else "Unknown",
            "nationality": contestant.nationality if contestant else "Unknown",
        })

    for cat in champions_by_category:
        champions_by_category[cat].sort(key=lambda x: x["year"])

    return {
        "category_champions": dict(champions_by_category),
    }


@router.get("/points-ranking", response_model=List[ContestantPointsOut], summary="选手积分排行")
def points_ranking(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    points_records = (
        db.query(ContestantPoints)
        .order_by(ContestantPoints.total_points.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    results = []
    for p in points_records:
        contestant = db.query(Contestant).filter(Contestant.id == p.contestant_id).first()
        if contestant:
            results.append(ContestantPointsOut(
                contestant_id=contestant.id,
                contestant_name=contestant.name,
                nationality=contestant.nationality,
                total_points=p.total_points,
                events_participated=p.events_participated,
                gold_count=p.gold_count,
                silver_count=p.silver_count,
                bronze_count=p.bronze_count,
            ))
    return results


@router.get("/city-map", response_model=List[CityMapOut], summary="赛事举办城市地图数据")
def city_map_data(db: Session = Depends(get_db)):
    events = db.query(ContestEvent).order_by(ContestEvent.edition_number).all()

    results = []
    for event in events:
        results.append(CityMapOut(
            city=event.host_city,
            country=event.host_country,
            latitude=event.latitude,
            longitude=event.longitude,
            edition_number=event.edition_number,
            event_name=event.name,
        ))
    return results


@router.get("/event-summary/{event_id}", summary="赛事概览统计")
def event_summary(event_id: int, db: Session = Depends(get_db)):
    event = db.query(ContestEvent).filter(ContestEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="赛事不存在")

    total_registrations = db.query(Registration).filter(Registration.event_id == event_id).count()
    approved_registrations = db.query(Registration).filter(
        Registration.event_id == event_id, Registration.status == RegistrationStatus.APPROVED
    ).count()

    categories = (
        db.query(Registration.category)
        .filter(Registration.event_id == event_id, Registration.status == RegistrationStatus.APPROVED)
        .distinct()
        .all()
    )

    category_counts = {}
    for (cat,) in categories:
        count = db.query(Registration).filter(
            Registration.event_id == event_id,
            Registration.category == cat,
            Registration.status == RegistrationStatus.APPROVED,
        ).count()
        category_counts[cat.value] = count

    total_scores = db.query(Score).filter(Score.event_id == event_id).count()
    total_judges = db.query(Judge).count()

    awards_count = db.query(Award).filter(Award.event_id == event_id).count()

    return {
        "event_id": event_id,
        "event_name": event.name,
        "edition_number": event.edition_number,
        "status": event.status.value,
        "total_registrations": total_registrations,
        "approved_registrations": approved_registrations,
        "categories": category_counts,
        "total_scores_given": total_scores,
        "total_judges": total_judges,
        "total_awards": awards_count,
    }


@router.get("/category-distribution", summary="历届各组别参赛人数分布")
def category_distribution(db: Session = Depends(get_db)):
    registrations = db.query(Registration).filter(Registration.status == RegistrationStatus.APPROVED).all()

    distribution = defaultdict(lambda: defaultdict(int))
    for reg in registrations:
        event = db.query(ContestEvent).filter(ContestEvent.id == reg.event_id).first()
        if event:
            distribution[reg.category.value][event.edition_number] += 1

    return {
        "category_distribution": {cat: dict(editions) for cat, editions in distribution.items()},
    }
