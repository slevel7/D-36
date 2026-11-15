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
            assert evidence["page"] == 2 and evidence["original_url"].endswith("/original")
            assert "missing records" in evidence["excerpt"]
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


def add_reviewer():
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


def test_project_collaboration_and_canonical_task_permissions():
    add_reviewer()
    c = login()
    reviewer = login("reviewer@example.test")
    other = login("other@example.test")
    project = c.post(
        "/work/projects",
        json={
            "title": "DEMO review project",
            "purpose": "Coordinate fictional file completeness reviews",
        },
    ).json()
    id = project["id"]
    assert other.get("/work/projects/" + id).status_code == 404
    assert reviewer.get("/work/projects/" + id).status_code == 403
    assert (
        c.post(
            "/work/projects/" + id + "/members",
            json={"email": "other@example.test", "role": "member"},
        ).status_code
        == 403
    )
    assert (
        c.post(
            "/work/projects/" + id + "/members",
            json={"email": "reviewer@example.test", "role": "viewer"},
        ).status_code
        == 200
    )
    assert (
        reviewer.post(
            "/work/projects/" + id + "/discussions", json={"body": "Must be denied for viewer"}
        ).status_code
        == 403
    )
    assert (
        c.post(
            "/work/projects/" + id + "/members",
            json={"email": "reviewer@example.test", "role": "member"},
        ).status_code
        == 200
    )
    task = c.post(
        "/work/tasks",
        json={
            "title": "DEMO check source evidence",
            "project_id": id,
            "assignee_email": "reviewer@example.test",
            "due_date": "2026-12-01",
        },
    ).json()
    assert reviewer.get("/work/tasks").json()[0]["id"] == task["id"]
    assert (
        reviewer.patch("/work/tasks/" + task["id"], json={"status": "Completed"}).status_code == 200
    )
    assert c.get("/work/projects/" + id).json()["tasks"][0]["status"] == "Completed"
    assert (
        reviewer.post(
            "/work/tasks/" + task["id"] + "/comments", json={"body": "Fictional records reviewed"}
        ).status_code
        == 200
    )
    assert (
        c.post(
            "/work/projects/" + id + "/meetings",
            json={
                "title": "DEMO review meeting",
                "starts": "2026-12-01T10:00:00+05:30",
                "agenda": "Review completeness and assign follow-up",
            },
        ).status_code
        == 200
    )
    assert (
        c.post(
            "/work/projects/" + id + "/discussions",
            json={"body": "Please review the sample agenda"},
        ).status_code
        == 200
    )
    source = c.post(
        "/documents?source=true",
        json={"title": "DEMO project source", "body": "Synthetic records only"},
    ).json()
    assert (
        c.post("/work/projects/" + id + "/files", json={"document_id": source["id"]}).status_code
        == 200
    )
    assert len(reviewer.get("/work/projects/" + id).json()["files"]) == 1
    reviewer_id = reviewer.get("/auth/me").json()["id"]
    assert c.post("/documents/" + source["id"] + "/restrict/" + reviewer_id).status_code == 200
    assert reviewer.get("/work/projects/" + id).json()["files"] == []
    assert any(n["category"] == "meetings" for n in reviewer.get("/workspace/notifications").json())


