from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models import (Competency, JobScopeCompetency, Question,
                        SupervisorAnswer, User)
from app.schemas.survey import RatingSubmit
from app.services.cycles import assert_open, get_cycle

router = APIRouter(prefix="/rating", tags=["supervisor rating"])


def _questions(db: Session, staff: User) -> list[Question]:
    """The supervisor answers the same questions as the staff member's job scope survey."""
    return list(db.scalars(select(Question).where(Question.job_scope_id == staff.job_scope_id)
                           .order_by(Question.id)))


def _my_report(db: Session, supervisor: User, staff_id: int) -> User:
    staff = db.get(User, staff_id)
    if staff is None or staff.supervisor_id != supervisor.id:
        raise HTTPException(403, "You can only rate your own direct reports")
    return staff


def rating_status(rated: int, total: int) -> str:
    return "Not started" if rated == 0 else "Complete" if rated >= total else "Partial"


@router.get("/team")
def my_team(cycle_id: int | None = None, sup: User = Depends(require_role("supervisor")),
            db: Session = Depends(get_db)):
    cycle = get_cycle(db, cycle_id)
    team = db.scalars(select(User).where(User.supervisor_id == sup.id).order_by(User.name))
    out = []
    for s in team:
        total = len(_questions(db, s))
        rated = db.scalar(select(func.count()).select_from(SupervisorAnswer)
                          .where(SupervisorAnswer.staff_id == s.id,
                                 SupervisorAnswer.cycle_id == cycle.id))
        out.append({"staff_id": s.id, "name": s.name, "rated": rated, "total": total,
                    "status": rating_status(rated, total)})
    return {"cycle": {"id": cycle.id, "year": cycle.year, "is_open": cycle.is_open},
            "team": out}


@router.get("/{staff_id}")
def get_ratings(staff_id: int, cycle_id: int | None = None,
                sup: User = Depends(require_role("supervisor")),
                db: Session = Depends(get_db)):
    staff = _my_report(db, sup, staff_id)
    cycle = get_cycle(db, cycle_id)
    given = {r.question_id: r.answer for r in db.scalars(
        select(SupervisorAnswer).where(SupervisorAnswer.staff_id == staff.id,
                                       SupervisorAnswer.cycle_id == cycle.id))}
    comp_names = {c.id: c.name for c in db.scalars(select(Competency))}
    required = {j.competency_id: j.required_level for j in db.scalars(
        select(JobScopeCompetency).where(JobScopeCompetency.job_scope_id == staff.job_scope_id))}
    return {"staff": {"id": staff.id, "name": staff.name},
            "cycle": {"id": cycle.id, "year": cycle.year, "is_open": cycle.is_open},
            "questions": [{"question_id": q.id, "competency": comp_names[q.competency_id],
                           "required": required.get(q.competency_id), "text": q.text,
                           "rating": given.get(q.id)} for q in _questions(db, staff)]}


@router.put("/{staff_id}")
def save_ratings(staff_id: int, body: RatingSubmit,
                 sup: User = Depends(require_role("supervisor")),
                 db: Session = Depends(get_db)):
    staff = _my_report(db, sup, staff_id)
    cycle = get_cycle(db, body.cycle_id)
    assert_open(cycle)
    valid = {q.id for q in _questions(db, staff)}
    for r in body.ratings:
        if r.question_id not in valid:
            raise HTTPException(400, f"Question {r.question_id} is not in this staff member's job scope")
    existing = {r.question_id: r for r in db.scalars(
        select(SupervisorAnswer).where(SupervisorAnswer.staff_id == staff.id,
                                       SupervisorAnswer.cycle_id == cycle.id))}
    for r in body.ratings:
        row = existing.get(r.question_id)
        if row:
            row.answer = r.rating
            row.supervisor_id = sup.id
        else:
            db.add(SupervisorAnswer(supervisor_id=sup.id, staff_id=staff.id, cycle_id=cycle.id,
                                    question_id=r.question_id, answer=r.rating))
    db.commit()
    return {"saved": len(body.ratings)}
