import os

import pytest

os.environ["DATABASE_URL"] = "sqlite://"
import main
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

main.engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
main.Base.metadata.create_all(main.engine)
with Session(main.engine) as db:
    db.add(
        main.User(email="employee@example.test", password=main.hash_password("Test-password-123"))
    )
    db.commit()
client = TestClient(main.app)


def test_auth_and_revocation():
    assert client.get("/auth/me").status_code == 401
    assert (
        client.post(
            "/auth/login", json={"email": "employee@example.test", "password": "wrong"}
        ).status_code
        == 401
    )
    result = client.post(
        "/auth/login", json={"email": "employee@example.test", "password": "Test-password-123"}
    )
    assert result.status_code == 200
    assert "HttpOnly" in result.headers["set-cookie"]
    assert client.get("/auth/me").json()["department"] == "DEMO Pension"
    assert client.get("/admin/audit").status_code == 403
    assert client.post("/auth/logout").status_code == 403
    assert (
        client.post("/auth/logout", headers={"x-csrf-token": result.json()["csrf"]}).status_code
        == 200
    )
    assert client.get("/auth/me").status_code == 401


def test_password_salts():
    a, b = main.hash_password("same"), main.hash_password("same")
    assert a != b
    assert main.verify("same", a)
    assert not main.verify("wrong", a)


def test_grounded_draft_and_permissions():
    with Session(main.engine) as db:
        for email, role, dept in [
            ("reviewer@example.test", "reviewer", "DEMO Pension"),
            ("other@example.test", "employee", "Other"),
        ]:
            db.add(
                main.User(
                    email=email,
                    role=role,
                    department=dept,
                    password=main.hash_password("Test-password-123"),
                )
            )
        db.commit()

    def signin(email):
        c = TestClient(main.app)
        token = c.post(
            "/auth/login", json={"email": email, "password": "Test-password-123"}
        ).json()["csrf"]
        c.headers["x-csrf-token"] = token
        return c

    employee = signin("employee@example.test")
    source_ids = []
    for title, body in [
        ("DEMO circular", "DEMO: Files require completeness review.\nNo actual legal rule."),
        (
            "DEMO correspondence",
            "DEMO: Supporting service records are missing.\nIllustrative only.",
        ),
    ]:
        result = employee.post("/documents?source=true", json={"title": title, "body": body})
        assert result.status_code == 200
        source_ids.append(result.json()["id"])
    result = employee.post(
        "/agent/draft", json={"title": "DEMO office note", "source_ids": source_ids}
    )
    assert result.status_code == 200
    id = result.json()["id"]
    doc = employee.get("/documents/" + id).json()
    version = doc["versions"][0]["id"]
    assert len(doc["citations"]) == 2
    for citation in doc["citations"]:
        evidence = employee.get("/citations/" + citation["id"]).json()
        assert evidence["excerpt"] == evidence["body"].split("\n")[0]
        assert evidence["sha256"] == main.hashlib.sha256(evidence["body"].encode()).hexdigest()
    other = signin("other@example.test")
    assert other.get("/documents/" + id).status_code == 404
    assert other.get("/citations/" + doc["citations"][0]["id"]).status_code == 404
    assert other.get("/versions/" + version + "/export/docx").status_code == 404
    assert (
        other.post(
            "/agent/draft", json={"title": "Forbidden", "source_ids": source_ids}
        ).status_code
        == 404
    )
    assert (
        employee.post(
            "/versions/" + version + "/submit", json={"reviewer_email": "employee@example.test"}
        ).status_code
        == 422
    )
    approval = employee.post(
        "/versions/" + version + "/submit", json={"reviewer_email": "reviewer@example.test"}
    ).json()
    assert (
        employee.post(
            "/approvals/" + approval["id"] + "/decide",
            json={"status": "APPROVED", "comment": "self"},
        ).status_code
        == 403
    )
    reviewer = signin("reviewer@example.test")
    assert (
        reviewer.post(
            "/approvals/" + approval["id"] + "/decide",
            json={"status": "CHANGES_REQUESTED", "comment": "Please verify wording"},
        ).status_code
        == 200
    )
    approval = employee.post(
        "/versions/" + version + "/submit", json={"reviewer_email": "reviewer@example.test"}
    ).json()
    assert (
        reviewer.post(
            "/approvals/" + approval["id"] + "/decide",
            json={"status": "APPROVED", "comment": "Demo reviewed"},
        ).status_code
        == 200
    )
    import io
    import zipfile

    docx = employee.get("/versions/" + version + "/export/docx")
    assert zipfile.is_zipfile(io.BytesIO(docx.content))
    assert employee.get("/versions/" + version + "/export/pdf").content.startswith(b"%PDF")
    revision = employee.post(
        "/documents/" + id + "/versions",
        json={"title": "Revised", "body": "Unsupported new assertion"},
    ).json()
    assert (
        employee.post(
            "/versions/" + revision["id"] + "/submit",
            json={"reviewer_email": "reviewer@example.test"},
        ).status_code
        == 422
    )
    assert (
        employee.post(
            "/documents/" + source_ids[0] + "/versions",
            json={"title": "Overwrite", "body": "changed"},
        ).status_code
        == 403
    )