def test_distinct_case_lifecycles_and_separate_review():
    add_reviewer()
    c = login()
    reviewer = login("reviewer@example.test")
    other = login("other@example.test")
    pension = c.post(
        "/work/cases/pension",
        json={
            "pensioner_alias": "DEMO Pensioner A",
            "case_type": "Retirement",
            "summary": "Fictional case missing a sample supporting record",
        },
    ).json()
    id = pension["id"]
    assert other.get("/work/cases/pension/" + id).status_code == 404

    def advance(client, kind, id, status):
        return client.post(
            "/work/cases/" + kind + "/" + id + "/transition",
            json={"status": status, "note": "Fictional workflow review"},
        )

    assert advance(c, "pension", id, "COLLECTING").status_code == 200
    assert advance(c, "pension", id, "VERIFICATION").status_code == 200
    assert advance(c, "pension", id, "UNDER_REVIEW").status_code == 422
    detail = c.get("/work/cases/pension/" + id).json()
    for item in detail["checklist"]:
        assert (
            c.patch(
                "/work/cases/" + id + "/checklist/" + item["id"], json={"checked": True}
            ).status_code
            == 200
        )
    assert (
        c.post(
            "/work/cases/" + id + "/deficiencies",
            json={"body": "Sample service record needs clarification"},
        ).status_code
        == 200
    )
    assert advance(c, "pension", id, "UNDER_REVIEW").status_code == 422
    deficiency = c.get("/work/cases/pension/" + id).json()["deficiencies"][0]
    assert (
        c.post("/work/cases/" + id + "/deficiencies/" + deficiency["id"] + "/resolve").status_code
        == 200
    )
    assert advance(c, "pension", id, "UNDER_REVIEW").status_code == 200
    assert advance(c, "pension", id, "FORWARDED").status_code == 403
    assert advance(reviewer, "pension", id, "FORWARDED").status_code == 200
    assert advance(c, "pension", id, "CLOSED").status_code == 200
    grievance = c.post(
        "/work/cases/grievances",
        json={
            "complainant_alias": "DEMO Citizen B",
            "subject": "Fictional missing update",
            "channel": "Internal demo",
            "category": "Demo delay",
            "jurisdiction": "Illustrative department",
            "description": "A fictional request requires an internal update.",
        },
    ).json()
    gid = grievance["id"]
    for state in ["ASSIGNED", "INVESTIGATING", "RESPONSE_DRAFTED"]:
        assert advance(c, "grievances", gid, state).status_code == 200
    assert advance(c, "grievances", gid, "UNDER_REVIEW").status_code == 422
    assert (
        c.put(
            "/work/cases/" + gid + "/correspondence",
            json={"body": "DEMO draft response awaiting human review."},
        ).status_code
        == 200
    )
    assert advance(c, "grievances", gid, "UNDER_REVIEW").status_code == 200
    assert advance(reviewer, "grievances", gid, "INVESTIGATING").status_code == 200
    for state in ["RESPONSE_DRAFTED", "UNDER_REVIEW"]:
        assert advance(c, "grievances", gid, state).status_code == 200
    assert advance(c, "grievances", gid, "RESOLVED").status_code == 403
    assert advance(reviewer, "grievances", gid, "RESOLVED").status_code == 200
    assert advance(c, "grievances", gid, "CLOSED").status_code == 200
    task = c.post("/work/tasks", json={"title": "DEMO case follow-up", "case_id": gid}).json()
    assert (
        c.get("/work/tasks/" + task["id"]).json()["source_url"] == "/department/grievances/" + gid
    )


def test_outreach_consent_approval_optout_and_simulation_only():
    add_reviewer()
    c = login()
    reviewer = login("reviewer@example.test")
    other = login("other@example.test")
    campaign = c.post(
        "/work/campaigns",
        json={
            "name": "DEMO completeness reminder",
            "purpose": "Test consent-aware fictional delivery events",
            "script": "DEMO ONLY - please review the sample checklist.",
            "language": "en",
            "language_reviewed": True,
        },
    ).json()
    id = campaign["id"]
    assert (
        c.post(
            "/work/campaigns/" + id + "/contacts", json={"alias": "DEMO contact A", "consent": True}
        ).status_code
        == 200
    )
    assert (
        c.post(
            "/work/campaigns/" + id + "/contacts",
            json={"alias": "DEMO contact B", "consent": False},
        ).status_code
        == 200
    )
    assert (
        c.post(
            "/work/campaigns/" + id + "/contacts", json={"alias": "DEMO contact A", "consent": True}
        ).status_code
        == 409
    )
    assert c.post("/work/campaigns/" + id + "/simulate").status_code == 409
    assert (
        c.post(
            "/work/campaigns/" + id + "/submit", json={"reviewer_email": "reviewer@example.test"}
        ).status_code
        == 200
    )
    assert (
        c.post(
            "/work/campaigns/" + id + "/decision",
            json={"status": "APPROVED", "comment": "Cannot self approve"},
        ).status_code
        == 403
    )
    assert (
        reviewer.post(
            "/work/campaigns/" + id + "/decision",
            json={"status": "APPROVED", "comment": "Reviewed fictional consent and script"},
        ).status_code
        == 200
    )
    result = c.post("/work/campaigns/" + id + "/simulate").json()
    assert result["real_messages_sent"] == 0
    assert c.post("/work/campaigns/" + id + "/simulate").status_code == 409
    detail = c.get("/work/campaigns/" + id).json()
    assert {d["status"] for d in detail["deliveries"]} == {
        "SIMULATED_DELIVERED",
        "SKIPPED_NO_CONSENT_OR_OPT_OUT",
    }
    contact = detail["contacts"][0]
    assert (
        c.patch(
            "/work/campaigns/" + id + "/contacts/" + contact["id"],
            json={"opt_out": True, "feedback": "Fictional manual feedback"},
        ).status_code
        == 200
    )
    assert (
        c.patch(
            "/work/campaigns/" + id + "/contacts/" + contact["id"], json={"opt_out": False}
        ).status_code
        == 422
    )
    assert other.get("/work/campaigns/" + id).status_code == 404


