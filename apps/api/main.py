import hashlib
import hmac
import math
import os
import secrets
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import BigInteger, ForeignKey, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///./brahma.db"))


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String, unique=True)
    password: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="employee")
    department: Mapped[str] = mapped_column(String, default="DEMO Pension")


class LoginSession(Base):
    __tablename__ = "sessions"
    token: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    csrf: Mapped[str] = mapped_column(String)
    expires: Mapped[int]


class Audit(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    actor: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    created: Mapped[int] = mapped_column(default=lambda: int(time.time()))


def hash_password(password: str, salt=None):
    salt = salt or secrets.token_hex(16)
    return (
        salt + ":" + hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    )


def verify(password, encoded):
    return hmac.compare_digest(hash_password(password, encoded.split(":")[0]), encoded)


def db():
    with Session(engine) as session:
        yield session


def current(request: Request, session: Session = Depends(db)):
    token = hashlib.sha256(request.cookies.get("brahma_session", "").encode()).hexdigest()
    login = session.get(LoginSession, token)
    if not login or login.expires < time.time():
        raise HTTPException(401, "Sign in required")
    if request.method not in ("GET", "HEAD") and not hmac.compare_digest(
        request.headers.get("x-csrf-token", ""), login.csrf
    ):
        raise HTTPException(403, "CSRF validation failed")
    user = session.get(User, login.user_id)
    if not user:
        raise HTTPException(401, "Session revoked")
    return user


@asynccontextmanager
async def lifespan(app):
    yield


app = FastAPI(title="BrahmaGPT API", lifespan=lifespan)


class Credentials(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


@app.get("/health")
def health():
    return {"status": "ok", "ai": "DEMO deterministic; no external provider configured"}


@app.post("/auth/login")
def login(data: Credentials, response: Response, session: Session = Depends(db)):
    # Database-backed throttling survives process restarts; no password or email in audit.
    key = hashlib.sha256(data.email.lower().encode()).hexdigest()
    attempts = session.scalars(
        select(Audit).where(
            Audit.actor == key, Audit.action == "login_failed", Audit.created > time.time() - 300
        )
    ).all()
    if len(attempts) >= 5:
        retry_after = max(1, math.ceil(sorted(a.created for a in attempts)[-5] + 300 - time.time()))
        raise HTTPException(
            429,
            "Too many failed sign-in attempts. Please wait before trying again.",
            headers={"Retry-After": str(retry_after)},
        )
    user = session.scalar(select(User).where(User.email == data.email.lower()))
    valid = verify(data.password, user.password if user else DUMMY_PASSWORD)
    if not user or not valid:
        session.add(Audit(actor=key, action="login_failed"))
        session.commit()
        raise HTTPException(401, "Invalid credentials")
    raw, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    session.add(
        LoginSession(
            token=hashlib.sha256(raw.encode()).hexdigest(),
            user_id=user.id,
            csrf=csrf,
            expires=int(time.time()) + 28800,
        )
    )
    session.add(Audit(actor=user.id, action="login"))
    session.commit()
    response.set_cookie(
        "brahma_session",
        raw,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE") == "true",
        samesite="strict",
        max_age=28800,
    )
    return {"csrf": csrf}


DUMMY_PASSWORD = hash_password(secrets.token_urlsafe(32))


@app.get("/auth/me")
def me(request: Request, user: User = Depends(current), session: Session = Depends(db)):
    token = hashlib.sha256(request.cookies["brahma_session"].encode()).hexdigest()
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "department": user.department,
        "csrf": session.get(LoginSession, token).csrf,
    }


@app.post("/auth/logout")
def logout(
    request: Request,
    response: Response,
    user: User = Depends(current),
    session: Session = Depends(db),
):
    token = hashlib.sha256(request.cookies["brahma_session"].encode()).hexdigest()
    session.delete(session.get(LoginSession, token))
    session.commit()
    response.delete_cookie("brahma_session")
    return {"revoked": True}


@app.get("/admin/audit")
def audit(user: User = Depends(current), session: Session = Depends(db)):
    if user.role != "platform_admin":
        raise HTTPException(403, "Administrator role required")
    return [
        {"actor": a.actor, "action": a.action, "created": a.created}
        for a in session.scalars(select(Audit).order_by(Audit.created.desc()).limit(100))
    ]


class Record(Base):
    __tablename__ = "records"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    department: Mapped[str] = mapped_column(String)
    owner: Mapped[str] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    body: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="Draft")


class RecordInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(default="", max_length=50000)


KINDS = {"projects", "tasks", "pension", "grievances", "tools", "chats"}


