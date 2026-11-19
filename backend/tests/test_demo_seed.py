"""The optional demo seed, checked on its own in-memory database (not the shared test DB)."""
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import AssessmentCycle, SupervisorRating, SurveyAnswer, User
from app.seed import seed_base, seed_demo
from app.services.reports import department_report, individual_report


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    assert seed_base(session) is True
    yield session
    session.close()


def person(db, email):
    return db.scalar(select(User).where(User.email == email))


def report(db, email):
    cycle = db.scalar(select(AssessmentCycle))
    return individual_report(db, person(db, email), cycle)


def test_base_seed_has_no_answers_or_ratings(db):
    assert db.scalar(select(SurveyAnswer)) is None and db.scalar(select(SupervisorRating)) is None
    assert seed_base(db) is False          # second run is skipped


def test_demo_seed_is_added_once(db):
    assert seed_demo(db) is True
    assert seed_demo(db) is False
    answers = db.scalars(select(SurveyAnswer)).all()
    ratings = db.scalars(select(SupervisorRating)).all()
    assert len(answers) == 20 and len(ratings) == 12          # 4 staff x 5 answers, 4 x 3 ratings
    assert all(1 <= r.rating <= 5 for r in ratings)
    # every rating is by the staff member's own supervisor
    users = {u.id: u for u in db.scalars(select(User))}
    assert all(r.supervisor_id == users[r.staff_id].supervisor_id for r in ratings)


def test_chris_numbers(db):
    seed_demo(db)
    rep = report(db, "chris@demo.com")
    rows = {r["competency"]: r for r in rep["rows"]}
    # Programming: self (3 + reversed 4->2)/2 = 2.5, rating 3 -> 0.7*3 + 0.3*2.5 = 2.85 -> gap 1.15
    assert rows["Programming"]["self"] == 2.5 and rows["Programming"]["supervisor"] == 3
    assert (rows["Programming"]["actual"], rows["Programming"]["gap"]) == (2.85, 1.15)
    assert rows["Programming"]["category"] == "Moderate"
    # Database: self 2, rating 2 -> 2.0 -> gap exactly 1.0 (boundary) -> Moderate
    assert (rows["Database"]["gap"], rows["Database"]["category"]) == (1.0, "Moderate")
    # Security: self 1, rating 2 -> 1.7 -> gap 2.3 -> Critical
    assert (rows["Security"]["actual"], rows["Security"]["gap"]) == (1.7, 2.3)
    assert rows["Security"]["category"] == "Critical"
    assert rep["summary"] == "1 Critical · 2 Moderate · 0 Minor. Suggested focus: Security."
    assert rep["header"]["supervisor_rating_status"] == "Complete"


def test_other_demo_people(db):
    seed_demo(db)
    bella = {r["competency"]: r for r in report(db, "bella@demo.com")["rows"]}
    assert bella["Database"]["gap"] == 0 and bella["Database"]["category"] == "Minor"   # exceeds the level
    assert (bella["Security"]["gap"], bella["Security"]["category"]) == (1.0, "Moderate")
    gina = {r["competency"]: r for r in report(db, "gina@demo.com")["rows"]}
    assert (gina["Customer Service"]["gap"], gina["Customer Service"]["category"]) == (2.55, "Critical")
    edwin = report(db, "edwin@demo.com")
    assert edwin["summary"] == "0 Critical · 2 Moderate · 1 Minor. Suggested focus: Assessment."


def test_ict_department_report_with_demo_data(db):
    seed_demo(db)
    dept = person(db, "bella@demo.com").department_id
    from app.models import Department
    rep = department_report(db, db.get(Department, dept), db.scalar(select(AssessmentCycle)))
    assert (rep["header"]["staff_assessed"], rep["header"]["staff_total"]) == (2, 4)   # Nadia has no demo answers
    assert rep["header"]["supervisor_ratings_incomplete"] == 0
    sec = next(c for c in rep["competencies"] if c["competency"] == "Security")
    assert (sec["critical"], sec["moderate"], sec["avg_gap"]) == (1, 1, 1.65)
    assert rep["top_priorities"][0]["competency"] == "Security"
