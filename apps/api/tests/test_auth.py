import os

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
