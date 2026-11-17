"""End-to-end check: survey -> rating -> report, with the access rules."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from app.main import app
    from app.seed import run
    run()
    return TestClient(app)


def auth(client, email):
    r = client.post("/auth/login", data={"username": email, "password": "password123"})
    return {"Authorization": "Bearer " + r.json()["access_token"]}


@pytest.fixture(scope="module")
def filled(client):
    bella, chris, aiman = (auth(client, f"{n}@demo.com") for n in ("bella", "chris", "aiman"))
    # Bella: Programming q1=4, q2=2(neg->4) | Database q3=2,q4=2 | Security q5=1
    client.put("/survey/me", headers=bella, json={"answers": [
        {"question_id": 1, "answer": 4}, {"question_id": 2, "answer": 2},
        {"question_id": 3, "answer": 2}, {"question_id": 4, "answer": 2},
        {"question_id": 5, "answer": 1}]})
    # Chris: everything 5 (q2 is negative, so it counts as 1), no supervisor rating yet
    client.put("/survey/me", headers=chris, json={"answers": [
        {"question_id": i, "answer": 5} for i in range(1, 6)]})
    # Aiman answers the same 5 questions about Bella. q2 is negative: 2 counts as 4.
    # -> Programming (4 + 4)/2 = 4 | Database (2 + 2)/2 = 2 | Security 2
    r = client.put("/rating/3", headers=aiman, json={"ratings": [
        {"question_id": 1, "rating": 4}, {"question_id": 2, "rating": 2},
        {"question_id": 3, "rating": 2}, {"question_id": 4, "rating": 2},
        {"question_id": 5, "rating": 2}]})
    assert r.status_code == 200
    return {"bella": bella, "chris": chris, "aiman": aiman, "hr": auth(client, "hr@demo.com")}


def test_individual_report_numbers(client, filled):
    rep = client.get("/reports/me", headers=filled["bella"]).json()
    rows = {r["competency"]: r for r in rep["rows"]}
    # Security: 0.7*2 + 0.3*1 = 1.7 -> gap 2.3 Critical
    assert rows["Security"]["actual"] == 1.7 and rows["Security"]["gap"] == 2.3
    assert rows["Security"]["category"] == "Critical"
    # Database: 0.7*2 + 0.3*2 = 2.0 -> gap exactly 1.0 -> Moderate (boundary)
    assert rows["Database"]["gap"] == 1.0 and rows["Database"]["category"] == "Moderate"
    # Programming: self 4 (negative reversed), supervisor 4 -> 4.0 -> gap 0 -> Minor
    assert rows["Programming"]["gap"] == 0 and rows["Programming"]["category"] == "Minor"
    assert [r["competency"] for r in rep["rows"]] == ["Security", "Database", "Programming"]
    assert rep["summary"] == "1 Critical · 1 Moderate · 1 Minor. Suggested focus: Security."
    h = rep["header"]
    assert (h["staff_name"], h["job_scope"], h["department"]) == ("Bella", "System Developer", "ICT Unit")
    assert h["supervisor_rating_status"] == "Complete"


def test_missing_supervisor_rating_uses_self_only(client, filled):
    rep = client.get("/reports/me", headers=filled["chris"]).json()
    assert rep["header"]["supervisor_rating_status"] == "Not started"
    prog = next(r for r in rep["rows"] if r["competency"] == "Programming")
    assert prog["supervisor_pending"] is True
    assert prog["self"] == 3.0  # q1=5, q2=5 reversed to 1 -> (5+1)/2


def test_department_report(client, filled):
    rep = client.get("/reports/department/1", headers=filled["hr"]).json()
    assert rep["header"]["department"] == "ICT Unit"
    # Bella + Chris answered, Aiman (supervisor in the unit) did not
    assert rep["header"]["staff_assessed"] == 2 and rep["header"]["staff_total"] == 3
    assert rep["header"]["supervisor_ratings_incomplete"] == 1
    sec = next(c for c in rep["competencies"] if c["competency"] == "Security")
    # Bella gap 2.3 (Critical); Chris self-only 5 -> gap 0 (Minor)
    assert sec["critical"] == 1 and sec["minor"] == 1 and sec["avg_gap"] == 1.15
    assert rep["top_priorities"][0]["competency"] == "Security"


def test_access_rules(client, filled):
    h = filled
    assert client.get("/reports/individual/4", headers=h["bella"]).status_code == 403   # staff -> peer
    assert client.get("/reports/individual/3", headers=h["aiman"]).status_code == 200   # own report
    assert client.get("/reports/individual/6", headers=h["aiman"]).status_code == 403   # other dept
    assert client.get("/reports/individual/6", headers=h["hr"]).status_code == 200      # hr sees all
    assert client.get("/reports/department/1", headers=h["bella"]).status_code == 403   # staff
    assert client.get("/reports/department/2", headers=h["aiman"]).status_code == 403   # other dept
    assert client.get("/reports/department/1", headers=h["aiman"]).status_code == 200
    assert client.get("/reports/individual/3").status_code == 401                       # no token


def test_people_lists_respect_role(client, filled):
    names = lambda who: sorted(p["name"] for p in client.get("/reports/people", headers=filled[who]).json())
    assert names("bella") == ["Bella"]
    assert names("aiman") == ["Aiman (ICT Supervisor)", "Bella", "Chris"]
    assert len(names("hr")) == 7


def test_any_user_can_list_cycles(client, filled):
    r = client.get("/reports/cycles", headers=filled["bella"])
    assert r.status_code == 200 and r.json()[0]["year"] >= 2026
    assert client.get("/reports/cycles").status_code == 401


def test_supervisor_answers_the_survey_questions(client, filled):
    aiman = filled["aiman"]
    view = client.get("/rating/3", headers=aiman).json()
    assert [q["question_id"] for q in view["questions"]] == [1, 2, 3, 4, 5]
    assert view["questions"][0]["text"].startswith("I can build a feature")
    assert [q["rating"] for q in view["questions"]] == [4, 2, 2, 2, 2]
    # a question from another job scope is refused
    bad = client.put("/rating/3", headers=aiman, json={"ratings": [{"question_id": 6, "rating": 3}]})
    assert bad.status_code == 400
    assert client.put("/rating/3", headers=aiman, json={"ratings": [{"question_id": 1, "rating": 6}]}).status_code == 422


def test_partial_supervisor_rating_reverses_negative_questions(client, filled):
    """Aiman rates only Chris's two Programming questions: q1 = 5, q2 (negative) = 1 -> 5 and 5."""
    aiman, chris = filled["aiman"], filled["chris"]
    client.put("/rating/4", headers=aiman, json={"ratings": [
        {"question_id": 1, "rating": 5}, {"question_id": 2, "rating": 1}]})
    team = {m["name"]: m for m in client.get("/rating/team", headers=aiman).json()["team"]}
    assert team["Chris"]["status"] == "Partial" and team["Chris"]["rated"] == 2
    rep = client.get("/reports/me", headers=chris).json()
    rows = {r["competency"]: r for r in rep["rows"]}
    assert rows["Programming"]["supervisor"] == 5.0 and rows["Programming"]["supervisor_pending"] is False
    assert rows["Database"]["supervisor"] is None and rows["Database"]["supervisor_pending"] is True
