"""Required levels are per year: edit, clone, and delete a year without touching other years."""
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


def levels(client, hr, cycle_id):
    ov = client.get(f"/setup/overview?cycle_id={cycle_id}", headers=hr).json()
    return {(s["id"], c["competency_id"]): c["required_level"]
            for s in ov["job_scopes"] for c in s["competencies"]}


def new_year(client, hr, year, copy_from=None):
    body = {"year": year, **({"copy_from_cycle_id": copy_from} if copy_from else {})}
    r = client.post("/setup/cycles", headers=hr, json=body)
    assert r.status_code == 201
    return r.json()


def test_new_year_clones_levels_and_edits_stay_in_that_year(client):
    hr, aiman = auth(client, "hr@demo.com"), auth(client, "aiman@demo.com")
    base = levels(client, hr, 1)
    y = new_year(client, hr, 2030, copy_from=1)
    assert y["levels_copied"] == len(base) > 0
    assert levels(client, hr, y["id"]) == base

    url = f"/setup/job-scopes/1/competencies/1?cycle_id={y['id']}"
    assert client.put(url, headers=hr, json={"required_level": 2}).json()["year"] == 2030
    assert levels(client, hr, y["id"])[(1, 1)] == 2
    assert levels(client, hr, 1)[(1, 1)] == base[(1, 1)]          # 2026 unchanged
    # the supervisor sees the level of the year being rated
    req = lambda cid: client.get(f"/rating/3?cycle_id={cid}", headers=aiman).json()["competencies"][0]["required"]
    assert (req(1), req(y["id"])) == (base[(1, 1)], 2)


def test_new_year_without_copy_is_empty_until_levels_are_copied(client):
    hr = auth(client, "hr@demo.com")
    y = new_year(client, hr, 2031)
    assert y["levels_copied"] == 0 and levels(client, hr, y["id"]) == {}
    assert client.get(f"/rating/3?cycle_id={y['id']}", headers=auth(client, "aiman@demo.com")).json()["competencies"] == []
    url = f"/setup/cycles/{y['id']}/copy-levels"
    assert client.post(url, headers=hr, json={"from_cycle_id": y["id"]}).status_code == 400
    assert client.post(url, headers=hr, json={"from_cycle_id": 1}).json()["levels_copied"] == len(levels(client, hr, 1))
    assert client.post(url, headers=hr, json={"from_cycle_id": 1}).json()["levels_copied"] == 0   # nothing overwritten
    assert client.post("/setup/cycles", headers=hr, json={"year": 2032, "copy_from_cycle_id": 999}).status_code == 404


def test_remove_competency_from_one_year_only(client):
    hr = auth(client, "hr@demo.com")
    y = new_year(client, hr, 2033, copy_from=1)
    # questions exist for scope 1 / competency 1, so removal is still refused...
    assert client.delete(f"/setup/job-scopes/1/competencies/1?cycle_id={y['id']}", headers=hr).status_code == 409
    # ...but a competency with no questions can be dropped from that year alone
    client.put(f"/setup/job-scopes/1/competencies/4?cycle_id={y['id']}", headers=hr, json={"required_level": 3})
    assert client.delete(f"/setup/job-scopes/1/competencies/4?cycle_id={y['id']}", headers=hr).status_code == 200
    assert (1, 4) not in levels(client, hr, y["id"])


def test_delete_year_needs_force_when_answers_exist_and_keeps_master_data(client):
    hr, chris = auth(client, "hr@demo.com"), auth(client, "chris@demo.com")
    y = new_year(client, hr, 2034, copy_from=1)
    qs = client.get(f"/survey/me?cycle_id={y['id']}", headers=chris).json()["questions"]
    client.put("/survey/me", headers=chris, json={"cycle_id": y["id"],
               "answers": [{"question_id": qs[0]["id"], "answer": 3}]})
    listed = next(c for c in client.get("/setup/cycles", headers=hr).json() if c["id"] == y["id"])
    assert (listed["answers"], listed["levels"] > 0) == (1, True)

    before = client.get("/setup/overview?cycle_id=1", headers=hr).json()
    r = client.delete(f"/setup/cycles/{y['id']}", headers=hr)
    assert r.status_code == 409 and "1 survey answer" in r.json()["detail"]
    r = client.delete(f"/setup/cycles/{y['id']}?force=true", headers=hr)
    assert r.status_code == 200 and (r.json()["year"], r.json()["answers"]) == (2034, 1)
    assert 2034 not in [c["year"] for c in client.get("/setup/cycles", headers=hr).json()]
    assert client.delete(f"/setup/cycles/{y['id']}", headers=hr).status_code == 404
    # other years, job scopes, competencies and questions are untouched
    after = client.get("/setup/overview?cycle_id=1", headers=hr).json()
    strip = lambda ov: [{**s, "questions": [{k: v for k, v in q.items() if k != "answer_count"}
                                            for q in s["questions"]]} for s in ov["job_scopes"]]
    assert strip(after) == strip(before) and after["competencies"] == before["competencies"]


def test_delete_year_without_data_needs_no_force_and_only_hr(client):
    hr = auth(client, "hr@demo.com")
    y = new_year(client, hr, 2035)
    assert client.delete(f"/setup/cycles/{y['id']}", headers=auth(client, "aiman@demo.com")).status_code == 403
    assert client.delete(f"/setup/cycles/{y['id']}", headers=hr).status_code == 200


def test_the_only_remaining_year_cannot_be_deleted():
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.core.database import Base, get_db
    from app.main import app
    from app.seed import seed_base

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        seed_base(db)

    def override():
        with Session() as db:
            yield db

    app.dependency_overrides[get_db] = override
    try:
        c = TestClient(app)
        hr = auth(c, "hr@demo.com")
        r = c.delete("/setup/cycles/1", headers=hr)
        assert r.status_code == 409 and "only year" in r.json()["detail"]
    finally:
        app.dependency_overrides.clear()
