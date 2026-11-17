from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Competency, Question, SurveyAnswer, User
from app.schemas.survey import SurveySubmit
from app.services.cycles import assert_open, get_cycle

router = APIRouter(prefix="/survey", tags=["survey"])


def _my_questions(db: Session, user: User) -> list[Question]:
    if user.job_scope_id is None:
        raise HTTPException(400, "You have no job scope, so there is no survey for you")
    return list(db.scalars(select(Question)
                           .where(Question.job_scope_id == user.job_scope_id)
                           .order_by(Question.id)))


@router.get("/me")
def my_survey(cycle_id: int | None = None, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    cycle = get_cycle(db, cycle_id)
    questions = _my_questions(db, user)
    answers = {a.question_id: a.answer for a in db.scalars(
        select(SurveyAnswer).where(SurveyAnswer.user_id == user.id,
                                   SurveyAnswer.cycle_id == cycle.id))}
    comp_names = {c.id: c.name for c in db.scalars(select(Competency))}
    return {
        "cycle": {"id": cycle.id, "year": cycle.year, "is_open": cycle.is_open},
        "answered": len(answers), "total": len(questions),
        "questions": [{"id": q.id, "competency": comp_names[q.competency_id],
                       "text": q.text, "answer": answers.get(q.id)} for q in questions],
    }


@router.put("/me")
def save_my_answers(body: SurveySubmit, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    """Create or overwrite answers. Allowed only while the cycle is open."""
    cycle = get_cycle(db, body.cycle_id)
    assert_open(cycle)
    valid_ids = {q.id for q in _my_questions(db, user)}
    for a in body.answers:
        if a.question_id not in valid_ids:
            raise HTTPException(400, f"Question {a.question_id} is not in your job scope")
    existing = {a.question_id: a for a in db.scalars(
        select(SurveyAnswer).where(SurveyAnswer.user_id == user.id,
                                   SurveyAnswer.cycle_id == cycle.id))}
    for a in body.answers:
        row = existing.get(a.question_id)
        if row:
            row.answer = a.answer
        else:
            db.add(SurveyAnswer(user_id=user.id, cycle_id=cycle.id,
                                question_id=a.question_id, answer=a.answer))
    db.commit()
    return {"saved": len(body.answers)}