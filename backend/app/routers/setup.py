from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models import (AssessmentCycle, Competency, Department, JobScope,
                        JobScopeCompetency, Question, SupervisorAnswer, SurveyAnswer)
from app.schemas.setup import (CycleCreate, NameIn, QuestionCreate,
                               QuestionUpdate, RequiredLevelIn)
from app.services.cycles import get_cycle

router = APIRouter(prefix="/setup", tags=["HR setup"],
                   dependencies=[Depends(require_role("hr"))])


def _answer_count(db: Session, question_id: int) -> int:
    staff = db.scalar(select(func.count()).select_from(SurveyAnswer)
                      .where(SurveyAnswer.question_id == question_id)) or 0
    sup = db.scalar(select(func.count()).select_from(SupervisorAnswer)
                    .where(SupervisorAnswer.question_id == question_id)) or 0
    return staff + sup


def _pair_exists(db: Session, scope_id: int, comp_id: int) -> bool:
    return db.scalar(select(JobScopeCompetency).where(
        JobScopeCompetency.job_scope_id == scope_id,
        JobScopeCompetency.competency_id == comp_id)) is not None


# ---------- overview (one call for the whole setup screen) ----------

@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    comps = {c.id: c.name for c in db.scalars(select(Competency).order_by(Competency.name))}
    scopes = []
    for s in db.scalars(select(JobScope).order_by(JobScope.name)):
        levels = db.scalars(select(JobScopeCompetency)
                            .where(JobScopeCompetency.job_scope_id == s.id)
                            .order_by(JobScopeCompetency.competency_id))
        questions = db.scalars(select(Question).where(Question.job_scope_id == s.id)
                               .order_by(Question.id))
        scopes.append({
            "id": s.id, "name": s.name,
            "competencies": [{"competency_id": l.competency_id, "name": comps[l.competency_id],
                              "required_level": l.required_level} for l in levels],
            "questions": [{"id": q.id, "competency_id": q.competency_id,
                           "competency": comps[q.competency_id], "text": q.text,
                           "is_negative": q.is_negative,
                           "answer_count": _answer_count(db, q.id)} for q in questions],
        })
    return {"job_scopes": scopes,
            "competencies": [{"id": i, "name": n} for i, n in comps.items()],
            "departments": [{"id": d.id, "name": d.name} for d in db.scalars(select(Department))]}


# ---------- job scopes and competencies ----------

@router.post("/job-scopes", status_code=201)
def create_job_scope(body: NameIn, db: Session = Depends(get_db)):
    if db.scalar(select(JobScope).where(JobScope.name == body.name.strip())):
        raise HTTPException(409, "A job scope with this name already exists")
    s = JobScope(name=body.name.strip())
    db.add(s)
    db.commit()
    return {"id": s.id, "name": s.name}


@router.post("/competencies", status_code=201)
def create_competency(body: NameIn, db: Session = Depends(get_db)):
    if db.scalar(select(Competency).where(Competency.name == body.name.strip())):
        raise HTTPException(409, "A competency with this name already exists")
    c = Competency(name=body.name.strip())
    db.add(c)
    db.commit()
    return {"id": c.id, "name": c.name}


@router.put("/job-scopes/{scope_id}/competencies/{competency_id}")
def set_required_level(scope_id: int, competency_id: int, body: RequiredLevelIn,
                       db: Session = Depends(get_db)):
    """Add a competency to a job scope, or change its required level."""
    if db.get(JobScope, scope_id) is None or db.get(Competency, competency_id) is None:
        raise HTTPException(404, "Job scope or competency not found")
    row = db.scalar(select(JobScopeCompetency).where(
        JobScopeCompetency.job_scope_id == scope_id,
        JobScopeCompetency.competency_id == competency_id))
    if row:
        row.required_level = body.required_level
    else:
        db.add(JobScopeCompetency(job_scope_id=scope_id, competency_id=competency_id,
                                  required_level=body.required_level))
    db.commit()
    return {"job_scope_id": scope_id, "competency_id": competency_id,
            "required_level": body.required_level}


