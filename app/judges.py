from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Judge, Score, Registration, Contestant, ContestEvent
from app.schemas import JudgeCreate, JudgeOut, ScoreCreate, ScoreOut
from app.enums import SCORING_DIMENSIONS, RegistrationStatus, EventStatus

router = APIRouter(prefix="/judges", tags=["评委管理"])


@router.post("", response_model=JudgeOut, summary="添加评委")
def create_judge(data: JudgeCreate, db: Session = Depends(get_db)):
    judge = Judge(**data.model_dump())
    db.add(judge)
    db.commit()
    db.refresh(judge)
    return judge


@router.get("", response_model=List[JudgeOut], summary="查询评委列表")
def list_judges(skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    return db.query(Judge).offset(skip).limit(limit).all()


@router.get("/{judge_id}", response_model=JudgeOut, summary="获取评委详情")
def get_judge(judge_id: int, db: Session = Depends(get_db)):
    judge = db.query(Judge).filter(Judge.id == judge_id).first()
    if not judge:
        raise HTTPException(status_code=404, detail="评委不存在")
    return judge


@router.delete("/{judge_id}", summary="删除评委")
def delete_judge(judge_id: int, db: Session = Depends(get_db)):
    judge = db.query(Judge).filter(Judge.id == judge_id).first()
    if not judge:
        raise HTTPException(status_code=404, detail="评委不存在")
    db.delete(judge)
    db.commit()
    return {"message": "评委已删除"}