def test_configured_tools_and_explicit_idempotent_agent_actions():
    employee = login()
    administrator = login("admin@example.test")
    other = login("other@example.test")
    department = next(
        d for d in employee.get("/workspace/departments").json() if d["name"] == "DEMO Pension"
    )
    payload = {
        "title": "DEMO movement register",
        "description": "An internal fictional file movement register",
        "department_id": department["id"],
        "roles": ["employee"],
        "fields": [
            {"name": "subject", "label": "Subject", "type": "text", "required": True},
            {"name": "pages", "label": "Pages", "type": "number", "required": True},
        ],
        "states": ["Received", "Assigned", "Closed"],
    }
    assert employee.post("/configured/admin/tools", json=payload).status_code == 403
    config = administrator.post("/configured/admin/tools", json=payload)
    assert config.status_code == 200
    config = config.json()
    id = config["tool_id"]
    assert employee.get("/configured/tools/" + id).status_code == 403
    assert (
        administrator.post(
            "/configured/admin/tools/" + config["id"] + "/activate",
            json={"comment": "Reviewed sample form and employee scope"},
        ).status_code
        == 200
    )
    assert id in {t["id"] for t in employee.get("/workspace/tools?tab=department").json()}
    assert other.get("/configured/tools/" + id).status_code == 404
    assert (
        employee.post(
            "/configured/tools/" + id + "/entries", json={"values": {"pages": 1}}
        ).status_code
        == 422
    )
    assert (
        employee.post(
            "/configured/tools/" + id + "/entries",
            json={"values": {"subject": "DEMO file", "pages": "not a number"}},
        ).status_code
        == 422
    )
    entry = employee.post(
        "/configured/tools/" + id + "/entries",
        json={"values": {"subject": "DEMO file", "pages": 4}},
    ).json()
    assert (
        employee.patch(
            "/configured/tools/" + id + "/entries/" + entry["id"], json={"status": "Closed"}
        ).status_code
        == 409
    )
    assert (
        employee.patch(
            "/configured/tools/" + id + "/entries/" + entry["id"], json={"status": "Assigned"}
        ).status_code
        == 200
    )
    before = len(employee.get("/work/tasks?view=team").json())
    proposal = employee.post(
        "/configured/actions/propose-task",
        json={
            "title": "DEMO confirmed follow-up",
            "description": "Explicitly proposed, not inferred",
        },
    ).json()
    assert len(employee.get("/work/tasks?view=team").json()) == before
    assert other.post("/configured/actions/" + proposal["id"] + "/confirm").status_code == 404
    confirmed = employee.post("/configured/actions/" + proposal["id"] + "/confirm").json()
    replay = employee.post("/configured/actions/" + proposal["id"] + "/confirm").json()
    assert confirmed["id"] == replay["id"] and replay["replayed"] is True
    assert len(employee.get("/work/tasks?view=team").json()) == before + 1
    assert any(
        a["action"].startswith("agent:confirmed_task")
        for a in employee.get("/workspace/activity").json()
    )


