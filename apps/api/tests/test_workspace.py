import io

import main
import pytest
import workspace as work
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


@pytest.fixture(autouse=True)
def database(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    monkeypatch.setattr(main, "engine", engine)
    main.Base.metadata.create_all(engine)
    with Session(engine) as session:
        for email, role, department in [
            ("employee@example.test", "employee", "DEMO Pension"),
            ("admin@example.test", "platform_admin", "DEMO Administration"),
            ("other@example.test", "employee", "DEMO Other"),
        ]:
            session.add(
                main.User(
                    email=email,
                    role=role,
                    department=department,
                    password=main.hash_password("Test-password-123"),
                )
            )
        session.commit()
        work.seed_workspace(session)
    yield
    engine.dispose()


def login(email="employee@example.test"):
    c = TestClient(main.app)
    r = c.post("/auth/login", json={"email": email, "password": "Test-password-123"})
    assert r.status_code == 200
    c.headers["x-csrf-token"] = r.json()["csrf"]
    return c


def test_profile_settings_and_private_files():
    c = login()
    other = login("other@example.test")
    r = c.put(
        "/workspace/profile",
        json={
            "display_name": "Demo colleague",
            "phone": "12345",
            "contact_email": "demo@example.test",
            "office_address": "Demo office",
            "bio": "Fictional employee",
        },
    )
    assert (
        r.status_code == 200
        and c.get("/workspace/profile").json()["display_name"] == "Demo colleague"
    )
    assert (
        c.put(
            "/workspace/profile", json={"display_name": "No", "role": "platform_admin"}
        ).status_code
        == 422
    )
    pref = c.get("/workspace/preferences").json()
    pref["text_size"] = "large"
    pref["theme"] = "dark"
    assert c.put("/workspace/preferences", json=pref).status_code == 200
    assert c.get("/workspace/bootstrap").json()["preferences"]["text_size"] == "large"
    pref["notifications"]["security"] = False
    assert c.put("/workspace/preferences", json=pref).status_code == 422
    assert (
        c.post(
            "/workspace/profile/files", files={"file": ("bad.pdf", b"bad", "application/pdf")}
        ).status_code
        == 422
    )
    from reportlab.pdfgen import canvas

    out = io.BytesIO()
    pdf = canvas.Canvas(out)
    pdf.drawString(50, 700, "DEMO profile document")
    pdf.save()
    file = c.post(
        "/workspace/profile/files", files={"file": ("demo.pdf", out.getvalue(), "application/pdf")}
    ).json()
    assert c.get("/workspace/profile/files/" + file["id"]).content.startswith(b"%PDF")
    assert other.get("/workspace/profile/files/" + file["id"]).status_code == 404
    from PIL import Image

    out = io.BytesIO()
    Image.new("RGB", (32, 32), "black").save(out, format="PNG")
    assert (
        c.post(
            "/workspace/profile/avatar", files={"file": ("avatar.png", out.getvalue(), "image/png")}
        ).status_code
        == 200
    )
    assert c.get("/workspace/profile/avatar").headers["content-type"] == "image/png"


def test_access_decision_scope_expiry_and_notifications():
    c = login()
    administrator = login("admin@example.test")
    target = next(
        d
        for d in c.get("/workspace/departments").json()
        if d["name"] == "DEMO General Administration"
    )
    data = {
        "department_id": target["id"],
        "division_id": target["divisions"][0]["id"],
        "reason": "DEMO cross-workspace coordination",
        "duration_days": 7,
    }
    r = c.post("/workspace/access-requests", json=data)
    assert r.status_code == 200
    assert c.post("/workspace/access-requests", json=data).status_code == 409
    id = r.json()["id"]
    assert c.get("/workspace/admin/access-requests").status_code == 403
    assert (
        administrator.post(
            "/workspace/admin/access-requests/" + id + "/decision",
            json={"status": "APPROVED", "comment": "Demo access approved"},
        ).status_code
        == 200
    )
    assert (
        administrator.post(
            "/workspace/admin/access-requests/" + id + "/decision",
            json={"status": "APPROVED", "comment": "Repeated"},
        ).status_code
        == 409
    )
    memberships = c.get("/workspace/bootstrap").json()["memberships"]
    assert len(memberships) == 2
    member = next(m for m in memberships if m["department_id"] == target["id"])
    original = c.post(
        "/documents?source=true",
        json={"title": "Restricted original department", "body": "DEMO source"},
    ).json()["id"]
    assert c.post("/workspace/switch", json={"membership_id": member["id"]}).status_code == 200
    assert c.get("/auth/me").json()["department"] == "DEMO General Administration"
    assert c.get("/documents/" + original).status_code == 404
    inbox = c.get("/workspace/notifications").json()
    assert len(inbox) == 1
    assert c.post("/workspace/notifications/" + inbox[0]["id"] + "/read").status_code == 200
    assert c.get("/workspace/notifications?filter=unread").json() == []
    assert (
        administrator.post("/workspace/admin/memberships/" + member["id"] + "/revoke").status_code
        == 200
    )
    assert c.get("/workspace/bootstrap").status_code == 403


def test_tool_catalogue_persistence_order_recents_and_policy():
    c = login()
    other = login("other@example.test")
    titles = {t["id"] for t in c.get("/workspace/tools?tab=department").json()}
    assert "pension" in titles
    assert other.post("/workspace/tools/pension/open").status_code == 404
    assert c.post("/workspace/tools/calendar/open").status_code == 409
    assert c.get("/workspace/tools?tab=connected").json() == []
    for id in ["documents", "tasks"]:
        assert c.post("/workspace/tools/" + id + "/favourite").status_code == 200
    assert (
        c.put("/workspace/favourites/order", json={"ids": ["tasks", "documents"]}).status_code
        == 200
    )
    assert [t["id"] for t in c.get("/workspace/tools?tab=favourites").json()] == [
        "tasks",
        "documents",
    ]
    assert c.post("/workspace/tools/documents/open").json()["href"] == "/documents"
    assert c.get("/workspace/tools?tab=recent").json()[0]["id"] == "documents"
    assert c.post("/workspace/tools/documents/dismiss").status_code == 200
    assert "documents" not in {t["id"] for t in c.get("/workspace/tools?tab=recommended").json()}
    assert c.delete("/workspace/tools/recent").status_code == 200
    assert c.get("/workspace/tools?tab=recent").json() == []
    assert any(a["action"] == "tool:open:documents" for a in c.get("/workspace/activity").json())
    assert (
        c.post(
            "/workspace/tool-requests",
            json={"title": "Demo register", "reason": "Need an authorised register for demo work"},
        ).status_code
        == 200
    )
    assert c.get("/workspace/tool-summary").json()["pending_requests"] == 1


def test_security_support_providers_and_conversation():
    c = login()
    second = login()
    other = login("other@example.test")
    sessions = c.get("/workspace/security/sessions").json()
    assert len(sessions) == 2
    id = next(s["id"] for s in sessions if not s["current"])
    assert other.delete("/workspace/security/sessions/" + id).status_code == 404
    assert c.delete("/workspace/security/sessions/" + id).status_code == 200
    assert second.get("/auth/me").status_code == 401
    assert (
        c.post(
            "/workspace/security/password",
            json={"current_password": "wrong", "new_password": "Different-password-123"},
        ).status_code
        == 403
    )
    assert (
        c.post(
            "/workspace/security/password",
            json={
                "current_password": "Test-password-123",
                "new_password": "Different-password-123",
            },
        ).status_code
        == 200
    )
    assert c.get("/workspace/notifications").json()[0]["category"] == "security"
    assert all(
        p["status"] == "Not configured" for p in c.get("/workspace/providers").json()["providers"]
    )
    assert (
        c.post(
            "/workspace/providers/google/request",
            json={"reason": "Need approved demo calendar access"},
        ).status_code
        == 200
    )
    ticket = c.post(
        "/workspace/support",
        json={
            "category": "issue",
            "subject": "Demo support ticket",
            "message": "Please inspect this fictional issue.",
        },
    )
    assert ticket.status_code == 200 and len(c.get("/workspace/support").json()) == 1
    assert other.get("/workspace/support").json() == []
    chat = c.post("/workspace/conversations", json={"content": "First demo message"}).json()
    assert (
        c.post(
            "/workspace/conversations/" + chat["id"] + "/messages",
            json={"content": "Second demo message"},
        ).status_code
        == 200
    )
    messages = c.get("/workspace/conversations/" + chat["id"]).json()["messages"]
    assert len(messages) == 4 and any("AI not configured" in m["content"] for m in messages)
    assert other.get("/workspace/conversations/" + chat["id"]).status_code == 404


def test_original_upload_revision_citations_and_review_exports():
    import hashlib
    import zipfile

    from docx import Document as Word
    from files import ReviewEvent
    from reportlab.pdfgen import canvas

    employee = login()
    other = login("other@example.test")
    with Session(main.engine) as session:
        session.add(
            main.User(
                email="reviewer@example.test",
                role="reviewer",
                department="DEMO Pension",
                password=main.hash_password("Test-password-123"),
            )
        )
        session.commit()
        work.seed_workspace(session)
    reviewer = login("reviewer@example.test")
    output = io.BytesIO()
    pdf = canvas.Canvas(output)
    pdf.drawString(40, 750, "DEMO circular: completeness review is required.")
    pdf.showPage()
    pdf.drawString(40, 750, "DEMO page two: missing records need clarification.")
    pdf.save()
    pdf_bytes = output.getvalue()
    pdf_source = employee.post(
        "/files/upload", files={"file": ("demo-circular.pdf", pdf_bytes, "application/pdf")}
    )
    assert pdf_source.status_code == 200
    pdf_source = pdf_source.json()
    assert pdf_source["sha256"] == hashlib.sha256(pdf_bytes).hexdigest()
    paragraphs = employee.get("/files/versions/" + pdf_source["version_id"] + "/passages").json()
    assert {p["page"] for p in paragraphs} == {1, 2}
    assert (
        employee.get("/files/versions/" + pdf_source["version_id"] + "/original").content
        == pdf_bytes
    )
    assert other.get("/files/versions/" + pdf_source["version_id"] + "/original").status_code == 404
    word = Word()
    word.add_paragraph("DEMO correspondence: supporting records have not been supplied.")
    word.add_paragraph("DEMO: request a human completeness check.")
    output = io.BytesIO()
    word.save(output)
    word_source = employee.post(
        "/files/upload",
        files={
            "file": (
                "demo-correspondence.docx",
                output.getvalue(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    ).json()
    assert (
        len(employee.get("/files/versions/" + word_source["version_id"] + "/passages").json()) == 2
    )
    assert (
        employee.post(
            "/files/upload", files={"file": ("fake.pdf", b"not a pdf", "application/pdf")}
        ).status_code
        == 422
    )
    draft = employee.post(
        "/agent/draft",
        json={
            "title": "DEMO pension office note",
            "source_ids": [pdf_source["id"], word_source["id"]],
        },
    ).json()
    document = employee.get("/documents/" + draft["id"]).json()
    original = document["versions"][0]
    assert len(document["citations"]) == 2
    for c in document["citations"]:
        evidence = employee.get("/citations/" + c["id"]).json()
        assert evidence["excerpt"] in evidence["body"]
        if evidence["document"].endswith(".pdf"):
            assert evidence["page"] == 1 and evidence["original_url"].endswith("/original")
    suggestions = employee.get("/files/documents/" + draft["id"] + "/recommendations").json()
    assert len(suggestions) == 3
    assert (
        employee.post(
            "/files/recommendations/" + suggestions[0]["id"], json={"status": "ACCEPTED"}
        ).status_code
        == 200
    )
    document = employee.get("/documents/" + draft["id"]).json()
    revision = document["versions"][-1]
    assert len(document["versions"]) == 2
    diff = employee.get(
        "/files/documents/" + draft["id"] + "/compare",
        params={"before": original["id"], "after": revision["id"]},
    ).json()["diff"]
    assert "+Recommendation (accepted suggestion)" in diff
    request = employee.post(
        "/versions/" + revision["id"] + "/submit", json={"reviewer_email": "reviewer@example.test"}
    )
    assert request.status_code == 200
    request = request.json()
    assert (
        employee.post(
            "/approvals/" + request["id"] + "/decide",
            json={"status": "APPROVED", "comment": "Self approval"},
        ).status_code
        == 403
    )
    assert (
        reviewer.post(
            "/approvals/" + request["id"] + "/decide",
            json={"status": "CHANGES_REQUESTED", "comment": "Please review wording"},
        ).status_code
        == 200
    )
    new_body = revision["body"] + "\nRecommendation: maintain a human follow-up register."
    revised = employee.post(
        "/documents/" + draft["id"] + "/versions",
        json={"title": "DEMO pension office note", "body": new_body},
    ).json()
    pending = employee.post(
        "/versions/" + revised["id"] + "/submit", json={"reviewer_email": "reviewer@example.test"}
    ).json()
    latest = employee.post(
        "/documents/" + draft["id"] + "/versions",
        json={
            "title": "DEMO pension office note",
            "body": new_body + "\nRecommendation: review weekly.",
        },
    ).json()
    assert (
        reviewer.post(
            "/approvals/" + pending["id"] + "/decide",
            json={"status": "APPROVED", "comment": "Stale version"},
        ).status_code
        == 409
    )
    pending = employee.post(
        "/versions/" + latest["id"] + "/submit", json={"reviewer_email": "reviewer@example.test"}
    ).json()
    assert (
        reviewer.post(
            "/approvals/" + pending["id"] + "/decide",
            json={"status": "APPROVED", "comment": "Reviewed fictional evidence and suggestions"},
        ).status_code
        == 200
    )
    assert any(
        n["category"] == "approvals" for n in reviewer.get("/workspace/notifications").json()
    )
    assert any(
        n["category"] == "approvals" for n in employee.get("/workspace/notifications").json()
    )
    for fmt in ["docx", "pdf", "pptx", "xlsx"]:
        result = employee.get("/versions/" + latest["id"] + "/export/" + fmt)
        assert result.status_code == 200
        assert (
            result.content.startswith(b"%PDF")
            if fmt == "pdf"
            else zipfile.is_zipfile(io.BytesIO(result.content))
        )
    invented = employee.post(
        "/documents/" + draft["id"] + "/versions",
        json={
            "title": "DEMO pension office note",
            "body": new_body.replace("Sourced facts", "Sourced facts\nRule 999 is mandatory."),
        },
    ).json()
    assert (
        employee.post(
            "/versions/" + invented["id"] + "/submit",
            json={"reviewer_email": "reviewer@example.test"},
        ).status_code
        == 422
    )
    with Session(main.engine) as session:
        assert len(session.scalars(select(ReviewEvent)).all()) == 2
    assert (
        employee.get("/files/versions/" + pdf_source["version_id"] + "/original").content
        == pdf_bytes
    )
