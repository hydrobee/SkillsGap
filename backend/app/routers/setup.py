from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models import (AssessmentCycle, Competency, Department, JobScope,
                        JobScopeCompetency, Question, SupervisorRating,
                        SurveyAnswer, User)
from app.schemas.setup import (CopyLevelsIn, CycleCreate, NameIn, QuestionCreate,
                               QuestionUpdate, RequiredLevelIn)
from app.services.cycles import get_cycle

router = APIRouter(prefix="/setup", tags=["HR setup"],
                   dependencies=[Depends(require_role("hr"))])


def _answer_count(db: Session, question_id: int) -> int:
    return db.scalar(select(func.count()).select_from(SurveyAnswer)
                     .where(SurveyAnswer.question_id == question_id)) or 0


def _pair_exists(db: Session, scope_id: int, comp_id: int) -> bool:
    """True if the competency is in the job scope in any year (questions are not versioned by year)."""
    return db.scalar(select(JobScopeCompetency).where(
        JobScopeCompetency.job_scope_id == scope_id,
        JobScopeCompetency.competency_id == comp_id).limit(1)) is not None


def _level_row(db: Session, scope_id: int, comp_id: int, cycle_id: int):
    return db.scalar(select(JobScopeCompetency).where(
        JobScopeCompetency.job_scope_id == scope_id,
        JobScopeCompetency.competency_id == comp_id,
        JobScopeCompetency.cycle_id == cycle_id))


def _copy_levels(db: Session, source: AssessmentCycle, target: AssessmentCycle) -> int:
    """Copy required levels from one year to another. Existing rows in the target are kept."""
    have = {(r.job_scope_id, r.competency_id) for r in db.scalars(
        select(JobScopeCompetency).where(JobScopeCompetency.cycle_id == target.id))}
    copied = 0
    for r in db.scalars(select(JobScopeCompetency).where(JobScopeCompetency.cycle_id == source.id)):
        if (r.job_scope_id, r.competency_id) not in have:
            db.add(JobScopeCompetency(job_scope_id=r.job_scope_id, competency_id=r.competency_id,
                                      cycle_id=target.id, required_level=r.required_level))
            copied += 1
    return copied


# ---------- overview (one call for the whole setup screen) ----------

@router.get("/overview")
def overview(cycle_id: int | None = None, db: Session = Depends(get_db)):
    """Everything for the setup screen. Required levels are those of the chosen year (default: latest)."""
    cycle = get_cycle(db, cycle_id)
    comps = {c.id: c.name for c in db.scalars(select(Competency).order_by(Competency.name))}
    scopes = []
    for s in db.scalars(select(JobScope).order_by(JobScope.name)):
        levels = db.scalars(select(JobScopeCompetency)
                            .where(JobScopeCompetency.job_scope_id == s.id,
                                   JobScopeCompetency.cycle_id == cycle.id)
                            .order_by(JobScopeCompetency.competency_id))
        questions = db.scalars(select(Question).where(Question.job_scope_id == s.id)
                               .order_by(Question.id))
        scopes.append({
            "id": s.id, "name": s.name,
            "staff_count": db.scalar(select(func.count()).select_from(User)
                                     .where(User.job_scope_id == s.id)) or 0,
            "competencies": [{"competency_id": l.competency_id, "name": comps[l.competency_id],
                              "required_level": l.required_level} for l in levels],
            "questions": [{"id": q.id, "competency_id": q.competency_id,
                           "competency": comps[q.competency_id], "text": q.text,
                           "is_negative": q.is_negative,
                           "answer_count": _answer_count(db, q.id)} for q in questions],
        })
    used_by: dict[int, list[str]] = {}
    for comp_id, scope_name in db.execute(
            select(JobScopeCompetency.competency_id, JobScope.name)
            .join(JobScope, JobScope.id == JobScopeCompetency.job_scope_id).distinct()
            .order_by(JobScope.name)):
        used_by.setdefault(comp_id, []).append(scope_name)
    return {"cycle": {"id": cycle.id, "year": cycle.year, "is_open": cycle.is_open},
            "job_scopes": scopes,
            "competencies": [{"id": i, "name": n, "used_by": used_by.get(i, [])}
                             for i, n in comps.items()],
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


@router.delete("/job-scopes/{scope_id}")
def delete_job_scope(scope_id: int, db: Session = Depends(get_db)):
    """Delete a job scope together with its questions and its required levels in every year.
    Refused while staff are assigned to it or any survey answer was recorded for its questions."""
    scope = db.get(JobScope, scope_id)
    if scope is None:
        raise HTTPException(404, "Job scope not found")
    staff = db.scalar(select(func.count()).select_from(User).where(User.job_scope_id == scope_id)) or 0
    if staff:
        raise HTTPException(409, f"{staff} staff member(s) are assigned to {scope.name}. "
                                 "Move them to another job scope before deleting it.")
    qids = list(db.scalars(select(Question.id).where(Question.job_scope_id == scope_id)))
    answers = (db.scalar(select(func.count()).select_from(SurveyAnswer)
                         .where(SurveyAnswer.question_id.in_(qids))) or 0) if qids else 0
    if answers:
        raise HTTPException(409, f"{answers} survey answer(s) were recorded for the questions of {scope.name}, "
                                 "so it cannot be deleted without changing past reports.")
    levels = db.execute(delete(JobScopeCompetency).where(JobScopeCompetency.job_scope_id == scope_id)).rowcount
    db.execute(delete(Question).where(Question.job_scope_id == scope_id))
    db.delete(scope)
    db.commit()
    return {"deleted": True, "questions": len(qids), "levels": levels}


@router.delete("/competencies/{competency_id}")
def delete_competency(competency_id: int, db: Session = Depends(get_db)):
    """Delete a competency that no job scope uses (in any year) and nobody has been rated on."""
    comp = db.get(Competency, competency_id)
    if comp is None:
        raise HTTPException(404, "Competency not found")
    used = list(db.scalars(select(JobScope.name).join(JobScopeCompetency,
                                                     JobScopeCompetency.job_scope_id == JobScope.id)
                           .where(JobScopeCompetency.competency_id == competency_id)
                           .distinct().order_by(JobScope.name)))
    if used:
        raise HTTPException(409, f"{comp.name} is used by {len(used)} job scope(s): {', '.join(used)}. "
                                 "Remove it from them first.")
    if db.scalar(select(Question.id).where(Question.competency_id == competency_id).limit(1)):
        raise HTTPException(409, f"{comp.name} still has survey questions. Delete the questions first.")
    ratings = db.scalar(select(func.count()).select_from(SupervisorRating)
                        .where(SupervisorRating.competency_id == competency_id)) or 0
    if ratings:
        raise HTTPException(409, f"{ratings} supervisor rating(s) exist for {comp.name}, "
                                 "so it cannot be deleted without changing past reports.")
    db.delete(comp)
    db.commit()
    return {"deleted": True}


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
                       cycle_id: int | None = None, db: Session = Depends(get_db)):
    """Add a competency to a job scope, or change its required level, for one year (default: latest)."""
    if db.get(JobScope, scope_id) is None or db.get(Competency, competency_id) is None:
        raise HTTPException(404, "Job scope or competency not found")
    cycle = get_cycle(db, cycle_id)
    row = _level_row(db, scope_id, competency_id, cycle.id)
    if row:
        row.required_level = body.required_level
    else:
        db.add(JobScopeCompetency(job_scope_id=scope_id, competency_id=competency_id,
                                  cycle_id=cycle.id, required_level=body.required_level))
    db.commit()
    return {"job_scope_id": scope_id, "competency_id": competency_id,
            "year": cycle.year, "required_level": body.required_level}