def test_membership_reviewer_rights_are_effective_without_changing_identity_role():
    employee = login()
    target = login("other@example.test")
    administrator = login("admin@example.test")
    department = next(
        d for d in employee.get("/workspace/departments").json() if d["name"] == "DEMO Pension"
    )
    request = target.post(
        "/workspace/access-requests",
        json={
            "department_id": department["id"],
            "division_id": department["divisions"][0]["id"],
            "reason": "Review fictional pension department drafts",
            "requested_role": "reviewer",
            "duration_days": 3,
        },
    ).json()
    assert (
        administrator.post(
            "/workspace/admin/access-requests/" + request["id"] + "/decision",
            json={"status": "APPROVED", "comment": "Scoped reviewer access for fictional work"},
        ).status_code
        == 200
    )
    membership = next(
        m
        for m in target.get("/workspace/bootstrap").json()["memberships"]
        if m["department_id"] == department["id"]
    )
    assert (
        target.post("/workspace/switch", json={"membership_id": membership["id"]}).status_code
        == 200
    )
    assert target.get("/auth/me").json()["role"] == "reviewer"
    ids = [
        employee.post(
            "/documents?source=true",
            json={
                "title": "DEMO source " + str(i),
                "body": "DEMO supporting records need human review " + str(i),
            },
        ).json()["id"]
        for i in range(2)
    ]
    draft = employee.post(
        "/agent/draft", json={"title": "DEMO scoped-review note", "source_ids": ids}
    ).json()
    version = employee.get("/documents/" + draft["id"]).json()["versions"][0]["id"]
    approval = employee.post(
        "/versions/" + version + "/submit", json={"reviewer_email": "other@example.test"}
    )
    assert approval.status_code == 200
    assert (
        target.post(
            "/approvals/" + approval.json()["id"] + "/decide",
            json={
                "status": "APPROVED",
                "comment": "Reviewed with explicitly approved department role",
            },
        ).status_code
        == 200
    )
    with Session(main.engine) as session:
        identity = session.scalar(select(main.User).where(main.User.email == "other@example.test"))
        assert identity.role == "employee" and identity.department == "DEMO Other"


def test_pension_register_operations_and_review_permissions():
    add_reviewer()
    c, reviewer, other = login(), login("reviewer@example.test"), login("other@example.test")
    case = c.post(
        "/work/cases/pension",
        json={
            "pensioner_alias": "Demo pensioner",
            "case_type": "Family",
            "summary": "Family pension supporting evidence review",
        },
    ).json()
    path = "/pension/cases/" + case["id"]
    assert other.get(path + "/register").status_code == 404
    data = {
        "scheme": "Social welfare",
        "scheme_name": "Scheme awaiting rule verification",
        "payment_status": "Missing",
        "payment_period": "2026-11",
        "service_start": "2020-01-01",
        "service_end": "2019-01-01",
    }
    assert c.put(path + "/register", json=data).status_code == 422
    data["service_end"] = "2026-01-01"
    assert c.put(path + "/register", json=data).status_code == 200
    assert c.get(path + "/register").json()["register"]["payment_status"] == "Missing"
    assert reviewer.put(path + "/register", json=data).status_code == 403
    op = c.post(
        path + "/operations",
        json={
            "kind": "Life certificate",
            "notes": "Review attached certificate against source records",
            "due_date": "2026-12-01",
        },
    ).json()
    endpoint = "/pension/operations/" + op["id"] + "/decision"
    assert (
        c.post(endpoint, json={"action": "complete", "note": "Premature completion"}).status_code
        == 403
    )
    assert (
        c.post(
            endpoint,
            json={
                "action": "submit",
                "reviewer_email": "reviewer@example.test",
                "note": "Please review supporting evidence",
            },
        ).status_code
        == 200
    )
    assert (
        c.post(endpoint, json={"action": "approve", "note": "Self approval attempt"}).status_code
        == 403
    )
    assert (
        reviewer.post(
            endpoint, json={"action": "return", "note": "Missing source evidence"}
        ).status_code
        == 200
    )
    assert (
        c.post(
            endpoint,
            json={
                "action": "submit",
                "reviewer_email": "reviewer@example.test",
                "note": "Evidence corrected",
            },
        ).status_code
        == 200
    )
    assert (
        reviewer.post(
            endpoint, json={"action": "approve", "note": "Reviewed internal work only"}
        ).status_code
        == 200
    )
    assert (
        c.post(
            endpoint, json={"action": "complete", "note": "Certificate review recorded"}
        ).status_code
        == 200
    )


