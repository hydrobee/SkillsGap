from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import assert_can_view, get_current_user
from app.models import AssessmentCycle, Department, JobScope, User
from app.services.cycles import get_cycle
from app.services.reports import department_report, individual_report

router = APIRouter(prefix="/reports", tags=["reports"])


def _person(u: User, scopes: dict, depts: dict) -> dict:
    return {"id": u.id, "name": u.name, "role": u.role,
            "job_scope": scopes.get(u.job_scope_id), "department": depts.get(u.department_id)}


@router.get("/cycles")
def cycles(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Assessment cycles, newest first. Any logged-in user may list them."""
    return [{"id": c.id, "year": c.year, "is_open": c.is_open}
            for c in db.scalars(select(AssessmentCycle).order_by(AssessmentCycle.year.desc()))]


@router.get("/people")
def people_i_can_view(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Who the logged-in user may open an individual report for."""
    if user.role == "hr":
        q = select(User).where(User.job_scope_id.is_not(None))
    elif user.role == "supervisor":
        q = select(User).where((User.id == user.id) | (User.supervisor_id == user.id))
    else:
        q = select(User).where(User.id == user.id)
    scopes = {s.id: s.name for s in db.scalars(select(JobScope))}
    depts = {d.id: d.name for d in db.scalars(select(Department))}
    return [_person(u, scopes, depts) for u in db.scalars(q.order_by(User.name))]


@router.get("/individual/{user_id}")
def individual(user_id: int, cycle_id: int | None = None,
               viewer: User = Depends(get_current_user), db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "User not found")
    assert_can_view(viewer, target)
    if target.job_scope_id is None:
        raise HTTPException(400, "This user has no job scope, so there is no report")
    return individual_report(db, target, get_cycle(db, cycle_id))


@router.get("/me")
def my_report(cycle_id: int | None = None, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    return individual(user.id, cycle_id, user, db)


@router.get("/departments")
def departments_i_can_view(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role == "hr":
        q = select(Department)
    elif user.role == "supervisor" and user.department_id:
        q = select(Department).where(Department.id == user.department_id)
    else:
        raise HTTPException(403, "Department reports are for supervisors and HR")
    return [{"id": d.id, "name": d.name} for d in db.scalars(q.order_by(Department.name))]


@router.get("/department/{department_id}")
def department(department_id: int, cycle_id: int | None = None,
               viewer: User = Depends(get_current_user), db: Session = Depends(get_db)):
    dept = db.get(Department, department_id)
    if dept is None:
        raise HTTPException(404, "Department not found")
    allowed = viewer.role == "hr" or (viewer.role == "supervisor"
                                      and viewer.department_id == dept.id)
    if not allowed:
        raise HTTPException(403, "You cannot view this department report")
    return department_report(db, dept, get_cycle(db, cycle_id))
