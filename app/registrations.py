import random
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db
from app.models import Registration, ContestEvent, Contestant
from app.schemas import (
    RegistrationCreate, RegistrationReview, RegistrationOut,
    RegistrationDetailOut, MessageOut,
)
from app.enums import RegistrationStatus, EventStatus, BeardCategory

router = APIRouter(prefix="/registrations", tags=["选手报名"])


@router.post("", response_model=RegistrationOut, summary="选手在线报名")
def create_registration(data: RegistrationCreate, db: Session = Depends(get_db)):
    event = db.query(ContestEvent).filter(ContestEvent.id == data.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="赛事不存在")

    if event.status != EventStatus.REGISTRATION_OPEN:
        raise HTTPException(status_code=400, detail="该赛事当前未开放报名")

    contestant = db.query(Contestant).filter(Contestant.id == data.contestant_id).first()
    if not contestant:
        raise HTTPException(status_code=404, detail="选手不存在")

    existing = db.query(Registration).filter(
        Registration.contestant_id == data.contestant_id,
        Registration.event_id == data.event_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="该选手已报名此赛事")

    same_category = db.query(Registration).filter(
        Registration.contestant_id == data.contestant_id,
        Registration.event_id == data.event_id,
        Registration.category == data.category,
    ).first()
    if same_category:
        raise HTTPException(status_code=400, detail="该选手已报名此组别")

    registration = Registration(**data.model_dump())
    db.add(registration)
    db.commit()
    db.refresh(registration)
    return registration


@router.get("", response_model=List[RegistrationDetailOut], summary="查询报名列表")
def list_registrations(
    event_id: Optional[int] = Query(None),
    contestant_id: Optional[int] = Query(None),
    category: Optional[BeardCategory] = Query(None),
    status: Optional[RegistrationStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(Registration)
    if event_id:
        q = q.filter(Registration.event_id == event_id)
    if contestant_id:
        q = q.filter(Registration.contestant_id == contestant_id)
    if category:
        q = q.filter(Registration.category == category)
    if status:
        q = q.filter(Registration.status == status)

    registrations = q.offset(skip).limit(limit).all()

    results = []
    for reg in registrations:
        contestant = db.query(Contestant).filter(Contestant.id == reg.contestant_id).first()
        results.append(RegistrationDetailOut(
            id=reg.id,
            contestant_id=reg.contestant_id,
            event_id=reg.event_id,
            category=reg.category,
            status=reg.status,
            appearance_order=reg.appearance_order,
            registered_at=reg.registered_at,
            reviewed_at=reg.reviewed_at,
            contestant_name=contestant.name if contestant else None,
            contestant_nationality=contestant.nationality if contestant else None,
        ))
    return results


@router.get("/{registration_id}", response_model=RegistrationDetailOut, summary="获取报名详情")
def get_registration(registration_id: int, db: Session = Depends(get_db)):
    reg = db.query(Registration).filter(Registration.id == registration_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="报名记录不存在")

    contestant = db.query(Contestant).filter(Contestant.id == reg.contestant_id).first()
    return RegistrationDetailOut(
        id=reg.id,
        contestant_id=reg.contestant_id,
        event_id=reg.event_id,
        category=reg.category,
        status=reg.status,
        appearance_order=reg.appearance_order,
        registered_at=reg.registered_at,
        reviewed_at=reg.reviewed_at,
        contestant_name=contestant.name if contestant else None,
        contestant_nationality=contestant.nationality if contestant else None,
    )


@router.put("/{registration_id}/review", response_model=RegistrationOut, summary="管理员审核报名")
def review_registration(registration_id: int, data: RegistrationReview, db: Session = Depends(get_db)):
    reg = db.query(Registration).filter(Registration.id == registration_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="报名记录不存在")

    if reg.status != RegistrationStatus.PENDING:
        raise HTTPException(status_code=400, detail="该报名已审核，无法再次审核")

    reg.status = data.status
    reg.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(reg)
    return reg


@router.post("/events/{event_id}/generate-order", summary="生成分组出场顺序")
def generate_appearance_order(event_id: int, db: Session = Depends(get_db)):
    event = db.query(ContestEvent).filter(ContestEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="赛事不存在")

    registrations = (
        db.query(Registration)
        .filter(Registration.event_id == event_id, Registration.status == RegistrationStatus.APPROVED)
        .all()
    )

    if not registrations:
        raise HTTPException(status_code=400, detail="暂无已审核通过的报名")

    categories = {}
    for reg in registrations:
        cat = reg.category.value
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(reg)

    for cat, regs in categories.items():
        random.shuffle(regs)
        for idx, reg in enumerate(regs, start=1):
            reg.appearance_order = idx

    db.commit()
    return {"message": "出场顺序已生成", "categories": {cat: len(regs) for cat, regs in categories.items()}}
