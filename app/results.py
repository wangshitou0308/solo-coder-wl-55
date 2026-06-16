from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from collections import defaultdict

from app.database import get_db
from app.models import Award, ContestEvent, Contestant, Registration, Score, ContestantPoints
from app.schemas import AwardCreate, AwardOut, EventResultsOut
from app.enums import AwardType, BeardCategory, RegistrationStatus, AWARD_POINTS

router = APIRouter(prefix="/results", tags=["赛事结果"])


def recalculate_contestant_points(contestant_id: int, db: Session, auto_commit: bool = True):
    db.flush()
    awards = db.query(Award).filter(Award.contestant_id == contestant_id).all()
    total_points = sum(a.points for a in awards)
    gold_count = sum(1 for a in awards if a.award_type == AwardType.GOLD)
    silver_count = sum(1 for a in awards if a.award_type == AwardType.SILVER)
    bronze_count = sum(1 for a in awards if a.award_type == AwardType.BRONZE)

    participated_events = (
        db.query(Registration.event_id)
        .filter(Registration.contestant_id == contestant_id, Registration.status == RegistrationStatus.APPROVED)
        .distinct()
        .count()
    )

    points_record = db.query(ContestantPoints).filter(ContestantPoints.contestant_id == contestant_id).first()
    if not points_record:
        points_record = ContestantPoints(contestant_id=contestant_id)
        db.add(points_record)

    points_record.total_points = total_points
    points_record.events_participated = participated_events
    points_record.gold_count = gold_count
    points_record.silver_count = silver_count
    points_record.bronze_count = bronze_count
    if auto_commit:
        db.commit()


@router.post("/awards", response_model=AwardOut, summary="颁发奖项")
def create_award(data: AwardCreate, db: Session = Depends(get_db)):
    event = db.query(ContestEvent).filter(ContestEvent.id == data.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="赛事不存在")

    contestant = db.query(Contestant).filter(Contestant.id == data.contestant_id).first()
    if not contestant:
        raise HTTPException(status_code=404, detail="选手不存在")

    if data.award_type in (AwardType.GOLD, AwardType.SILVER, AwardType.BRONZE) and not data.category:
        raise HTTPException(status_code=400, detail="金/银/铜奖必须指定参赛组别")

    if data.category:
        reg = db.query(Registration).filter(
            Registration.contestant_id == data.contestant_id,
            Registration.event_id == data.event_id,
            Registration.category == data.category,
        ).first()
        if not reg:
            raise HTTPException(status_code=400, detail="该选手未报名此赛事的该组别")
        if reg.status != RegistrationStatus.APPROVED:
            raise HTTPException(status_code=400, detail="该选手报名尚未审核通过，无法颁发该组别奖项")

    if data.award_type == AwardType.OVERALL_CHAMPION:
        existing = db.query(Award).filter(
            Award.event_id == data.event_id,
            Award.award_type == AwardType.OVERALL_CHAMPION,
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="该赛事已颁发全场总冠军")

    if data.category and data.award_type in (AwardType.GOLD, AwardType.SILVER, AwardType.BRONZE):
        existing = db.query(Award).filter(
            Award.event_id == data.event_id,
            Award.category == data.category,
            Award.award_type == data.award_type,
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"该赛事该组别已颁发{data.award_type.value}奖")

    points = AWARD_POINTS[data.award_type]

    award = Award(
        event_id=data.event_id,
        contestant_id=data.contestant_id,
        category=data.category,
        award_type=data.award_type,
        points=points,
    )
    db.add(award)
    db.commit()
    db.refresh(award)

    recalculate_contestant_points(data.contestant_id, db)

    result = AwardOut.model_validate(award)
    result.contestant_name = contestant.name
    return result


@router.get("/awards", response_model=List[AwardOut], summary="查询奖项列表")
def list_awards(
    event_id: Optional[int] = Query(None),
    contestant_id: Optional[int] = Query(None),
    award_type: Optional[AwardType] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Award)
    if event_id:
        q = q.filter(Award.event_id == event_id)
    if contestant_id:
        q = q.filter(Award.contestant_id == contestant_id)
    if award_type:
        q = q.filter(Award.award_type == award_type)

    awards = q.all()
    results = []
    for a in awards:
        contestant = db.query(Contestant).filter(Contestant.id == a.contestant_id).first()
        out = AwardOut.model_validate(a)
        out.contestant_name = contestant.name if contestant else None
        results.append(out)
    return results


@router.get("/event/{event_id}", summary="赛事结果公示")
def get_event_results(event_id: int, db: Session = Depends(get_db)):
    event = db.query(ContestEvent).filter(ContestEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="赛事不存在")

    awards = db.query(Award).filter(Award.event_id == event_id).all()

    category_results = defaultdict(list)
    best_newcomer = None
    overall_champion = None

    for award in awards:
        contestant = db.query(Contestant).filter(Contestant.id == award.contestant_id).first()
        award_info = {
            "award_id": award.id,
            "contestant_id": award.contestant_id,
            "contestant_name": contestant.name if contestant else "Unknown",
            "nationality": contestant.nationality if contestant else "Unknown",
            "award_type": award.award_type.value,
            "category": award.category.value if award.category else None,
            "points": award.points,
        }

        if award.award_type in (AwardType.GOLD, AwardType.SILVER, AwardType.BRONZE) and award.category:
            category_results[award.category.value].append(award_info)
        elif award.award_type == AwardType.BEST_NEWCOMER:
            best_newcomer = award_info
        elif award.award_type == AwardType.OVERALL_CHAMPION:
            overall_champion = award_info

    for cat in category_results:
        category_results[cat].sort(key=lambda x: {"gold": 0, "silver": 1, "bronze": 2}.get(x["award_type"], 3))

    return {
        "event_id": event_id,
        "event_name": event.name,
        "edition_number": event.edition_number,
        "host_city": event.host_city,
        "category_results": dict(category_results),
        "best_newcomer": best_newcomer,
        "overall_champion": overall_champion,
    }


@router.post("/auto-awards/{event_id}", summary="自动生成各组别前三名奖项")
def auto_generate_awards(event_id: int, db: Session = Depends(get_db)):
    from app.scoring import get_category_rankings

    event = db.query(ContestEvent).filter(ContestEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="赛事不存在")

    categories = (
        db.query(Registration.category)
        .filter(Registration.event_id == event_id, Registration.status == RegistrationStatus.APPROVED)
        .distinct()
        .all()
    )

    created_awards = []

    for (cat,) in categories:
        try:
            ranking_data = get_category_rankings(event_id, cat, db)
        except HTTPException:
            continue

        award_map = {0: AwardType.GOLD, 1: AwardType.SILVER, 2: AwardType.BRONZE}

        for rank, entry in enumerate(ranking_data.rankings[:3]):
            if rank in award_map:
                existing = db.query(Award).filter(
                    Award.event_id == event_id,
                    Award.category == cat,
                    Award.award_type == award_map[rank],
                ).first()
                if not existing:
                    award = Award(
                        event_id=event_id,
                        contestant_id=entry.contestant_id,
                        category=cat,
                        award_type=award_map[rank],
                        points=AWARD_POINTS[award_map[rank]],
                    )
                    db.add(award)
                    created_awards.append({
                        "contestant_id": entry.contestant_id,
                        "contestant_name": entry.contestant_name,
                        "category": cat.value,
                        "award_type": award_map[rank].value,
                    })
                    recalculate_contestant_points(entry.contestant_id, db, auto_commit=False)

    db.commit()
    return {"message": "奖项已自动生成", "awards": created_awards}