@router.delete("/job-scopes/{scope_id}/competencies/{competency_id}")
def remove_competency_from_scope(scope_id: int, competency_id: int,
                                 db: Session = Depends(get_db)):
    row = db.scalar(select(JobScopeCompetency).where(
        JobScopeCompetency.job_scope_id == scope_id,
        JobScopeCompetency.competency_id == competency_id))
    if row is None:
        raise HTTPException(404, "Not found")
    if db.scalar(select(Question).where(Question.job_scope_id == scope_id,
                                        Question.competency_id == competency_id)):
        raise HTTPException(409, "Delete this competency's questions first")
    db.delete(row)
    db.commit()
    return {"deleted": True}


# ---------- questions ----------

@router.post("/questions", status_code=201)
def create_question(body: QuestionCreate, db: Session = Depends(get_db)):
    if not _pair_exists(db, body.job_scope_id, body.competency_id):
        raise HTTPException(400, "Add this competency (with a required level) to the job scope first")
    q = Question(job_scope_id=body.job_scope_id, competency_id=body.competency_id,
                 text=body.text.strip(), is_negative=body.is_negative)
    db.add(q)
    db.commit()
    return {"id": q.id}


@router.put("/questions/{question_id}")
def update_question(question_id: int, body: QuestionUpdate, db: Session = Depends(get_db)):
    q = db.get(Question, question_id)
    if q is None:
        raise HTTPException(404, "Question not found")
    if body.is_negative is not None and body.is_negative != q.is_negative \
            and _answer_count(db, q.id):
        raise HTTPException(409, "Staff or supervisors have already answered this question, so its wording "
                                 "direction cannot be flipped")
    if body.text is not None:
        q.text = body.text.strip()
    if body.is_negative is not None:
        q.is_negative = body.is_negative
    db.commit()
    return {"id": q.id}


@router.delete("/questions/{question_id}")
def delete_question(question_id: int, force: bool = False, db: Session = Depends(get_db)):
    """Refused (409) if anyone has answered it, unless force=true, which also deletes those answers."""
    q = db.get(Question, question_id)
    if q is None:
        raise HTTPException(404, "Question not found")
    count = _answer_count(db, q.id)
    if count and not force:
        raise HTTPException(409, f"{count} answer(s) already exist for this question. "
                                 "Confirm in the screen to delete it together with its answers.")
    if count:
        db.execute(delete(SurveyAnswer).where(SurveyAnswer.question_id == q.id))
        db.execute(delete(SupervisorAnswer).where(SupervisorAnswer.question_id == q.id))
    db.delete(q)
    db.commit()
    return {"deleted": True}


# ---------- assessment cycles ----------

@router.get("/cycles")
def list_cycles(db: Session = Depends(get_db)):
    return [{"id": c.id, "year": c.year, "is_open": c.is_open}
            for c in db.scalars(select(AssessmentCycle).order_by(AssessmentCycle.year.desc()))]


@router.post("/cycles", status_code=201)
def create_cycle(body: CycleCreate, db: Session = Depends(get_db)):
    if db.scalar(select(AssessmentCycle).where(AssessmentCycle.year == body.year)):
        raise HTTPException(409, "A cycle for this year already exists")
    c = AssessmentCycle(year=body.year, is_open=True)
    db.add(c)
    db.commit()
    return {"id": c.id, "year": c.year, "is_open": c.is_open}


@router.post("/cycles/{cycle_id}/close")
def close_cycle(cycle_id: int, db: Session = Depends(get_db)):
    cycle = get_cycle(db, cycle_id)
    cycle.is_open = False
    db.commit()
    return {"id": cycle.id, "is_open": cycle.is_open}


@router.post("/cycles/{cycle_id}/open")
def open_cycle(cycle_id: int, db: Session = Depends(get_db)):
    cycle = get_cycle(db, cycle_id)
    cycle.is_open = True
    db.commit()
    return {"id": cycle.id, "is_open": cycle.is_open}