def scoped_record(id, user, session):
    record = session.get(Record, id)
    if not record or record.department != user.department:
        raise HTTPException(404, "Record not found")
    return record


@app.get("/records/{kind}")
def records(kind: str, user: User = Depends(current), session: Session = Depends(db)):
    if kind not in KINDS:
        raise HTTPException(404)
    return session.scalars(
        select(Record).where(Record.kind == kind, Record.department == user.department)
    ).all()


@app.post("/records/{kind}")
def create_record(
    kind: str, data: RecordInput, user: User = Depends(current), session: Session = Depends(db)
):
    if kind not in KINDS:
        raise HTTPException(404)
    if kind == "tools" and user.role != "platform_admin":
        raise HTTPException(403)
    record = Record(
        kind=kind, title=data.title, body=data.body, owner=user.id, department=user.department
    )
    session.add(record)
    session.add(Audit(actor=user.id, action="create:" + kind))
    session.commit()
    session.refresh(record)
    return record


@app.patch("/records/{id}")
def edit_record(
    id: str, data: RecordInput, user: User = Depends(current), session: Session = Depends(db)
):
    record = scoped_record(id, user, session)
    if record.owner != user.id:
        raise HTTPException(403)
    record.title, record.body = data.title, data.body
    session.add(Audit(actor=user.id, action="edit:" + id))
    session.commit()
    return {"saved": True}


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    department: Mapped[str] = mapped_column(String)
    owner: Mapped[str] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String)
    source: Mapped[bool] = mapped_column(default=False)


class Version(Base):
    __tablename__ = "document_versions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    body: Mapped[str] = mapped_column(Text)
    digest: Mapped[str] = mapped_column(String)
    created: Mapped[int] = mapped_column(BigInteger, default=time.time_ns)


class Citation(Base):
    __tablename__ = "citations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"))
    source_version: Mapped[str] = mapped_column(ForeignKey("document_versions.id"))
    paragraph: Mapped[int]
    excerpt: Mapped[str] = mapped_column(Text)


class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"))
    requester: Mapped[str] = mapped_column(ForeignKey("users.id"))
    reviewer: Mapped[str] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String, default="UNDER_REVIEW")
    comment: Mapped[str] = mapped_column(Text, default="")


def document_access(id, user, session):
    document = session.get(Document, id)
    if (
        not document
        or document.department != user.department
        or session.get(DocumentRestriction, (id, user.id))
    ):
        raise HTTPException(404, "Document not found")
    return document


def add_version(document, body, session):
    version = Version(
        document_id=document.id, body=body, digest=hashlib.sha256(body.encode()).hexdigest()
    )
    session.add(version)
    session.flush()
    return version


@app.get("/documents")
def documents(user: User = Depends(current), session: Session = Depends(db)):
    candidates = session.scalars(
        select(Document).where(Document.department == user.department)
    ).all()
    return [d for d in candidates if not session.get(DocumentRestriction, (d.id, user.id))]


@app.post("/documents")
def new_document(
    data: RecordInput,
    source: bool = False,
    user: User = Depends(current),
    session: Session = Depends(db),
):
    document = Document(title=data.title, source=source, department=user.department, owner=user.id)
    session.add(document)
    session.flush()
    add_version(document, data.body, session)
    session.add(Audit(actor=user.id, action="document:create:" + document.id))
    session.commit()
    session.refresh(document)
    return document


@app.get("/documents/{id}")
def get_document(id: str, user: User = Depends(current), session: Session = Depends(db)):
    document = document_access(id, user, session)
    versions = session.scalars(
        select(Version).where(Version.document_id == id).order_by(Version.created, Version.id)
    ).all()
    for version in versions:
        for c in session.scalars(select(Citation).where(Citation.version_id == version.id)):
            source_version = session.get(Version, c.source_version)
            document_access(source_version.document_id, user, session)
    return {
        "document": document,
        "versions": versions,
        "citations": session.scalars(
            select(Citation).where(Citation.version_id.in_([v.id for v in versions]))
        ).all(),
    }


@app.post("/documents/{id}/versions")
def save_version(
    id: str, data: RecordInput, user: User = Depends(current), session: Session = Depends(db)
):
    document = document_access(id, user, session)
    if document.owner != user.id or document.source:
        raise HTTPException(403, "Source originals are immutable")
    version = add_version(document, data.body, session)
    session.add(Audit(actor=user.id, action="document:revise:" + id))
    session.commit()
    session.refresh(version)
    return version


class DraftInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    source_ids: list[str] = Field(min_length=2, max_length=10)


@app.post("/agent/draft")
def draft(data: DraftInput, user: User = Depends(current), session: Session = Depends(db)):
    sources = []
    for id in dict.fromkeys(data.source_ids):
        document = document_access(id, user, session)
        if not document.source:
            raise HTTPException(422, "Select original source documents")
        version = session.scalar(select(Version).where(Version.document_id == id))
        if not version or not version.body.strip():
            raise HTTPException(422, "Source text is empty")
        sources.append(version)
    if len(sources) < 2:
        raise HTTPException(422, "Two distinct sources required")
    document = Document(title=data.title, department=user.department, owner=user.id, source=False)
    session.add(document)
    session.flush()
    body = (
        "AI-assisted draft — requires review\nDEMO deterministic excerpt compilation; no legal verification.\n\n"
        + data.title
        + "\n\nSourced facts\n"
    )
    for i, v in enumerate(sources):
        body += f"[{i + 1}] " + v.body.split("\n")[0] + "\n\n"
    body += "Recommendations (suggestions): Review completeness and obtain missing facts before issuing correspondence.\nUnknown: recipients, reference number, authority and signature. Source not verified for any additional claims."
    version = add_version(document, body, session)
    for v in sources:
        session.add(
            Citation(
                version_id=version.id,
                source_version=v.id,
                paragraph=1,
                excerpt=v.body.split("\n")[0],
            )
        )
    session.add(Audit(actor=user.id, action="agent:demo_draft:" + document.id))
    session.commit()
    return {
        "id": document.id,
        "mode": "DEMO deterministic",
        "recommendations": [
            "Review completeness",
            "Verify authority and recipients; suggestion only",
        ],
    }


@app.get("/citations/{id}")
def citation(id: str, user: User = Depends(current), session: Session = Depends(db)):
    c = session.get(Citation, id)
    if not c:
        raise HTTPException(404)
    parent = session.get(Version, c.version_id)
    document_access(parent.document_id, user, session)
    source = session.get(Version, c.source_version)
    document = document_access(source.document_id, user, session)
    return {
        "document": document.title,
        "version": source.id,
        "sha256": source.digest,
        "paragraph": c.paragraph,
        "excerpt": c.excerpt,
        "body": source.body,
        "anchor": "paragraph-1",
        "limitation": "Text paragraph anchor; no pagination",
    }


class ApprovalInput(BaseModel):
    reviewer_email: str


@app.post("/versions/{id}/submit")
def submit(
    id: str, data: ApprovalInput, user: User = Depends(current), session: Session = Depends(db)
):
    version = session.get(Version, id)
    if not version:
        raise HTTPException(404)
    document = document_access(version.document_id, user, session)
    if document.owner != user.id:
        raise HTTPException(403)
    reviewer = session.scalar(
        select(User).where(
            User.email == data.reviewer_email,
            User.department == user.department,
            User.role == "reviewer",
        )
    )
    if not reviewer or reviewer.id == user.id:
        raise HTTPException(422, "Separate authorised reviewer required")
    if not session.scalar(select(Citation).where(Citation.version_id == id)):
        raise HTTPException(422, "Grounded citations required; revised drafts must be regrounded")
    approval = Approval(version_id=id, requester=user.id, reviewer=reviewer.id)
    session.add(approval)
    session.add(Audit(actor=user.id, action="approval:submit:" + id))
    session.commit()
    session.refresh(approval)
    return approval


@app.get("/approvals")
def approvals(user: User = Depends(current), session: Session = Depends(db)):
    return session.scalars(
        select(Approval).where((Approval.requester == user.id) | (Approval.reviewer == user.id))
    ).all()


class Decision(BaseModel):
    status: str
    comment: str = Field(min_length=1, max_length=5000)


@app.post("/approvals/{id}/decide")
def decide(id: str, data: Decision, user: User = Depends(current), session: Session = Depends(db)):
    approval = session.get(Approval, id)
    if not approval or approval.reviewer != user.id or user.role != "reviewer":
        raise HTTPException(403)
    if approval.status != "UNDER_REVIEW" or data.status not in {
        "APPROVED",
        "CHANGES_REQUESTED",
        "REJECTED",
    }:
        raise HTTPException(422)
    version = session.get(Version, approval.version_id)
    document_access(version.document_id, user, session)
    for c in session.scalars(select(Citation).where(Citation.version_id == version.id)):
        source_version = session.get(Version, c.source_version)
        document_access(source_version.document_id, user, session)
    approval.status, approval.comment = data.status, data.comment
    session.add(Audit(actor=user.id, action="approval:" + data.status + ":" + id))
    session.commit()
    return {"status": data.status}


