"""Run from the backend folder:

    python -m app.seed            # job scopes, competencies, the 15 questions, demo users
    python -m app.seed --demo     # the same, plus sample survey answers and supervisor
                                  # competency ratings for the 2026 cycle (so reports have data)

Safe to run twice: each part is skipped if its data already exists."""
import sys

from sqlalchemy import select

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import (AssessmentCycle, Competency, Department, JobScope,
                        JobScopeCompetency, Question, SupervisorRating,
                        SurveyAnswer, User)

PASSWORD = "password123"

# job scope -> [(competency, required level, question, negatively worded)]
SEED = {
    "System Developer": [
        ("Programming", 4, "I can build a feature from requirement to deployment on my own.", False),
        ("Programming", 4, "I often need help to debug my code.", True),
        ("Database", 3, "I can design normalised tables for a new module.", False),
        ("Database", 3, "I can write efficient queries that join 3 or more tables.", False),
        ("Security", 4, "I apply input validation and access checks by default.", False),
    ],
    "Lecturer": [
        ("Teaching Delivery", 4, "I adapt my teaching to different learner levels.", False),
        ("Teaching Delivery", 4, "I find it hard to keep trainees engaged in practical sessions.", True),
        ("Assessment", 4, "I design assessments aligned to the National Occupational Skills Standard (NOSS).", False),
        ("Assessment", 4, "I give written feedback that helps trainees improve.", False),
        ("Digital Tools", 3, "I struggle to use the LMS to run assessments.", True),
    ],
    "Admin Officer": [
        ("Records Management", 3, "I file and retrieve records accurately following the SOP.", False),
        ("Records Management", 3, "I handle personal data according to PDPA requirements.", False),
        ("Customer Service", 4, "I respond to enquiries within the client charter timeline.", False),
        ("Customer Service", 4, "I often need to pass routine complaints to my supervisor.", True),
        ("Office Productivity", 3, "I can summarise data in a spreadsheet using formulas or pivot tables.", False),
    ],
}

DEPARTMENTS = ["ICT Unit", "Academic", "Administration"]

# (name, email, role, department, job scope, supervisor email)
USERS = [
    ("HR Manager", "hr@demo.com", "hr", None, None, None),
    ("Aiman (ICT Supervisor)", "aiman@demo.com", "supervisor", "ICT Unit", "System Developer", None),
    ("Bella", "bella@demo.com", "staff", "ICT Unit", "System Developer", "aiman@demo.com"),
    ("Chris", "chris@demo.com", "staff", "ICT Unit", "System Developer", "aiman@demo.com"),
    ("Nadia", "nadia@demo.com", "staff", "ICT Unit", "System Developer", "aiman@demo.com"),
    ("Dayang (Academic Supervisor)", "dayang@demo.com", "supervisor", "Academic", "Lecturer", None),
    ("Edwin", "edwin@demo.com", "staff", "Academic", "Lecturer", "dayang@demo.com"),
    ("Astrid", "astrid@demo.com", "staff", "Academic", "Lecturer", "dayang@demo.com"),
    ("Farah (Admin Supervisor)", "farah@demo.com", "supervisor", "Administration", "Admin Officer", None),
    ("Gina", "gina@demo.com", "staff", "Administration", "Admin Officer", "farah@demo.com"),
]


# Optional demo assessment data, keyed by staff email.
#   answers: one 1-5 answer per survey question of their job scope, in question order
#            (negatively worded questions are reversed when scored)
#   ratings: the supervisor's direct 1-5 rating per competency
DEMO = {
    "bella@demo.com": {"answers": [4, 2, 3, 4, 3],
                       "ratings": {"Programming": 4, "Database": 3, "Security": 3}},
    "chris@demo.com": {"answers": [3, 4, 2, 2, 1],
                       "ratings": {"Programming": 3, "Database": 2, "Security": 2}},
    "edwin@demo.com": {"answers": [4, 2, 3, 3, 4],
                       "ratings": {"Teaching Delivery": 4, "Assessment": 3, "Digital Tools": 2}},
    "gina@demo.com": {"answers": [3, 2, 3, 4, 2],
                      "ratings": {"Records Management": 3, "Customer Service": 1,
                                  "Office Productivity": 2}},
}


