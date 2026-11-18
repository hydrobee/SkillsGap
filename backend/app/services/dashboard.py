"""HR dashboard: one organisation-wide snapshot of an assessment cycle.
Re-uses the same per-person rows as the individual/department reports, so the numbers match."""
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AssessmentCycle, Department, User
from app.services.reports import (CATEGORIES, department_rollup, supervisor_status,
                                  top_priorities, user_rows)


def survey_status(answered: int, questions: int) -> str:
    if answered == 0:
        return "Not started"
    return "Complete" if answered >= questions else "In progress"


def _avg(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def hr_dashboard(db: Session, cycle: AssessmentCycle) -> dict:
    depts = {d.id: d.name for d in db.scalars(select(Department).order_by(Department.name))}
    names = {u.id: u.name for u in db.scalars(select(User))}
    staff = list(db.scalars(select(User).where(User.job_scope_id.is_not(None)).order_by(User.name)))

    people, all_rows = [], []
    by_dept: dict[int | None, list[dict]] = defaultdict(list)       # people per department
    rows_by_dept: dict[int | None, list[list[dict]]] = defaultdict(list)
    for s in staff:
        d = user_rows(db, s, cycle)
        rows = [{**r, "staff_id": s.id, "staff_name": s.name} for r in d["rows"]]
        gaps = [r["gap"] for r in rows]
        p = {
            "id": s.id, "name": s.name, "role": s.role,
            "department": depts.get(s.department_id),
            "supervisor": names.get(s.supervisor_id),
            "survey": survey_status(d["answered"], d["questions"]),
            "answered": d["answered"], "questions": d["questions"],
            # only people with a supervisor need a supervisor rating
            "rating": supervisor_status(d["rated"], d["rating_total"]) if s.supervisor_id else None,
            "rated": d["rated"], "rating_total": d["rating_total"],
            "critical": sum(1 for r in rows if r["category"] == "Critical"),
            "moderate": sum(1 for r in rows if r["category"] == "Moderate"),
            "avg_gap": _avg(gaps),
            "_supervisor_id": s.supervisor_id,
        }
        people.append(p)
        by_dept[s.department_id].append(p)
        if rows:
            all_rows.extend(rows)
            rows_by_dept[s.department_id].append(rows)

    needs_rating = [p for p in people if p["rating"] is not None]
    assessed = [p for p in people if p["avg_gap"] is not None]

    departments = []
    for dept_id, dept_name in depts.items():
        ps = by_dept.get(dept_id, [])
        if not ps:
            continue
        dept_rows = [r for rows in rows_by_dept.get(dept_id, []) for r in rows]
        top = top_priorities(department_rollup(rows_by_dept.get(dept_id, [])), 1)
        rated = [p for p in ps if p["rating"] is not None]
        departments.append({
            "id": dept_id, "name": dept_name, "staff_total": len(ps),
            "assessed": sum(1 for p in ps if p["avg_gap"] is not None),
            "survey_complete": sum(1 for p in ps if p["survey"] == "Complete"),
            "rating_needed": len(rated),
            "rating_complete": sum(1 for p in rated if p["rating"] == "Complete"),
            "avg_gap": _avg([r["gap"] for r in dept_rows]),
            "critical_staff": sum(1 for p in ps if p["critical"] > 0),
            "top_priority": top[0]["competency"] if top else None,
        })

    # supervisors who still owe ratings
    owed: dict[int, dict] = {}
    for p in needs_rating:
        sid = p["_supervisor_id"]
        o = owed.setdefault(sid, {"id": sid, "name": names.get(sid), "pending": 0, "team": 0})
        o["team"] += 1
        if p["rating"] != "Complete":
            o["pending"] += 1
    pending_supervisors = sorted((o for o in owed.values() if o["pending"]),
                                 key=lambda o: (-o["pending"], o["name"] or ""))

    order = {"Not started": 0, "In progress": 1}
    survey_pending = sorted((p for p in people if p["survey"] != "Complete"),
                            key=lambda p: (order[p["survey"]], p["name"]))
    attention = sorted((p for p in people if p["critical"] > 0),
                       key=lambda p: (-p["critical"], -(p["avg_gap"] or 0), p["name"]))[:6]

    for p in people:
        p.pop("_supervisor_id")
    priorities = top_priorities(department_rollup([[r] for r in all_rows]), 5)
    for pr in priorities:
        pr.pop("staff", None)  # counts are enough here; the department report has the names

    return {
        "cycle": {"id": cycle.id, "year": cycle.year, "is_open": cycle.is_open},
        "totals": {
            "staff": len(people),
            "survey_complete": sum(1 for p in people if p["survey"] == "Complete"),
            "survey_in_progress": sum(1 for p in people if p["survey"] == "In progress"),
            "survey_not_started": sum(1 for p in people if p["survey"] == "Not started"),
            "rating_needed": len(needs_rating),
            "rating_complete": sum(1 for p in needs_rating if p["rating"] == "Complete"),
            "assessed": len(assessed),
            "staff_with_critical": sum(1 for p in people if p["critical"] > 0),
            "avg_gap": _avg([r["gap"] for r in all_rows]),
        },
        "categories": {c: sum(1 for r in all_rows if r["category"] == c) for c in CATEGORIES},
        "priorities": priorities,
        "departments": departments,
        "survey_pending": survey_pending,
        "pending_supervisors": pending_supervisors,
        "attention": attention,
    }
