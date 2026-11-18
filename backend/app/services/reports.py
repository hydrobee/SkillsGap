"""Builds the individual and department reports.
The summary and roll-up helpers are pure (no database) so they are easy to test."""
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (AssessmentCycle, Competency, Department, JobScope,
                        JobScopeCompetency, Question, SupervisorRating,
                        SurveyAnswer, User)
from app.services.gap import competency_result

CATEGORIES = ("Critical", "Moderate", "Minor")


def supervisor_status(rated: int, total: int) -> str:
    return "Not started" if rated == 0 else "Complete" if rated >= total else "Partial"


# ---------- pure helpers ----------

def sort_rows(rows: list[dict]) -> list[dict]:
    """Largest gap first; ties by competency name so the order is stable."""
    return sorted(rows, key=lambda r: (-r["gap"], r["competency"]))


def summary_line(rows: list[dict]) -> str:
    if not rows:
        return "No survey answers yet."
    counts = {c: sum(1 for r in rows if r["category"] == c) for c in CATEGORIES}
    focus = rows[0]["competency"] if rows[0]["gap"] > 0 else "none"
    return (f'{counts["Critical"]} Critical · {counts["Moderate"]} Moderate · '
            f'{counts["Minor"]} Minor. Suggested focus: {focus}.')


def department_rollup(per_staff_rows: list[list[dict]]) -> list[dict]:
    """per_staff_rows = one list of competency rows per ASSESSED staff member."""
    by_comp: dict[str, list[dict]] = defaultdict(list)
    for rows in per_staff_rows:
        for r in rows:
            by_comp[r["competency"]].append(r)
    out = []
    for name, rs in by_comp.items():
        n = len(rs)
        out.append({
            "competency": name,
            "required": round(sum(r["required"] for r in rs) / n, 2),
            "avg_actual": round(sum(r["actual"] for r in rs) / n, 2),
            "avg_gap": round(sum(r["gap"] for r in rs) / n, 2),
            "critical": sum(1 for r in rs if r["category"] == "Critical"),
            "moderate": sum(1 for r in rs if r["category"] == "Moderate"),
            "minor": sum(1 for r in rs if r["category"] == "Minor"),
            "staff_count": n,
            # who sits in each category, largest gap first (rows carry staff_id/staff_name
            # when they come from department_report; pure-test rows may not)
            "staff": sorted(
                ({"id": r.get("staff_id"), "name": r.get("staff_name"), "actual": r["actual"],
                  "gap": r["gap"], "category": r["category"]} for r in rs),
                key=lambda s: (-s["gap"], s["name"] or "")),
        })
    return sorted(out, key=lambda c: (-c["avg_gap"], -c["critical"], c["competency"]))


def top_priorities(rollup: list[dict], n: int = 3) -> list[dict]:
    return [{"rank": i, **c} for i, c in enumerate([c for c in rollup if c["avg_gap"] > 0][:n], 1)]


# ---------- database loading ----------

def user_rows(db: Session, user: User, cycle: AssessmentCycle) -> dict:
    """Competency rows for one person. Competencies with no survey answers are skipped."""
    questions = list(db.scalars(select(Question).where(Question.job_scope_id == user.job_scope_id)))
    answers = {a.question_id: a.answer for a in db.scalars(
        select(SurveyAnswer).where(SurveyAnswer.user_id == user.id,
                                   SurveyAnswer.cycle_id == cycle.id))}
    ratings = {r.competency_id: r.rating for r in db.scalars(
        select(SupervisorRating).where(SupervisorRating.staff_id == user.id,
                                       SupervisorRating.cycle_id == cycle.id))}
    scope_comps = db.execute(
        select(Competency, JobScopeCompetency.required_level)
        .join(JobScopeCompetency, JobScopeCompetency.competency_id == Competency.id)
        .where(JobScopeCompetency.job_scope_id == user.job_scope_id,
               JobScopeCompetency.cycle_id == cycle.id)).all()

    rows = []
    for comp, required in scope_comps:
        comp_qs = [q for q in questions if q.competency_id == comp.id]
        given = [(answers[q.id], q.is_negative) for q in comp_qs if q.id in answers]
        if not given:
            continue
        # supervisor score = the 1-5 rating given for this competency (None until rated)
        rows.append({"competency_id": comp.id, "competency": comp.name,
                     **competency_result(required, given, ratings.get(comp.id))})
    return {
        "rows": sort_rows(rows),
        "answered": len(answers), "questions": len(questions),
        # ratings given vs competencies that need one (ratings for removed competencies don't count)
        "rated": sum(1 for comp, _ in scope_comps if comp.id in ratings),
        "rating_total": len(scope_comps),
    }


def individual_report(db: Session, user: User, cycle: AssessmentCycle) -> dict:
    data = user_rows(db, user, cycle)
    dept = db.get(Department, user.department_id) if user.department_id else None
    scope = db.get(JobScope, user.job_scope_id)
    return {
        "header": {
            "staff_name": user.name,
            "job_scope": scope.name,
            "department": dept.name if dept else None,
            "cycle": {"id": cycle.id, "year": cycle.year, "is_open": cycle.is_open},
            "supervisor_rating_status": supervisor_status(data["rated"], data["rating_total"]),
            "survey_progress": f'{data["answered"]} of {data["questions"]} answered',
        },
        "rows": data["rows"],
        "summary": summary_line(data["rows"]),
    }


def department_report(db: Session, department: Department, cycle: AssessmentCycle) -> dict:
    staff = list(db.scalars(select(User).where(User.department_id == department.id,
                                               User.job_scope_id.is_not(None))
                            .order_by(User.name)))
    per_staff, assessed, provisional = [], 0, 0
    for s in staff:
        d = user_rows(db, s, cycle)
        if d["rows"]:
            assessed += 1
            per_staff.append([{**r, "staff_id": s.id, "staff_name": s.name} for r in d["rows"]])
            if d["rated"] < d["rating_total"]:
                provisional += 1
    rollup = department_rollup(per_staff)
    return {
        "header": {
            "department": department.name,
            "cycle": {"id": cycle.id, "year": cycle.year, "is_open": cycle.is_open},
            "staff_assessed": assessed, "staff_total": len(staff),
            "supervisor_ratings_incomplete": provisional,
        },
        "competencies": rollup,
        "top_priorities": top_priorities(rollup),
    }
