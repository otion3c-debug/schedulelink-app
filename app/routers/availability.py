from datetime import time
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import AvailabilityRule, User
from ..security import get_current_user
import uuid

router = APIRouter(prefix="/availability", tags=["availability"])

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def parse_time(value: str) -> time:
    parts = value.split(":")
    if len(parts) < 2 or len(parts) > 3:
        raise ValueError("Invalid time format")
    return time(hour=int(parts[0]), minute=int(parts[1]))


class RuleIn(BaseModel):
    day_of_week: int
    start_time: str
    end_time: str

    @field_validator("day_of_week")
    @classmethod
    def _check_day(cls, v):
        if v < 0 or v > 6:
            raise ValueError("day_of_week must be 0-6")
        return v


class RuleBulkIn(BaseModel):
    rules: List[RuleIn]


def _serialize(r: AvailabilityRule) -> dict:
    return {
        "id": str(r.id),
        "day_of_week": r.day_of_week,
        "day_name": DAY_NAMES[r.day_of_week],
        "start_time": r.start_time.strftime("%H:%M"),
        "end_time": r.end_time.strftime("%H:%M"),
        "is_active": r.is_active,
    }


@router.get("")
def list_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rules = (
        db.query(AvailabilityRule)
        .filter(AvailabilityRule.user_id == current_user.id)
        .order_by(AvailabilityRule.day_of_week, AvailabilityRule.start_time)
        .all()
    )
    return {"rules": [_serialize(r) for r in rules]}


@router.post("")
def create_rule(
    body: RuleIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    start = parse_time(body.start_time)
    end = parse_time(body.end_time)
    if start >= end:
        raise HTTPException(400, "start_time must be before end_time")
    rule = AvailabilityRule(
        user_id=current_user.id,
        day_of_week=body.day_of_week,
        start_time=start,
        end_time=end,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return _serialize(rule)


@router.put("/bulk")
def bulk_replace(
    body: RuleBulkIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.query(AvailabilityRule).filter(AvailabilityRule.user_id == current_user.id).delete()
    out = []
    for r in body.rules:
        start = parse_time(r.start_time)
        end = parse_time(r.end_time)
        if start >= end:
            raise HTTPException(400, "start_time must be before end_time")
        rule = AvailabilityRule(
            user_id=current_user.id,
            day_of_week=r.day_of_week,
            start_time=start,
            end_time=end,
        )
        db.add(rule)
        db.flush()
        out.append(_serialize(rule))
    db.commit()
    return {"rules": out}


@router.delete("/{rule_id}")
def delete_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rule = db.query(AvailabilityRule).filter(
        AvailabilityRule.id == uuid.UUID(rule_id),
        AvailabilityRule.user_id == current_user.id,
    ).first()
    if not rule:
        raise HTTPException(404, "Rule not found")
    db.delete(rule)
    db.commit()
    return {"success": True}