@pytest.fixture(autouse=True)
def isolated_database():
    main.Base.metadata.drop_all(main.engine)
    main.Base.metadata.create_all(main.engine)
    with Session(main.engine) as db:
        db.add(
            main.User(
                email="employee@example.test", password=main.hash_password("Test-password-123")
            )
        )
        db.commit()
    client.cookies.clear()
    yield


def test_preferences_search_and_source_revocation():
    employee = TestClient(main.app)
    token = employee.post(
        "/auth/login", json={"email": "employee@example.test", "password": "Test-password-123"}
    ).json()["csrf"]
    employee.headers["x-csrf-token"] = token
    assert (
        employee.put(
            "/profile/preferences",
            json={"theme": "dark", "language": "en", "display_name": "DEMO Employee"},
        ).status_code
        == 200
    )
    assert employee.get("/profile/preferences").json()["theme"] == "dark"
    assert (
        employee.put("/profile/preferences", json={"theme": "blue", "language": "en"}).status_code
        == 422
    )
    with Session(main.engine) as db:
        reviewer = main.User(
            email="reviewer@example.test",
            role="reviewer",
            password=main.hash_password("Test-password-123"),
        )
        db.add(reviewer)
        db.commit()
        db.refresh(reviewer)
        reviewer_id = reviewer.id
    review = TestClient(main.app)
    token = review.post(
        "/auth/login", json={"email": "reviewer@example.test", "password": "Test-password-123"}
    ).json()["csrf"]
    review.headers["x-csrf-token"] = token
    ids = [
        employee.post(
            "/documents?source=true",
            json={"title": "DEMO evidence " + str(i), "body": "DEMO source " + str(i)},
        ).json()["id"]
        for i in range(2)
    ]
    draft_id = employee.post("/agent/draft", json={"title": "Draft", "source_ids": ids}).json()[
        "id"
    ]
    doc = employee.get("/documents/" + draft_id).json()
    version_id = doc["versions"][0]["id"]
    approval = employee.post(
        "/versions/" + version_id + "/submit", json={"reviewer_email": "reviewer@example.test"}
    ).json()
    assert len(review.get("/search?q=evidence").json()) == 2
    assert employee.post("/documents/" + ids[0] + "/restrict/" + reviewer_id).status_code == 200
    assert len(review.get("/search?q=evidence").json()) == 1
    assert review.get("/documents/" + draft_id).status_code == 404
    assert review.get("/citations/" + doc["citations"][0]["id"]).status_code == 404
    assert review.get("/versions/" + version_id + "/export/pdf").status_code == 404
    assert (
        review.post(
            "/approvals/" + approval["id"] + "/decide",
            json={"status": "APPROVED", "comment": "Must fail after source access revoked"},
        ).status_code
        == 404
    )


def test_record_permissions_and_throttle():
    c = TestClient(main.app)
    for _ in range(5):
        assert (
            c.post(
                "/auth/login", json={"email": "unknown@example.test", "password": "wrong"}
            ).status_code
            == 401
        )
    assert (
        c.post(
            "/auth/login", json={"email": "unknown@example.test", "password": "wrong"}
        ).status_code
        == 429
    )
    token = c.post(
        "/auth/login", json={"email": "employee@example.test", "password": "Test-password-123"}
    ).json()["csrf"]
    c.headers["x-csrf-token"] = token
    assert c.post("/records/tools", json={"title": "Forbidden admin tool"}).status_code == 403
    record = c.post(
        "/records/tasks", json={"title": "DEMO follow-up", "body": "Review source completeness"}
    ).json()
    assert (
        c.patch(
            "/records/" + record["id"], json={"title": "DEMO follow-up edited", "body": "Updated"}
        ).status_code
        == 200
    )
    assert c.get("/records/tasks").json()[0]["title"] == "DEMO follow-up edited"
    assert c.get("/records/unknown").status_code == 404