def seed_base(db) -> bool:
    """Create the reference data and demo users. Returns False if it already exists."""
    if db.scalar(select(Department)):
        return False
    comps, scopes, depts = {}, {}, {}
    cycle = AssessmentCycle(year=2026, is_open=True)
    db.add(cycle)
    db.flush()
    for scope_name, rows in SEED.items():
        scope = JobScope(name=scope_name)
        db.add(scope)
        db.flush()
        scopes[scope_name] = scope
        done = set()
        for comp_name, level, text, neg in rows:
            if comp_name not in comps:
                comps[comp_name] = Competency(name=comp_name)
                db.add(comps[comp_name])
                db.flush()
            comp = comps[comp_name]
            if comp_name not in done:  # required level stored once per scope+competency
                db.add(JobScopeCompetency(job_scope_id=scope.id,
                                          competency_id=comp.id,
                                          cycle_id=cycle.id,
                                          required_level=level))
                done.add(comp_name)
            db.add(Question(job_scope_id=scope.id, competency_id=comp.id,
                            text=text, is_negative=neg))
    for dept_name in DEPARTMENTS:
        depts[dept_name] = Department(name=dept_name)
        db.add(depts[dept_name])
    db.flush()
    seed_users(db)
    return True


def seed_users(db) -> list[str]:
    """Create every user in USERS whose email is not in the database yet, so users added to
    the list later still get created on an already-seeded database. Returns the new emails."""
    depts = {d.name: d for d in db.scalars(select(Department))}
    scopes = {s.name: s for s in db.scalars(select(JobScope))}
    by_email = {u.email: u for u in db.scalars(select(User))}
    added = []
    for name, email, role, dept, scope, sup_email in USERS:
        if email in by_email:
            continue
        u = User(name=name, email=email, role=role,
                 password_hash=hash_password(PASSWORD),
                 department_id=depts[dept].id if dept else None,
                 job_scope_id=scopes[scope].id if scope else None,
                 supervisor_id=by_email[sup_email].id if sup_email else None)
        db.add(u)
        db.flush()
        by_email[email] = u
        added.append(email)
    db.commit()
    return added


def seed_demo(db) -> bool:
    """Add sample staff answers and supervisor competency ratings to the latest cycle.
    Returns False (and adds nothing) if any answers or ratings already exist."""
    if db.scalar(select(SurveyAnswer)) or db.scalar(select(SupervisorRating)):
        return False
    cycle = db.scalar(select(AssessmentCycle).order_by(AssessmentCycle.year.desc()))
    users = {u.email: u for u in db.scalars(select(User))}
    comp_ids = {c.name: c.id for c in db.scalars(select(Competency))}
    if cycle is None or not all(e in users for e in DEMO):
        return False
    for email, data in DEMO.items():
        staff = users[email]
        questions = list(db.scalars(select(Question).where(Question.job_scope_id == staff.job_scope_id)
                                    .order_by(Question.id)))
        for q, answer in zip(questions, data["answers"]):
            db.add(SurveyAnswer(user_id=staff.id, cycle_id=cycle.id, question_id=q.id, answer=answer))
        for comp_name, rating in data["ratings"].items():
            db.add(SupervisorRating(supervisor_id=staff.supervisor_id, staff_id=staff.id,
                                    cycle_id=cycle.id, competency_id=comp_ids[comp_name],
                                    rating=rating))
    db.commit()
    return True


def run(demo: bool = False):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if seed_base(db):
            print(f"Seeded. All demo users use password: {PASSWORD}")
        else:
            added = seed_users(db)
            if added:
                print(f"Already seeded. Added new users: {', '.join(added)} (password: {PASSWORD})")
            else:
                print("Already seeded, skipping.")
        if demo:
            if seed_demo(db):
                print("Demo data added: sample survey answers and supervisor ratings for the latest cycle.")
            else:
                print("Demo data skipped: answers or ratings already exist.")
    finally:
        db.close()


if __name__ == "__main__":
    run(demo="--demo" in sys.argv)