def test_legacy_import_preview_duplicates_validation_and_scope():
    c, other = login(), login("other@example.test")
    header = "external_id,pensioner_alias,case_type,retirement_date,summary,scheme,scheme_name\n"
    row = "SRC-001,Demo beneficiary,Retirement,2026-06-30,Imported case requires evidence review,Government employee,Demo scheme\n"

    def preview(content):
        return c.post(
            "/pension/imports/preview",
            data={"source": "Existing pension portal"},
            files={"file": ("export.csv", content.encode(), "text/csv")},
        )

    before = len(c.get("/work/cases/pension").json())
    r = preview(header + row + row)
    assert r.status_code == 200, r.text
    result = r.json()
    assert result["rows"][1]["duplicate"]
    assert len(c.get("/work/cases/pension").json()) == before
    endpoint = "/pension/imports/" + result["id"] + "/confirm"
    assert other.post(endpoint).status_code == 404
    assert c.post(endpoint).json() == {"imported": 1, "skipped": 1}
    assert c.post(endpoint).json() == {"imported": 1, "skipped": 1}
    assert len(c.get("/work/cases/pension").json()) == before + 1
    again = preview(header + row).json()
    assert again["rows"][0]["duplicate"]
    assert c.post("/pension/imports/" + again["id"] + "/confirm").json()["imported"] == 0
    invalid = preview(header + row.replace("Government employee", "Unsupported scheme")).json()
    assert invalid["rows"][0]["errors"]
    assert c.post("/pension/imports/" + invalid["id"] + "/confirm").status_code == 422
    assert (
        c.post(
            "/pension/connections",
            json={
                "name": "Existing portal",
                "website": "https://example.test/pension",
                "method": "API",
                "purpose": "Import authorised pension records",
            },
        ).json()["status"]
        == "REQUESTED_NOT_CONNECTED"
    )
    assert other.get("/pension/connections").json() == []
    assert (
        c.post(
            "/pension/connections",
            json={
                "name": "Unsafe portal",
                "website": "https://user:secret@example.test/",
                "method": "API",
                "purpose": "Import authorised pension records",
            },
        ).status_code
        == 422
    )


def test_audience_excel_import_and_formula_rejection():
    from openpyxl import Workbook

    c = login()
    campaign = c.post(
        "/work/campaigns",
        json={
            "name": "Demo pension outreach",
            "purpose": "Request missing certificates for review",
            "script": "Please provide supporting certificate records.",
            "language": "en",
            "language_reviewed": True,
        },
    ).json()
    book = Workbook()
    sheet = book.active
    sheet.append(["alias", "consent"])
    sheet.append(["Demo consenting recipient", "true"])
    sheet.append(["Demo no consent recipient", "false"])
    buffer = io.BytesIO()
    book.save(buffer)
    response = c.post(
        "/pension/imports/preview",
        data={
            "source": "Existing audience export",
            "target": "audience",
            "campaign_id": campaign["id"],
        },
        files={
            "file": (
                "audience.xlsx",
                buffer.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 200, response.text
    assert c.post("/pension/imports/" + response.json()["id"] + "/confirm").json()["imported"] == 2
    contacts = c.get("/work/campaigns/" + campaign["id"]).json()["contacts"]
    assert sorted(v["consent"] for v in contacts) == [False, True]
    report = c.get("/pension/campaigns/" + campaign["id"] + "/report")
    assert report.status_code == 200 and "NOT_SIMULATED" in report.text
    sheet.append(["=1+1", "true"])
    buffer = io.BytesIO()
    book.save(buffer)
    assert (
        c.post(
            "/pension/imports/preview",
            data={
                "source": "Existing audience export",
                "target": "audience",
                "campaign_id": campaign["id"],
            },
            files={"file": ("audience.xlsx", buffer.getvalue())},
        ).status_code
        == 422
    )
