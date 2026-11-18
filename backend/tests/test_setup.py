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


def test_only_hr_can_use_setup(client):
    for who in ("bella", "aiman"):
        assert client.get("/setup/overview", headers=auth(client, f"{who}@demo.com")).status_code == 403
    assert client.get("/setup/overview").status_code == 401


def test_overview_has_seed_data(client):
    ov = client.get("/setup/overview", headers=auth(client, "hr@demo.com")).json()
    assert {s["name"] for s in ov["job_scopes"]} == {"System Developer", "Lecturer", "Admin Officer"}
    dev = next(s for s in ov["job_scopes"] if s["name"] == "System Developer")
    assert len(dev["questions"]) == 5
    levels = {c["name"]: c["required_level"] for c in dev["competencies"]}
    assert levels == {"Programming": 4, "Database": 3, "Security": 4}


def test_hr_can_add_scope_competency_level_and_question(client):
    hr = auth(client, "hr@demo.com")
    scope = client.post("/setup/job-scopes", headers=hr, json={"name": "Trainer"}).json()
    comp = client.post("/setup/competencies", headers=hr, json={"name": "Communication"}).json()
    # a question cannot exist before the competency has a required level in that scope
    q = {"job_scope_id": scope["id"], "competency_id": comp["id"],
         "text": "I explain ideas clearly.", "is_negative": False}
    assert client.post("/setup/questions", headers=hr, json=q).status_code == 400
    url = f"/setup/job-scopes/{scope['id']}/competencies/{comp['id']}"
    assert client.put(url, headers=hr, json={"required_level": 6}).status_code == 422
    assert client.put(url, headers=hr, json={"required_level": 3}).status_code == 200
    assert client.put(url, headers=hr, json={"required_level": 4}).json()["required_level"] == 4
    assert client.post("/setup/questions", headers=hr, json=q).status_code == 201
    assert client.post("/setup/job-scopes", headers=hr, json={"name": "Trainer"}).status_code == 409


def test_question_with_answers_is_protected(client):
    hr, bella = auth(client, "hr@demo.com"), auth(client, "bella@demo.com")
    client.put("/survey/me", headers=bella, json={"answers": [{"question_id": 1, "answer": 3}]})
    assert client.delete("/setup/questions/1", headers=hr).status_code == 409
    assert client.put("/setup/questions/1", headers=hr, json={"is_negative": True}).status_code == 409
    # fixing a typo in the text is still fine
    assert client.put("/setup/questions/1", headers=hr, json={"text": "I can build a feature alone."}).status_code == 200


def test_remove_competency_blocked_while_questions_exist(client):
    hr = auth(client, "hr@demo.com")
    assert client.delete("/setup/job-scopes/1/competencies/1", headers=hr).status_code == 409


def test_new_question_appears_in_survey_and_new_cycle(client):
    hr, chris = auth(client, "hr@demo.com"), auth(client, "chris@demo.com")
    r = client.post("/setup/questions", headers=hr, json={
        "job_scope_id": 1, "competency_id": 3,
        "text": "I rarely check for common security flaws.", "is_negative": True})
    assert r.status_code == 201
    assert client.get("/survey/me", headers=chris).json()["total"] == 6
    assert client.post("/setup/cycles", headers=hr, json={"year": 2026}).status_code == 409
    assert client.post("/setup/cycles", headers=hr, json={"year": 2027}).status_code == 201


def test_force_delete_removes_question_and_its_answers(client):
    hr, chris, bella = (auth(client, f"{n}@demo.com") for n in ("hr", "chris", "bella"))
    qid = client.post("/setup/questions", headers=hr, json={
        "job_scope_id": 1, "competency_id": 1, "text": "A throw-away question."}).json()["id"]
    for who in (chris, bella):
        client.put("/survey/me", headers=who, json={"answers": [{"question_id": qid, "answer": 3}]})
    r = client.delete(f"/setup/questions/{qid}", headers=hr)
    assert r.status_code == 409 and "2 answer(s)" in r.json()["detail"]
    assert client.delete(f"/setup/questions/{qid}?force=true", headers=hr).status_code == 200
    ids = [q["id"] for q in client.get("/survey/me", headers=chris).json()["questions"]]
    assert qid not in ids
    assert client.delete(f"/setup/questions/{qid}", headers=hr).status_code == 404
