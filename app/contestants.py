import os
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Contestant, ContestantPhoto, Registration, Score, Award, ContestEvent, ContestantPoints
from app.schemas import (
    ContestantCreate, ContestantUpdate, ContestantOut,
    ContestantPhotoOut, ContestantHistoryOut, ContestantPointsOut,
)
from app.enums import PhotoType, SCORING_DIMENSIONS

router = APIRouter(prefix="/contestants", tags=["选手档案"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("", response_model=ContestantOut, summary="录入选手档案")
def create_contestant(data: ContestantCreate, db: Session = Depends(get_db)):
    if data.email:
        existing = db.query(Contestant).filter(Contestant.email == data.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="该邮箱已被注册")
    contestant = Contestant(**data.model_dump())
    db.add(contestant)
    db.commit()
    db.refresh(contestant)
    return contestant


@router.get("", response_model=List[ContestantOut], summary="查询选手列表")
def list_contestants(
    nationality: Optional[str] = Query(None, description="按国籍筛选"),
    name: Optional[str] = Query(None, description="按姓名模糊搜索"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(Contestant).options(joinedload(Contestant.photos))
    if nationality:
        q = q.filter(Contestant.nationality == nationality)
    if name:
        q = q.filter(Contestant.name.contains(name))
    return q.offset(skip).limit(limit).all()


@router.get("/{contestant_id}", response_model=ContestantOut, summary="获取选手详情")
def get_contestant(contestant_id: int, db: Session = Depends(get_db)):
    contestant = db.query(Contestant).options(joinedload(Contestant.photos)).filter(Contestant.id == contestant_id).first()
    if not contestant:
        raise HTTPException(status_code=404, detail="选手不存在")
    return contestant


@router.put("/{contestant_id}", response_model=ContestantOut, summary="更新选手档案")
def update_contestant(contestant_id: int, data: ContestantUpdate, db: Session = Depends(get_db)):
    contestant = db.query(Contestant).filter(Contestant.id == contestant_id).first()
    if not contestant:
        raise HTTPException(status_code=404, detail="选手不存在")
    update_data = data.model_dump(exclude_unset=True)
    if "email" in update_data and update_data["email"]:
        existing = db.query(Contestant).filter(Contestant.email == update_data["email"], Contestant.id != contestant_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="该邮箱已被注册")
    for key, value in update_data.items():
        setattr(contestant, key, value)
    db.commit()
    db.refresh(contestant)
    return contestant


@router.delete("/{contestant_id}", summary="删除选手档案")
def delete_contestant(contestant_id: int, db: Session = Depends(get_db)):
    contestant = db.query(Contestant).filter(Contestant.id == contestant_id).first()
    if not contestant:
        raise HTTPException(status_code=404, detail="选手不存在")
    for photo in contestant.photos:
        photo_path = os.path.join(UPLOAD_DIR, photo.file_path)
        if os.path.exists(photo_path):
            os.remove(photo_path)
    db.delete(contestant)
    db.commit()
    return {"message": "选手档案已删除"}


@router.post("/{contestant_id}/photos", response_model=ContestantPhotoOut, summary="上传选手照片")
def upload_photo(
    contestant_id: int,
    photo_type: PhotoType = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    contestant = db.query(Contestant).filter(Contestant.id == contestant_id).first()
    if not contestant:
        raise HTTPException(status_code=404, detail="选手不存在")

    contestant_dir = os.path.join(UPLOAD_DIR, str(contestant_id))
    os.makedirs(contestant_dir, exist_ok=True)

    file_ext = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
    filename = f"{photo_type.value}_{len(contestant.photos) + 1}{file_ext}"
    file_path = os.path.join(contestant_dir, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    relative_path = f"{contestant_id}/{filename}"
    photo = ContestantPhoto(contestant_id=contestant_id, photo_type=photo_type, file_path=relative_path)
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


@router.delete("/photos/{photo_id}", summary="删除选手照片")
def delete_photo(photo_id: int, db: Session = Depends(get_db)):
    photo = db.query(ContestantPhoto).filter(ContestantPhoto.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="照片不存在")
    photo_path = os.path.join(UPLOAD_DIR, photo.file_path)
    if os.path.exists(photo_path):
        os.remove(photo_path)
    db.delete(photo)
    db.commit()
    return {"message": "照片已删除"}


@router.get("/{contestant_id}/history", response_model=List[ContestantHistoryOut], summary="选手历年参赛记录与获奖")
def get_contestant_history(contestant_id: int, db: Session = Depends(get_db)):
    contestant = db.query(Contestant).filter(Contestant.id == contestant_id).first()
    if not contestant:
        raise HTTPException(status_code=404, detail="选手不存在")

    registrations = (
        db.query(Registration)
        .filter(Registration.contestant_id == contestant_id)
        .all()
    )

    results = []
    for reg in registrations:
        event = db.query(ContestEvent).filter(ContestEvent.id == reg.event_id).first()

        scores = db.query(Score).filter(Score.registration_id == reg.id).all()
        final_score = None
        if scores:
            weighted_totals = [s.weighted_total for s in scores]
            if len(weighted_totals) >= 3:
                weighted_totals_sorted = sorted(weighted_totals)
                trimmed = weighted_totals_sorted[1:-1]
                final_score = round(sum(trimmed) / len(trimmed), 2) if trimmed else round(sum(weighted_totals) / len(weighted_totals), 2)
            else:
                final_score = round(sum(weighted_totals) / len(weighted_totals), 2)

        award = db.query(Award).filter(
            Award.contestant_id == contestant_id,
            Award.event_id == reg.event_id,
        ).first()

        results.append(ContestantHistoryOut(
            event_id=event.id,
            event_name=event.name,
            edition_number=event.edition_number,
            host_city=event.host_city,
            event_date=event.event_date,
            category=reg.category,
            status=reg.status,
            appearance_order=reg.appearance_order,
            final_score=final_score,
            award=award.award_type.value if award else None,
        ))

    return results


@router.get("/{contestant_id}/points", response_model=ContestantPointsOut, summary="选手积分信息")
def get_contestant_points(contestant_id: int, db: Session = Depends(get_db)):
    contestant = db.query(Contestant).filter(Contestant.id == contestant_id).first()
    if not contestant:
        raise HTTPException(status_code=404, detail="选手不存在")

    points = db.query(ContestantPoints).filter(ContestantPoints.contestant_id == contestant_id).first()
    if not points:
        return ContestantPointsOut(
            contestant_id=contestant_id,
            contestant_name=contestant.name,
            nationality=contestant.nationality,
            total_points=0,
            events_participated=0,
            gold_count=0,
            silver_count=0,
            bronze_count=0,
        )

    return ContestantPointsOut(
        contestant_id=contestant_id,
        contestant_name=contestant.name,
        nationality=contestant.nationality,
        total_points=points.total_points,
        events_participated=points.events_participated,
        gold_count=points.gold_count,
        silver_count=points.silver_count,
        bronze_count=points.bronze_count,
    )
