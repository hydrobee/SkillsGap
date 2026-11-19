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
    # Aiman rates Bella per competency: Programming 4 | Database 2 | Security 2
    r = client.put("/rating/3", headers=aiman, json={"ratings": [
        {"competency_id": 1, "rating": 4}, {"competency_id": 2, "rating": 2},
        {"competency_id": 3, "rating": 2}]})
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
    # Bella + Chris answered; Aiman (supervisor in the unit) and Nadia did not
    assert rep["header"]["staff_assessed"] == 2 and rep["header"]["staff_total"] == 4
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
    assert names("aiman") == ["Aiman (ICT Supervisor)", "Bella", "Chris", "Nadia"]
    assert len(names("hr")) == 9


def test_any_user_can_list_cycles(client, filled):
    r = client.get("/reports/cycles", headers=filled["bella"])
    assert r.status_code == 200 and r.json()[0]["year"] >= 2026
    assert client.get("/reports/cycles").status_code == 401


def test_supervisor_rates_competencies_not_questions(client, filled):
    aiman = filled["aiman"]
    view = client.get("/rating/3", headers=aiman).json()
    assert "questions" not in view
    comps = view["competencies"]
    assert [c["competency_id"] for c in comps] == [1, 2, 3]
    assert [c["competency"] for c in comps] == ["Programming", "Database", "Security"]
    assert [c["required"] for c in comps] == [4, 3, 4]
    assert [c["rating"] for c in comps] == [4, 2, 2]
    # a competency from another job scope (7 = Records Management) is refused
    bad = client.put("/rating/3", headers=aiman, json={"ratings": [{"competency_id": 7, "rating": 3}]})
    assert bad.status_code == 400
    assert client.put("/rating/3", headers=aiman, json={"ratings": [{"competency_id": 1, "rating": 6}]}).status_code == 422
    assert client.put("/rating/3", headers=aiman, json={"ratings": [{"competency_id": 1, "rating": 0}]}).status_code == 422


def test_partial_rating_and_rating_can_be_changed(client, filled):
    """Aiman rates only Chris's Programming (5). The other competencies stay pending."""
    aiman, chris = filled["aiman"], filled["chris"]
    assert client.put("/rating/4", headers=aiman, json={"ratings": [{"competency_id": 1, "rating": 3}]}).status_code == 200
    assert client.put("/rating/4", headers=aiman, json={"ratings": [{"competency_id": 1, "rating": 5}]}).status_code == 200
    team = {m["name"]: m for m in client.get("/rating/team", headers=aiman).json()["team"]}
    assert (team["Chris"]["status"], team["Chris"]["rated"], team["Chris"]["total"]) == ("Partial", 1, 3)
    rows = {r["competency"]: r for r in client.get("/reports/me", headers=chris).json()["rows"]}
    prog = rows["Programming"]   # self 3.0 (q1=5, q2 reversed to 1), supervisor 5 -> 0.7*5 + 0.3*3 = 4.4
    assert prog["supervisor"] == 5 and prog["supervisor_pending"] is False
    assert prog["actual"] == 4.4 and prog["gap"] == 0 and prog["category"] == "Minor"
    assert rows["Database"]["supervisor"] is None and rows["Database"]["supervisor_pending"] is True


def test_hr_dashboard(client, filled):
    assert client.get("/reports/dashboard", headers=filled["aiman"]).status_code == 403
    assert client.get("/reports/dashboard", headers=filled["bella"]).status_code == 403
    d = client.get("/reports/dashboard", headers=filled["hr"]).json()
    t = d["totals"]
    # 9 people have a job scope; only Bella and Chris answered (all 5 questions)
    assert (t["staff"], t["survey_complete"], t["survey_not_started"]) == (9, 2, 7)
    # Bella, Chris, Nadia, Edwin, Astrid, Gina have a supervisor; only Bella is fully rated
    assert (t["rating_needed"], t["rating_complete"]) == (6, 1)
    assert t["assessed"] == 2 and t["staff_with_critical"] == 1   # Bella: Security gap 2.3
    assert sum(d["categories"].values()) == 6                    # 3 competencies x 2 people
    ict = next(x for x in d["departments"] if x["name"] == "ICT Unit")
    assert (ict["staff_total"], ict["survey_complete"], ict["top_priority"]) == (4, 2, "Security")
    assert d["priorities"][0]["competency"] == "Security"
    assert d["attention"][0]["name"] == "Bella"
    aiman = next(s for s in d["pending_supervisors"] if s["name"].startswith("Aiman"))
    assert (aiman["pending"], aiman["team"]) == (2, 3)           # Chris and Nadia not rated yet
    assert {p["name"] for p in d["survey_pending"]} >= {"Nadia", "Edwin", "Astrid", "Gina"}
