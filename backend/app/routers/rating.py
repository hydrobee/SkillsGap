from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models import Competency, JobScopeCompetency, SupervisorRating, User
from app.schemas.survey import RatingSubmit
from app.services.cycles import assert_open, get_cycle

router = APIRouter(prefix="/rating", tags=["supervisor rating"])


def _competencies(db: Session, staff: User, cycle_id: int) -> list[tuple[Competency, int]]:
    """The competencies of the staff member's job scope for this cycle, with the required level of each."""
    rows = db.execute(select(Competency, JobScopeCompetency.required_level)
                      .join(JobScopeCompetency, JobScopeCompetency.competency_id == Competency.id)
                      .where(JobScopeCompetency.job_scope_id == staff.job_scope_id,
                             JobScopeCompetency.cycle_id == cycle_id)
                      .order_by(Competency.id)).all()
    return [(c, lvl) for c, lvl in rows]


def _given(db: Session, staff: User, cycle_id: int) -> dict[int, int]:
    return {r.competency_id: r.rating for r in db.scalars(
        select(SupervisorRating).where(SupervisorRating.staff_id == staff.id,
                                       SupervisorRating.cycle_id == cycle_id))}


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
        comps = _competencies(db, s, cycle.id)
        given = _given(db, s, cycle.id)
        rated = sum(1 for c, _ in comps if c.id in given)
        out.append({"staff_id": s.id, "name": s.name, "rated": rated, "total": len(comps),
                    "status": rating_status(rated, len(comps))})
    return {"cycle": {"id": cycle.id, "year": cycle.year, "is_open": cycle.is_open},
            "team": out}


@router.get("/{staff_id}")
def get_ratings(staff_id: int, cycle_id: int | None = None,
                sup: User = Depends(require_role("supervisor")),
                db: Session = Depends(get_db)):
    staff = _my_report(db, sup, staff_id)
    cycle = get_cycle(db, cycle_id)
    given = _given(db, staff, cycle.id)
    return {"staff": {"id": staff.id, "name": staff.name},
            "cycle": {"id": cycle.id, "year": cycle.year, "is_open": cycle.is_open},
            "competencies": [{"competency_id": c.id, "competency": c.name, "required": lvl,
                              "rating": given.get(c.id)} for c, lvl in _competencies(db, staff, cycle.id)]}


@router.put("/{staff_id}")
def save_ratings(staff_id: int, body: RatingSubmit,
                 sup: User = Depends(require_role("supervisor")),
                 db: Session = Depends(get_db)):
    staff = _my_report(db, sup, staff_id)
    cycle = get_cycle(db, body.cycle_id)
    assert_open(cycle)
    valid = {c.id for c, _ in _competencies(db, staff, cycle.id)}
    for r in body.ratings:
        if r.competency_id not in valid:
            raise HTTPException(400, f"Competency {r.competency_id} is not in this staff member's job scope")
    existing = {r.competency_id: r for r in db.scalars(
        select(SupervisorRating).where(SupervisorRating.staff_id == staff.id,
                                       SupervisorRating.cycle_id == cycle.id))}
    for r in body.ratings:
        row = existing.get(r.competency_id)
        if row:
            row.rating = r.rating
            row.supervisor_id = sup.id
        else:
            db.add(SupervisorRating(supervisor_id=sup.id, staff_id=staff.id, cycle_id=cycle.id,
                                    competency_id=r.competency_id, rating=r.rating))
    db.commit()
    return {"saved": len(body.ratings)}
