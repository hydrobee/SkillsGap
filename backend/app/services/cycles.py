from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AssessmentCycle


def get_cycle(db: Session, cycle_id: int | None = None) -> AssessmentCycle:
    """A given cycle, or the latest year if cycle_id is not supplied."""
    if cycle_id is not None:
        cycle = db.get(AssessmentCycle, cycle_id)
    else:
        cycle = db.scalar(select(AssessmentCycle).order_by(AssessmentCycle.year.desc()))
    if cycle is None:
        raise HTTPException(404, "Assessment cycle not found")
    return cycle


def assert_open(cycle: AssessmentCycle) -> None:
    if not cycle.is_open:
        raise HTTPException(409, "This assessment cycle is closed")