@app.get("/versions/{id}/export/{format}")
def export(id: str, format: str, user: User = Depends(current), session: Session = Depends(db)):
    from io import BytesIO

    from docx import Document as WordDocument
    from reportlab.pdfgen import canvas

    version = session.get(Version, id)
    if not version:
        raise HTTPException(404)
    document_access(version.document_id, user, session)
    citations = session.scalars(select(Citation).where(Citation.version_id == id)).all()
    evidence = []
    for c in citations:
        source = session.get(Version, c.source_version)
        document_access(source.document_id, user, session)
        evidence.append(f"{source.id} SHA256 {source.digest} paragraph {c.paragraph}: {c.excerpt}")
    text = (
        "REVIEW COPY — not an issued official document\n"
        + version.body
        + "\nEvidence appendix\n"
        + "\n".join(evidence)
    )
    out = BytesIO()
    if format == "docx":
        doc = WordDocument()
        for line in text.splitlines():
            doc.add_paragraph(line)
        doc.save(out)
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif format == "pdf":
        import textwrap

        pdf = canvas.Canvas(out)
        y = 800
        for line in text.splitlines():
            for piece in textwrap.wrap(line, 90) or [""]:
                if y < 50:
                    pdf.showPage()
                    y = 800
                pdf.drawString(40, y, piece)
                y -= 14
        pdf.save()
        mime = "application/pdf"
    else:
        raise HTTPException(422, "Supported: docx, pdf")
    session.add(Audit(actor=user.id, action="export:" + id))
    session.commit()
    return Response(
        out.getvalue(),
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="review-copy.{format}"'},
    )


class DocumentRestriction(Base):
    __tablename__ = "document_restrictions"
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)


class Preference(Base):
    __tablename__ = "preferences"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    theme: Mapped[str] = mapped_column(String, default="system")
    language: Mapped[str] = mapped_column(String, default="en")
    display_name: Mapped[str] = mapped_column(String, default="")


class PreferencesInput(BaseModel):
    theme: str = Field(pattern="^(light|dark|system)$")
    language: str = Field(pattern="^(en)$")
    display_name: str = Field(default="", max_length=100)


@app.get("/profile/preferences")
def preferences(user: User = Depends(current), session: Session = Depends(db)):
    value = session.get(Preference, user.id)
    return {
        "theme": value.theme if value else "system",
        "language": "en",
        "display_name": value.display_name if value else "",
    }


@app.put("/profile/preferences")
def save_preferences(
    data: PreferencesInput, user: User = Depends(current), session: Session = Depends(db)
):
    value = session.get(Preference, user.id)
    if not value:
        value = Preference(user_id=user.id)
        session.add(value)
    value.theme, value.language, value.display_name = data.theme, data.language, data.display_name
    session.add(Audit(actor=user.id, action="profile:preferences"))
    session.commit()
    return {"saved": True}


@app.post("/documents/{id}/restrict/{user_id}")
def restrict_document(
    id: str, user_id: str, user: User = Depends(current), session: Session = Depends(db)
):
    document = document_access(id, user, session)
    if document.owner != user.id or user_id == user.id:
        raise HTTPException(403)
    target = session.get(User, user_id)
    if not target or target.department != user.department:
        raise HTTPException(404)
    if not session.get(DocumentRestriction, (id, user_id)):
        session.add(DocumentRestriction(document_id=id, user_id=user_id))
    session.add(Audit(actor=user.id, action="document:restrict:" + id))
    session.commit()
    return {"restricted": True}


@app.get("/search")
def search(q: str = "", user: User = Depends(current), session: Session = Depends(db)):
    if len(q) < 2 or len(q) > 200:
        raise HTTPException(422, "Search needs 2–200 characters")
    results = []
    for document in session.scalars(
        select(Document)
        .where(Document.department == user.department, Document.title.icontains(q, autoescape=True))
        .limit(100)
    ):
        try:
            document_access(document.id, user, session)
        except HTTPException:
            continue
        results.append(
            {
                "id": document.id,
                "title": document.title,
                "kind": "document",
                "url": "/documents/" + document.id,
            }
        )
    for record in session.scalars(
        select(Record)
        .where(Record.department == user.department, Record.title.icontains(q, autoescape=True))
        .limit(100)
    ):
        results.append(
            {
                "id": record.id,
                "title": record.title,
                "kind": record.kind,
                "url": "/records/" + record.id,
            }
        )
    return results
