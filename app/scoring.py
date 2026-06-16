from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from collections import defaultdict

from app.database import get_db
from app.models import Score, Registration, Contestant, ContestEvent, Judge
from app.schemas import ScoreCreate, ScoreOut, CategoryRankingOut, CategoryRankingsOut, AdvancementListOut
from app.enums import SCORING_DIMENSIONS, RegistrationStatus, BeardCategory

router = APIRouter(prefix="/scoring", tags=["评审打分"])


def calculate_weighted_total(score_data: dict) -> float:
    total = 0.0
    for dim, weight in SCORING_DIMENSIONS.items():
        total += score_data.get(dim, 0) * weight
    return round(total, 2)


@router.post("", response_model=ScoreOut, summary="评委打分")
def create_score(data: ScoreCreate, db: Session = Depends(get_db)):
    judge = db.query(Judge).filter(Judge.id == data.judge_id).first()
    if not judge:
        raise HTTPException(status_code=404, detail="评委不存在")

    registration = db.query(Registration).filter(Registration.id == data.registration_id).first()
    if not registration:
        raise HTTPException(status_code=404, detail="报名记录不存在")

    if registration.status != RegistrationStatus.APPROVED:
        raise HTTPException(status_code=400, detail="该报名尚未审核通过，无法打分")

    event = db.query(ContestEvent).filter(ContestEvent.id == data.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="赛事不存在")

    existing = db.query(Score).filter(
        Score.judge_id == data.judge_id,
        Score.registration_id == data.registration_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="该评委已对此选手打分，请勿重复打分")

    weighted_total = calculate_weighted_total(data.model_dump())

    score = Score(
        judge_id=data.judge_id,
        registration_id=data.registration_id,
        event_id=data.event_id,
        creativity=data.creativity,
        symmetry=data.symmetry,
        maintenance=data.maintenance,
        stage_presence=data.stage_presence,
        overall_impression=data.overall_impression,
        weighted_total=weighted_total,
    )
    db.add(score)
    db.commit()
    db.refresh(score)
    return score


@router.get("", response_model=List[ScoreOut], summary="查询打分记录")
def list_scores(
    event_id: Optional[int] = Query(None),
    registration_id: Optional[int] = Query(None),
    judge_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(Score)
    if event_id:
        q = q.filter(Score.event_id == event_id)
    if registration_id:
        q = q.filter(Score.registration_id == registration_id)
    if judge_id:
        q = q.filter(Score.judge_id == judge_id)
    return q.offset(skip).limit(limit).all()


@router.get("/rankings/{event_id}/{category}", summary="按组别生成排名")
def get_category_rankings(event_id: int, category: BeardCategory, db: Session = Depends(get_db)):
    event = db.query(ContestEvent).filter(ContestEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="赛事不存在")

    registrations = (
        db.query(Registration)
        .filter(
            Registration.event_id == event_id,
            Registration.category == category,
            Registration.status == RegistrationStatus.APPROVED,
        )
        .all()
    )

    if not registrations:
        raise HTTPException(status_code=404, detail="该组别无参赛选手")

    rankings = []
    for reg in registrations:
        contestant = db.query(Contestant).filter(Contestant.id == reg.contestant_id).first()
        scores = db.query(Score).filter(Score.registration_id == reg.id).all()

        if not scores:
            continue

        weighted_totals = [s.weighted_total for s in scores]

        if len(weighted_totals) >= 3:
            sorted_totals = sorted(weighted_totals)
            trimmed = sorted_totals[1:-1]
            final_score = round(sum(trimmed) / len(trimmed), 2)
        else:
            final_score = round(sum(weighted_totals) / len(weighted_totals), 2)

        scores_detail = []
        for s in scores:
            judge = db.query(Judge).filter(Judge.id == s.judge_id).first()
            scores_detail.append({
                "judge_id": s.judge_id,
                "judge_name": judge.name if judge else "Unknown",
                "creativity": s.creativity,
                "symmetry": s.symmetry,
                "maintenance": s.maintenance,
                "stage_presence": s.stage_presence,
                "overall_impression": s.overall_impression,
                "weighted_total": s.weighted_total,
            })

        rankings.append(CategoryRankingOut(
            rank=0,
            contestant_id=contestant.id,
            contestant_name=contestant.name,
            nationality=contestant.nationality,
            category=category,
            final_score=final_score,
            scores_detail=scores_detail,
        ))

    rankings.sort(key=lambda x: x.final_score, reverse=True)
    for idx, r in enumerate(rankings, start=1):
        r.rank = idx

    return CategoryRankingsOut(
        event_id=event_id,
        event_name=event.name,
        category=category,
        rankings=rankings,
    )


@router.get("/advancement/{event_id}/{category}", summary="按组别生成晋级名单")
def get_advancement_list(
    event_id: int,
    category: BeardCategory,
    top_n: int = Query(5, ge=1, le=20, description="晋级人数"),
    db: Session = Depends(get_db),
):
    rankings_data = get_category_rankings(event_id, category, db)

    advancing = rankings_data.rankings[:top_n]
    eliminated = rankings_data.rankings[top_n:]

    return AdvancementListOut(
        event_id=event_id,
        event_name=rankings_data.event_name,
        category=category,
        advancing=advancing,
        eliminated=eliminated,
    )


@router.get("/all-rankings/{event_id}", summary="获取赛事所有组别排名")
def get_all_category_rankings(event_id: int, db: Session = Depends(get_db)):
    event = db.query(ContestEvent).filter(ContestEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="赛事不存在")

    categories = (
        db.query(Registration.category)
        .filter(Registration.event_id == event_id, Registration.status == RegistrationStatus.APPROVED)
        .distinct()
        .all()
    )

    all_rankings = {}
    for (cat,) in categories:
        try:
            ranking_data = get_category_rankings(event_id, cat, db)
            all_rankings[cat.value] = ranking_data.rankings
        except HTTPException:
            continue

    return {
        "event_id": event_id,
        "event_name": event.name,
        "rankings_by_category": all_rankings,
    }
