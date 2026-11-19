"""Deleting job scopes and competencies: allowed when unused, refused with a clear message otherwise."""
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


def overview(client, hr):
    return client.get("/setup/overview?cycle_id=1", headers=hr).json()


def test_overview_reports_what_depends_on_each_item(client):
    hr = auth(client, "hr@demo.com")
    ov = overview(client, hr)
    dev = next(s for s in ov["job_scopes"] if s["name"] == "System Developer")
    assert dev["staff_count"] == 4   # Aiman, Bella, Chris, Nadia
    prog = next(c for c in ov["competencies"] if c["name"] == "Programming")
    assert prog["used_by"] == ["System Developer"]


def test_unused_job_scope_is_deleted_with_its_questions_and_levels_in_every_year(client):
    hr = auth(client, "hr@demo.com")
    scope = client.post("/setup/job-scopes", headers=hr, json={"name": "Temp scope"}).json()
    comp = client.post("/setup/competencies", headers=hr, json={"name": "Temp skill"}).json()
    y2 = client.post("/setup/cycles", headers=hr, json={"year": 2010}).json()
    for cid in (1, y2["id"]):
        client.put(f"/setup/job-scopes/{scope['id']}/competencies/{comp['id']}?cycle_id={cid}",
                   headers=hr, json={"required_level": 3})
    client.post("/setup/questions", headers=hr, json={"job_scope_id": scope["id"], "competency_id": comp["id"],
                                                      "text": "I can use the temp skill."})
    r = client.delete(f"/setup/job-scopes/{scope['id']}", headers=hr)
    assert r.status_code == 200 and (r.json()["questions"], r.json()["levels"]) == (1, 2)
    assert scope["id"] not in [s["id"] for s in overview(client, hr)["job_scopes"]]
    assert client.delete(f"/setup/job-scopes/{scope['id']}", headers=hr).status_code == 404
    # the competency itself survives, and is now unused so it can be deleted
    assert client.delete(f"/setup/competencies/{comp['id']}", headers=hr).status_code == 200
    assert comp["id"] not in [c["id"] for c in overview(client, hr)["competencies"]]


def test_job_scope_with_staff_cannot_be_deleted(client):
    hr = auth(client, "hr@demo.com")
    r = client.delete("/setup/job-scopes/1", headers=hr)
    assert r.status_code == 409 and "staff member(s) are assigned" in r.json()["detail"]
    assert any(s["id"] == 1 for s in overview(client, hr)["job_scopes"])


def test_competency_in_use_cannot_be_deleted(client):
    hr = auth(client, "hr@demo.com")
    r = client.delete("/setup/competencies/1", headers=hr)
    assert r.status_code == 409 and "System Developer" in r.json()["detail"]
    assert client.delete("/setup/competencies/9999", headers=hr).status_code == 404


def test_competency_with_ratings_cannot_be_deleted(client):
    from app.core.database import SessionLocal
    from app.models import SupervisorRating
    hr = auth(client, "hr@demo.com")
    comp = client.post("/setup/competencies", headers=hr, json={"name": "Rated skill"}).json()
    with SessionLocal() as db:
        db.add(SupervisorRating(supervisor_id=2, staff_id=3, cycle_id=1, competency_id=comp["id"], rating=3))
        db.commit()
    r = client.delete(f"/setup/competencies/{comp['id']}", headers=hr)
    assert r.status_code == 409 and "supervisor rating" in r.json()["detail"]
    with SessionLocal() as db:      # clean up so other tests see only the seed data
        db.query(SupervisorRating).filter_by(competency_id=comp["id"]).delete()
        db.commit()
    assert client.delete(f"/setup/competencies/{comp['id']}", headers=hr).status_code == 200


def test_only_hr_can_delete(client):
    for who in ("aiman", "bella"):
        h = auth(client, f"{who}@demo.com")
        assert client.delete("/setup/job-scopes/1", headers=h).status_code == 403
        assert client.delete("/setup/competencies/1", headers=h).status_code == 403
