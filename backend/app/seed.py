"""Run from the backend folder:  python -m app.seed
Safe to run twice: it skips if data already exists."""
from sqlalchemy import select

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import (AssessmentCycle, Competency, Department, JobScope,
                        JobScopeCompetency, Question, User)

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
    ("Dayang (Academic Supervisor)", "dayang@demo.com", "supervisor", "Academic", "Lecturer", None),
    ("Edwin", "edwin@demo.com", "staff", "Academic", "Lecturer", "dayang@demo.com"),
    ("Farah (Admin Supervisor)", "farah@demo.com", "supervisor", "Administration", "Admin Officer", None),
    ("Gina", "gina@demo.com", "staff", "Administration", "Admin Officer", "farah@demo.com"),
]


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.scalar(select(Department)):
            print("Already seeded, skipping.")
            return
        comps, scopes, depts = {}, {}, {}
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
                                              required_level=level))
                    done.add(comp_name)
                db.add(Question(job_scope_id=scope.id, competency_id=comp.id,
                                text=text, is_negative=neg))
        for dept_name in DEPARTMENTS:
            depts[dept_name] = Department(name=dept_name)
            db.add(depts[dept_name])
        db.add(AssessmentCycle(year=2026, is_open=True))
        db.flush()

        by_email = {}
        for name, email, role, dept, scope, sup_email in USERS:
            u = User(name=name, email=email, role=role,
                     password_hash=hash_password(PASSWORD),
                     department_id=depts[dept].id if dept else None,
                     job_scope_id=scopes[scope].id if scope else None,
                     supervisor_id=by_email[sup_email].id if sup_email else None)
            db.add(u)
            db.flush()
            by_email[email] = u
        db.commit()
        print(f"Seeded. All demo users use password: {PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    run()