@router.delete("/job-scopes/{scope_id}/competencies/{competency_id}")
def remove_competency_from_scope(scope_id: int, competency_id: int,
                                 cycle_id: int | None = None, db: Session = Depends(get_db)):
    cycle = get_cycle(db, cycle_id)
    row = _level_row(db, scope_id, competency_id, cycle.id)
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
        raise HTTPException(409, "Staff have already answered this question, so its wording "
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
    db.delete(q)
    db.commit()
    return {"deleted": True}


# ---------- assessment cycles ----------

@router.get("/cycles")
def list_cycles(db: Session = Depends(get_db)):
    def n(model, cid):
        return db.scalar(select(func.count()).select_from(model).where(model.cycle_id == cid)) or 0
    return [{"id": c.id, "year": c.year, "is_open": c.is_open,
             "levels": n(JobScopeCompetency, c.id), "answers": n(SurveyAnswer, c.id),
             "ratings": n(SupervisorRating, c.id)}
            for c in db.scalars(select(AssessmentCycle).order_by(AssessmentCycle.year.desc()))]


@router.post("/cycles", status_code=201)
def create_cycle(body: CycleCreate, db: Session = Depends(get_db)):
    if db.scalar(select(AssessmentCycle).where(AssessmentCycle.year == body.year)):
        raise HTTPException(409, "A cycle for this year already exists")
    source = None
    if body.copy_from_cycle_id is not None:
        source = db.get(AssessmentCycle, body.copy_from_cycle_id)
        if source is None:
            raise HTTPException(404, "The year to copy required levels from was not found")
    c = AssessmentCycle(year=body.year, is_open=True)
    db.add(c)
    db.flush()
    copied = _copy_levels(db, source, c) if source else 0
    db.commit()
    return {"id": c.id, "year": c.year, "is_open": c.is_open, "levels_copied": copied}


@router.post("/cycles/{cycle_id}/copy-levels")
def copy_levels(cycle_id: int, body: CopyLevelsIn, db: Session = Depends(get_db)):
    """Fill a year with another year's required levels. Levels already set in this year are kept."""
    target, source = get_cycle(db, cycle_id), get_cycle(db, body.from_cycle_id)
    if target.id == source.id:
        raise HTTPException(400, "Choose a different year to copy from")
    copied = _copy_levels(db, source, target)
    db.commit()
    return {"year": target.year, "from_year": source.year, "levels_copied": copied}


@router.delete("/cycles/{cycle_id}")
def delete_cycle(cycle_id: int, force: bool = False, db: Session = Depends(get_db)):
    """Delete a year: its required levels, and any answers and ratings recorded for it.
    Job scopes, competencies and questions are never touched. The last remaining year cannot be deleted."""
    cycle = get_cycle(db, cycle_id)
    if (db.scalar(select(func.count()).select_from(AssessmentCycle)) or 0) <= 1:
        raise HTTPException(409, "This is the only year left, so it cannot be deleted")
    count = lambda m: db.scalar(select(func.count()).select_from(m).where(m.cycle_id == cycle.id)) or 0
    answers, ratings, levels = count(SurveyAnswer), count(SupervisorRating), count(JobScopeCompetency)
    if (answers or ratings) and not force:
        raise HTTPException(409, f"{answers} survey answer(s) and {ratings} supervisor rating(s) "
                                 f"exist for {cycle.year}. Confirm to delete them too.")
    for m in (SurveyAnswer, SupervisorRating, JobScopeCompetency):
        db.execute(delete(m).where(m.cycle_id == cycle.id))
    db.delete(cycle)
    db.commit()
    return {"deleted": True, "year": cycle.year, "levels": levels, "answers": answers, "ratings": ratings}


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
