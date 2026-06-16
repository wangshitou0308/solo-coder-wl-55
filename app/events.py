from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db
from app.models import ContestEvent, Registration
from app.schemas import ContestEventCreate, ContestEventUpdate, ContestEventOut, MessageOut
from app.enums import EventStatus, RegistrationStatus, BeardCategory

router = APIRouter(prefix="/events", tags=["赛事管理"])


@router.post("", response_model=ContestEventOut, summary="创建赛事届次")
def create_event(data: ContestEventCreate, db: Session = Depends(get_db)):
    if data.registration_start >= data.registration_end:
        raise HTTPException(status_code=400, detail="报名开始时间必须早于结束时间")
    if data.registration_end >= data.event_date:
        raise HTTPException(status_code=400, detail="报名结束时间必须早于比赛日期")

    existing = db.query(ContestEvent).filter(ContestEvent.edition_number == data.edition_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="该届次编号已存在")

    event = ContestEvent(**data.model_dump())
    now = datetime.utcnow()
    reg_start = data.registration_start.replace(tzinfo=None) if data.registration_start.tzinfo else data.registration_start
    reg_end = data.registration_end.replace(tzinfo=None) if data.registration_end.tzinfo else data.registration_end
    if reg_start <= now <= reg_end:
        event.status = EventStatus.REGISTRATION_OPEN
    else:
        event.status = EventStatus.DRAFT

    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("", response_model=List[ContestEventOut], summary="查询赛事列表")
def list_events(
    status: Optional[EventStatus] = Query(None, description="按状态筛选"),
    host_country: Optional[str] = Query(None, description="按举办国筛选"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(ContestEvent)
    if status:
        q = q.filter(ContestEvent.status == status)
    if host_country:
        q = q.filter(ContestEvent.host_country == host_country)
    return q.order_by(ContestEvent.edition_number.desc()).offset(skip).limit(limit).all()


@router.get("/{event_id}", response_model=ContestEventOut, summary="获取赛事详情")
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(ContestEvent).filter(ContestEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="赛事不存在")
    return event


@router.put("/{event_id}", response_model=ContestEventOut, summary="更新赛事信息")
def update_event(event_id: int, data: ContestEventUpdate, db: Session = Depends(get_db)):
    event = db.query(ContestEvent).filter(ContestEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="赛事不存在")

    update_data = data.model_dump(exclude_unset=True)

    new_reg_start = update_data.get("registration_start", event.registration_start)
    new_reg_end = update_data.get("registration_end", event.registration_end)
    new_event_date = update_data.get("event_date", event.event_date)

    if new_reg_start and new_reg_end:
        reg_start_naive = new_reg_start.replace(tzinfo=None) if new_reg_start.tzinfo else new_reg_start
        reg_end_naive = new_reg_end.replace(tzinfo=None) if new_reg_end.tzinfo else new_reg_end
        if reg_start_naive >= reg_end_naive:
            raise HTTPException(status_code=400, detail="报名开始时间必须早于结束时间")

    if new_reg_end and new_event_date:
        reg_end_naive = new_reg_end.replace(tzinfo=None) if new_reg_end.tzinfo else new_reg_end
        event_date_naive = new_event_date.replace(tzinfo=None) if new_event_date.tzinfo else new_event_date
        if reg_end_naive >= event_date_naive:
            raise HTTPException(status_code=400, detail="报名结束时间必须早于比赛日期")

    for key, value in update_data.items():
        setattr(event, key, value)

    if event.registration_start and event.registration_end:
        now = datetime.utcnow()
        reg_start = event.registration_start.replace(tzinfo=None) if event.registration_start.tzinfo else event.registration_start
        reg_end = event.registration_end.replace(tzinfo=None) if event.registration_end.tzinfo else event.registration_end
        if event.status == EventStatus.DRAFT and reg_start <= now <= reg_end:
            event.status = EventStatus.REGISTRATION_OPEN

    db.commit()
    db.refresh(event)
    return event


@router.put("/{event_id}/status", response_model=ContestEventOut, summary="更新赛事状态")
def update_event_status(event_id: int, status: EventStatus, db: Session = Depends(get_db)):
    event = db.query(ContestEvent).filter(ContestEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="赛事不存在")
    event.status = status
    db.commit()
    db.refresh(event)
    return event


@router.get("/{event_id}/group-list", summary="获取赛事分组名单与出场顺序")
def get_group_list(event_id: int, db: Session = Depends(get_db)):
    event = db.query(ContestEvent).filter(ContestEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="赛事不存在")

    registrations = (
        db.query(Registration)
        .filter(Registration.event_id == event_id, Registration.status == RegistrationStatus.APPROVED)
        .order_by(Registration.category, Registration.appearance_order)
        .all()
    )

    groups = {}
    for reg in registrations:
        cat = reg.category.value
        if cat not in groups:
            groups[cat] = []
        groups[cat].append({
            "registration_id": reg.id,
            "contestant_id": reg.contestant_id,
            "contestant_name": reg.contestant.name,
            "nationality": reg.contestant.nationality,
            "appearance_order": reg.appearance_order,
        })

    return {
        "event_id": event_id,
        "event_name": event.name,
        "edition_number": event.edition_number,
        "groups": groups,
    }
